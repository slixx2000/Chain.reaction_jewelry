# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Django storefront for a jewelry business, paying via **Bila** mobile money.
SQLite. Dependencies live in `requirements.txt`; the venv is at `.venv/`
(gitignored) and Django is **not** installed system-wide, so every command must
go through `.venv/bin/python`.

Config comes from `.env` (see `.env.example`), loaded by `python-dotenv` in
`settings.py`. Without `BILA_API_KEY` set, checkout fails loudly — that is
intentional, never stub a fake success. With `EMAIL_HOST` blank, receipts print
to the console instead of sending.

Email templates live in `orders/templates/orders/email/` and are **inline-styled
tables** — none of the site's Tailwind reaches a mail client, so don't reach for
utility classes there.

## Commands

```bash
.venv/bin/python manage.py runserver
.venv/bin/python manage.py makemigrations && .venv/bin/python manage.py migrate
.venv/bin/python manage.py test                                   # all apps
.venv/bin/python manage.py test cart.tests.CartTests.test_add_and_total_uses_exact_decimals
```

Tests live in `cart/tests.py` (cart behaviour, delete authorization) and
`orders/tests.py` (phone parsing, webhook signatures, the payment state
machine). Payment tests patch `orders.services.bila.*` — never let a test hit
the real API.

## Architecture

Four apps, all mounted in `chainreaction/urls.py`:

- **core** — public pages (index, contact), auth. Login uses Django's built-in
  `LoginView` wired to `core.forms.LoginForm`; signup/logout are custom views.
  Owns `core/templates/core/base.html`, which every other template extends.
- **item** — the only model layer: `Category` and `Item` (`created_by` FK to
  `User`, `is_sold` flag, `price` as `DecimalField`, `ImageField` under
  `media/item_images/`). CRUD views scope edit/delete with
  `get_object_or_404(Item, pk=pk, created_by=request.user)` — that ownership
  filter *is* the authorization check. `delete` is `@require_POST`; link to it
  from a form, never an `<a>`.
- **cart** — session-backed, no models. `cart/cart.py` holds the `Cart` class
  storing `{item_id: {'quantity': n}}` under session key `cart_key`.
- **dashboard** — one view: the logged-in user's own items.
- **orders** — checkout, `Order`/`OrderItem`, and the Bila integration.

Two different rules about sold pieces, both deliberate: the **browse grid keeps
them**, greyed out and sorted last (`order_by('is_sold', '-created_at')`), as
proof the work sells; the **landing page excludes them entirely**, because the
hero and best-seller strips must be buyable. `Item.badge` is a manual
merchandising label and is suppressed on sold pieces — the "Sold Out" stamp
replaces it.

`core/storefront.py` defines what the landing page shows (hero, new arrivals,
best sellers) and is the **single** source for it. `core.views.index` renders
from it and `ItemAdmin`'s "Shows on" column reports from it — a second copy
would drift and the admin would start lying about where a piece appears.

`ItemAdmin.get_list_display` is built per request so the placement lookup runs
once per page rather than once per row; never cache that on the ModelAdmin
instance, which is a long-lived singleton shared across threads.

### Payment flow (orders app)

`orders/bila.py` is the only place that talks HTTP to Bila; `orders/services.py`
is the only place that changes order or stock state; views just translate
requests. Keep it that way.

1. `checkout` re-reads prices and availability **from the database** — the
   session cart is the customer's and is never trusted for money — then creates
   a `pending` Order with price snapshots on each `OrderItem`.
2. `services.start_payment` POSTs to `/collections/mobile-money`, which pushes a
   PIN prompt to the customer's handset. Bila's response is already a status, so
   it is fed straight into `apply_collection_status`.
3. Settlement arrives twice — by webhook and by the status page polling
   `orders:state`. `apply_collection_status` is idempotent and guards on
   `order.is_settled`; **the first terminal state wins**. Any new path into it
   must preserve that.
4. `_mark_items_sold` flips `is_sold` only on payment success. Pieces are
   one-of-a-kind, so this is the stock model.
5. `emails.send_order_emails` (customer receipt + seller alert) is queued with
   `transaction.on_commit`, so mail goes out only if the payment actually
   committed, and the `is_settled` guard is what keeps it to one send. Two
   layers of swallowing, both deliberate: `_send` eats delivery errors, and
   `send_order_emails` eats anything earlier (a template error, say) per
   message. Django runs `on_commit` callbacks in sequence and **stops at the
   first exception**, so register one guarded callback rather than several bare
   ones — otherwise a broken receipt silently cancels the seller alert.
   Note that `on_commit` callbacks do not fire under `TestCase` unless wrapped
   in `self.captureOnCommitCallbacks(execute=True)`.

The webhook (`/orders/webhook/bila/`) verifies `X-Bila-Signature`
(HMAC-SHA256 over `{timestamp}.{rawBody}`, 5-minute window) against
`BILA_WEBHOOK_SECRET`, then **ignores the body's status and re-reads the
collection from Bila's API**. The body is a trigger, not evidence — a replayed
or forged body must never be able to mark an order paid. It is `@csrf_exempt`
by necessity, so the signature check is the entire security boundary.

Guests can check out; `_get_visible_order` authorizes by order owner *or* a
reference stored in the session, so order pages are not readable by reference
alone.

`cart.context_processors.cart_context_processor` is registered in settings, so
`cart` is available in every template (used for the nav badge) — do not
instantiate `Cart` in a view just to render the header.

## Copy rule — do not describe the jewelry as made here

The pieces are **sourced abroad and resold in Zambia**. Nothing in the product
copy, metadata, emails or templates may say handmade, handcrafted, made by
hand, artisan, crafted in Zambia, or offer commissions. The positioning is
curation: chosen, sourced, found, brought here. `HonestCopyTests` in
`core/tests.py` fails the build if a banned phrase reaches a rendered page —
if you are tempted to loosen it, change the business, not the test.

The original Stitch reference design still carries the old "Made by Hand" copy.
If you are handed it, take its **visual** system only.

## Design system — "Obsidian & Gold"

Landing page and shared chrome follow an editorial system: obsidian/ink
surfaces, warm ivory text, antique gold used sparingly as an accent, Bodoni
Moda display over Hanken Grotesk body, **sharp 0px corners**, hairline ivory
rules, no shadows (depth comes from tonal layering and the `.grain` overlay),
and deliberate asymmetry. Tokens live in the Tailwind config in `base.html`
alongside the older `chain-*` colours, which inner pages still use — that
config is the source of truth now, not any external design file.

The landing page banner is `SiteContent.hero_image`, a deliberate single-row
model edited at **admin → Site content**. Always read it via
`SiteContent.load()`, which creates the row on first use so templates never
have to handle it missing; `save()` pins `pk=1` and drops `force_insert` so
`create()` updates instead of hitting the unique constraint. Empty image falls
back to the labelled placeholder — never hard-code a hero path.

`core/_placeholder.html` renders a labelled block wherever a photo has not been
shot yet. **Multi-line `{# #}` comments do not exist in Django** — it only
closes on the same line, so a `{% include %}` written inside one is executed for
real. Use `{% comment %}` in templates; this exact mistake made the placeholder
partial include itself and blew the stack.

## Conventions

- Tailwind comes from the CDN in `base.html`, with a custom `chain-*` palette
  (`chain-gold`, `chain-slate-dark`, `chain-wine`) defined inline in that
  `<script>` block. New colors go there, not in a config file.
- Form field styling lives in Python: `INPUT` in `core/forms.py` and
  `item/forms.py` is the shared Tailwind class string, applied via
  `StyledFormMixin` (auth forms) or `Meta.widgets` (`ItemForm`). Templates never
  restate it.
- Three partials carry the repeated markup — reuse them instead of copying:
  `core/_form.html` (whole form body: errors, labels, fields) and
  `item/_card.html` (product card, incl. sold badge and add-to-bag form).
- `ItemForm` serves both create and edit; there is no separate edit form.
- All URL namespaces are set (`core:`, `item:`, `cart:`, `dashboard:`); always
  reverse with the namespace.
- `add_to_cart` branches on the `X-Requested-With` header: AJAX gets JSON
  (consumed by the vanilla JS at the bottom of `base.html` to update the badge
  and modal), plain POST gets a same-host-checked referer redirect. Keep both
  paths working — the JS falls back to a full navigation on any error.
- There is no order/checkout/payment model. The checkout button deliberately
  links to `core:contact` and says so; don't fake a payment flow.
