# Hosting Plan — Chain Reaction

Everything needed to take this from a laptop to a shop that takes real money.
Written 2026-08-10. Prices are the free tiers as advertised; verify before you
rely on them.

---

## 1. What is missing right now

Ordered by whether it *stops* you launching.

### Blockers — the site will not work correctly without these

| # | Gap | What actually happens | Fix |
|---|-----|----------------------|-----|
| 1 | ~~**`STATIC_ROOT` is not set**~~ ✅ | `collectstatic` fails, so the admin loads with no CSS in production | Set `STATIC_ROOT` + add WhiteNoise |
| 2 | **SQLite on an ephemeral disk** (code ready — set `DATABASE_URL`) | Every redeploy wipes orders, customers, products | Managed Postgres |
| 3 | **`MEDIA_ROOT` is a local folder** (code ready — set the four `R2_*` vars) | Every product photo disappears on redeploy | Object storage (R2 / Cloudinary) |
| 4 | **`SECRET_KEY` still the `django-insecure-` default** | Session and password-reset tokens are forgeable. It is also **already public in git history** | Generate a new one, set via env |
| 5 | ~~**No WSGI server**~~ ✅ | `runserver` is not safe or fast enough for production | `gunicorn` in requirements |
| 6 | ~~**`TIME_ZONE = 'UTC'`**~~ ✅ | Order times in the admin and receipts read 2 hours behind Lusaka | `Africa/Lusaka` |
| 7 | ~~**No `LOGGING` config**~~ ✅ | Every `logger.exception` in the payment code goes nowhere. You would be blind to failed payments | Console logging + Sentry |
| 8 | ~~**No password reset**~~ ✅ | A customer who forgets their password is locked out forever, with no self-service route | Django's built-in reset views + Resend |
| 9 | ~~**No stuck-order reconciliation**~~ ✅ | If a customer approves the PIN then closes the tab *and* the webhook is missed, the order sits `pending` forever. You have been paid and do not know | Management command on a cron |
| 10 | ~~**Product images are served raw**~~ ✅ | A 4 MB phone photo × 12 on the browse grid = a ~50 MB page. On Zambian mobile data that is unusable | Resize on upload, or Cloudinary transforms |

### Security — do before taking real payments

| # | Gap | Fix |
|---|-----|-----|
| 11 | ~~**No rate limiting anywhere**~~ ✅ | Applied per §5; LocMemCache means limits are per-worker until Redis or Cloudflare fronts it |
| 12 | ~~`SECURE_HSTS_SECONDS` unset~~ ✅ | Now env-driven; set it once HTTPS works |
| 13 | ~~No upload size/type limit~~ ✅ | 8 MB cap, JPEG/PNG/WebP only |
| 14 | Admin is at the guessable `/admin/` | Move it, and/or put Cloudflare Access in front |
| 15 | ~~No error monitoring~~ ✅ | Sentry wired, inert until `SENTRY_DSN` is set |

### Trust and legal — customers and payment providers expect these

| # | Gap |
|---|-----|
| 16 | ~~No Terms/Privacy/Returns~~ ⚠️ **drafted, needs your review** — each page carries a highlighted box to delete once checked. Bila may ask for these during onboarding, and taking money without a refund policy is a dispute waiting to happen |
| 17 | ~~No 404 / 500 templates~~ ✅ done |
| 18 | ~~No favicon or `robots.txt`~~ ✅ (sitemap still missing) |
| 19 | No business contact details beyond an email — a phone number materially increases conversion in Zambia |

### Nice to have

- Order confirmation by SMS (many customers will not check email)
- A real "About" page — the curation story is your differentiator and it currently only exists as two lines on the landing page
- Stock reconciliation if you ever hold more than one of a piece
- Analytics (Plausible free trial / self-hosted, or GA4)

---

## 2. Hosting options

### The honest constraint

Free tiers that **sleep after inactivity** are risky here, because Bila posts a
webhook when a payment settles. If your app is asleep, that delivery may fail.

You are partly protected: the order status page polls Bila directly, and
`refresh_from_bila` reconciles state. But a customer who closes the tab relies
on the webhook alone — which is exactly why **blocker #9 (the reconciliation
cron) matters more than usual on a free tier**.

### Comparison

| Option | Free tier | Sleeps? | Region for Zambia | Verdict |
|---|---|---|---|---|
| **Fly.io** | Small allowance, pay-as-you-go after | Optional scale-to-zero (~1–2 s wake) | **Johannesburg (`jnb`)** — closest to Lusaka | ⭐ **Recommended.** The only one with an African region |
| **Render** | 512 MB web service free | Yes, ~50 s cold start | Frankfurt / Oregon | Simplest to set up; the cold start is painful for a shop |
| **Koyeb** | 1 free instance | No | Frankfurt / Washington | Good middle ground |
| **Oracle Cloud Always Free** | 4 ARM cores, 24 GB RAM, genuinely free forever | No | Johannesburg available | Best hardware by far, but *you* run the server, patches, backups, TLS |
| **PythonAnywhere** | Free tier | No | EU/US | ⚠️ **Avoid.** Free accounts can only reach whitelisted domains — Bila's API would be blocked |
| **Railway** | Trial credit only | No | EU/US | Not free ongoing |
| **Vercel / Netlify** | — | — | — | Not suited to Django with a database and uploads |

### Recommended stack (all free tier)

```
Cloudflare (DNS, CDN, WAF, rate limiting)
        │
        ▼
   Fly.io  (Django + gunicorn, jnb region)
        ├── Neon          → Postgres
        ├── Cloudflare R2 → product photos
        ├── Resend        → receipts and seller alerts
        └── Sentry        → error tracking
```

**If you want the least work instead of the best result:** Render + Neon +
Cloudinary + Resend. Accept the cold start, and make sure the reconciliation
cron runs from an external scheduler (cron-job.org) rather than in-process.

---

## 3. Third parties

| Need | Pick | Free tier | Why |
|---|---|---|---|
| **Email** | **Resend** | 3,000/month, 100/day | Best developer experience, plain SMTP available so no code change is needed. Requires domain verification to send from your own address |
| **Database** | **Neon** | 0.5 GB, scale-to-zero | Postgres, generous, painless |
| ← alternative | Supabase | 500 MB | Also gives you storage in one account |
| **Media storage** | **Cloudflare R2** | 10 GB + **zero egress fees** | Egress is what makes S3 expensive; R2 charges none |
| ← alternative | **Cloudinary** | 25 credits/month | Costs more at scale, but does **automatic resizing, WebP and CDN** — which fixes blocker #10 for free. For an image-heavy jewelry shop this is the pragmatic pick |
| **CDN / DNS / WAF** | **Cloudflare** | Free | Also where you get free rate limiting |
| **Errors** | **Sentry** | 5k errors/month | Tells you when a payment breaks |
| **Uptime** | **UptimeRobot** | 50 monitors, 5-min checks | Also keeps a sleeping free instance warm |
| **Scheduled jobs** | **cron-job.org** | Free | Hits your reconciliation endpoint on a schedule |
| **SMS (optional)** | Africa's Talking | Pay as you go | Zambian coverage, cheap |

### On Resend specifically

No code change is needed — the app already reads SMTP settings from the
environment:

```
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=re_xxxxxxxxxxxx     # your Resend API key
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Chain Reaction <orders@yourdomain.com>
```

You must verify `yourdomain.com` in Resend (add their DNS records) before you
can send from that address. For testing before you own a domain, send from
`onboarding@resend.dev`.

---

## 4. Storage and performance

### The problem today

`Item.image` stores whatever is uploaded, at full size, and the templates serve
that same file into a 350 px grid slot. A modern phone photo is 3–6 MB. Twelve
of them is a ~50 MB page. On a Zambian mobile connection that is a page nobody
waits for.

### Two ways to fix it

**Option A — Cloudinary (less code, recommended to start).**
Upload once; request `w_600,f_auto,q_auto` variants in the template. Cloudinary
resizes, converts to WebP, and serves from its CDN. Blocker #10 disappears
without writing an image pipeline.

**Option B — R2 + resize on upload (cheaper at scale).**
`django-storages` points `MEDIA_ROOT` at R2. On save, Pillow writes a 1600 px
"full" and a 600 px "card" version. Serve the card version in grids. More code,
but no per-transform cost and no vendor lock.

Either way:

- Serve **static** files with WhiteNoise (compressed, hashed filenames, cached
  forever) and let Cloudflare cache them at the edge. Do not put static on R2 —
  it adds complexity for no gain at this size.
- Keep `loading="lazy"` on grid images (already done).
- Cap uploads: reject anything over ~8 MB or outside JPEG/PNG/WebP.

### Sizing guidance

At 10 GB of R2 storage you can hold roughly 2,000 product photos at 5 MB each,
or about 20,000 once resized. You will not outgrow the free tier for years.

---

## 5. Rate limiting — where and why

Nothing is rate limited today. Priorities:

| Endpoint | Risk if unlimited | Suggested limit |
|---|---|---|
| `POST /login/` | Password brute force | 5 / 5 min per IP **and** per username |
| `POST /signup/` | Bulk fake accounts | 3 / hour per IP |
| Password reset (once added) | Email bombing a customer | 3 / hour per IP + per email |
| `POST /orders/checkout/` | Triggers a **real Bila API call** and a PIN prompt to a real phone. Abuse costs you money and spams a stranger's handset | 5 / hour per IP, 3 / hour per phone number |
| `GET /orders/<ref>/state/` | Polled every 5 s by design; a stuck tab hammers Bila's API | 30 / min per IP |
| `POST /cart/add/<id>/` | Session bloat | 60 / min per IP |
| `POST /orders/webhook/bila/` | Signature-protected, but verification costs CPU | 120 / min per IP |

**Checkout is the one that matters most** — every request there sends a PIN
prompt to a real phone. Unlimited, that is a harassment vector and a bill.

**How:** `django-ratelimit` for per-view decorators, plus Cloudflare rate
limiting rules at the edge as a second layer. Add `django-axes` if you want
account lockout with an admin audit trail.

---

## 6. Launch sequence

### Phase 1 — make it deployable ✅ DONE
- [x] `STATIC_ROOT` + WhiteNoise + `gunicorn` — verified: `collectstatic`
      produces 130 fingerprinted files and the admin loads its CSS under gunicorn
- [x] `TIME_ZONE = 'Africa/Lusaka'`
- [x] `LOGGING` to console, with `orders` kept verbose
- [x] `dj-database-url` — set `DATABASE_URL` and it switches to Postgres
- [x] 404 / 500 templates (500 is standalone by design)
- [x] Password reset, four pages plus the email
- [x] Upload size and format validation, checked against the parsed image
- [x] `Dockerfile`, `.dockerignore`, `fly.toml`
- [x] **Reconciliation** — `manage.py reconcile_orders` and a token-protected
      `POST /orders/cron/reconcile/` for external schedulers
- [x] `manage.py check --deploy` passes clean with production env vars

**Still outstanding (needs your accounts or a decision):** object storage for
media, image resizing, rate limiting, Sentry, Terms/Privacy/Returns pages.

### Phase 2 — accounts (you do these, then hand me the keys)
- [x] Domain: **chainreactionjewelry.site**
- [x] **Resend** — domain verified, API key in `.env`. Test receipt and seller
      alert both delivered to the inbox (not spam) on 2026-08-10, so SPF/DKIM
      are good. Reply-To correctly resolves to the Gmail inbox.
- [ ] Neon → copy `DATABASE_URL`
- [ ] Cloudflare R2 (or Cloudinary) → copy credentials
- [x] **Bila sandbox** — key and wallet id in `.env`, connectivity confirmed
      2026-08-10 (a status lookup authenticated and returned "not found").
      The webhook URL still cannot be registered until there is a public host.
- [ ] Sentry → copy DSN
- [ ] Point the domain at Cloudflare
- [x] `DJANGO_SECRET_KEY` generated (a separate one is still needed for prod)

### Decisions made
- **Host: Fly.io**, `jnb` (Johannesburg) — `Dockerfile` and `fly.toml` are ready.
- **Media: Cloudflare R2** — wired via django-storages, inert until the four
  `R2_*` variables are set. Verify with `manage.py check_storage`.
- **Email: Resend** — verified and delivering.

### Proven working (2026-08-10, against the real sandbox)
- Full purchase over a public tunnel: checkout → Bila → paid → stock marked
  sold → bag cleared → receipt and seller alert delivered.
- Two real bugs this caught, both since fixed: a wrong `BILA_WALLET_ID` failing
  every checkout, and the seller alert being lost when a second SMTP connection
  timed out.
- Bila's webhook was never registered (the sandbox account had zero configs),
  so delivery is still unproven. Not a blocker: both purchases settled through
  polling, and `reconcile_orders` covers the closed-tab case.

### Phase 3 — wire up and test in sandbox
- [ ] Fill in `.env`, deploy
- [ ] `migrate`, `createsuperuser`, `seed_demo`
- [ ] Upload a real hero image at admin → Site content
- [ ] Register the Bila **sandbox** webhook: `https://yourdomain.com/orders/webhook/bila/`
- [ ] Full test purchase with a sandbox key — confirm the PIN prompt, the paid
      state, the receipt email, and the seller alert
- [ ] Kill the tab mid-payment and confirm the reconciliation cron settles it

### Phase 4 — go live
- [ ] Swap `BILA_BASE_URL` to `https://api.usebila.com` and the key to `sk_live_`
- [ ] Re-register the webhook against the live account
- [ ] `DJANGO_DEBUG=False`, `SECURE_HSTS_SECONDS=31536000`
- [ ] `manage.py check --deploy` clean
- [ ] Rate limits on
- [ ] **One real low-value purchase with your own phone**, end to end
- [ ] Terms / Privacy / Returns published
- [ ] UptimeRobot + Sentry alerting to your email
- [ ] Confirm database backups are on (Neon does this, but check the retention)

---

## 7a. What actually happened — Oracle VM (2026-08-17)

Instead of Koyeb, the shop runs on an **Oracle Cloud Always Free VM**
(`instance-20260816-1409`, VM.Standard.E2.1.Micro, 1 GB RAM, af-johannesburg-1,
`ssh opc@92.4.149.191`). Persistent disk means **no Neon and no R2 needed**:
SQLite lives in `/home/opc/app/data/`, media in `/home/opc/app/media/`, both
bind-mounted into the container.

Stack on the VM: Docker (static binaries at `/usr/local/bin` — **never run
`dnf` on this box**, it OOM-wedges the 1 GB instance for ~30 min; three
force-reboots learned this) + `docker compose` (web: gunicorn ×2 workers,
caddy: auto-HTTPS). A 2 GB swapfile (`/swapfile2`) supplements the stock 1 GB.
`reconcile-orders.timer` (systemd) sweeps stuck orders every 10 min. VCN
security list and firewalld both allow 80/443.

Deploying an update: push to GitHub, then on the VM
`cd /home/opc/app && curl -fsSL .../archive/refs/heads/main.tar.gz | tar xz
--strip-components=1 && docker compose up -d --build` (run it via
`sudo systemd-run` so a dropped SSH session can't kill it).

**Live since 2026-08-17, launch complete the same day**:
https://chainreactionjewelry.site serves over HTTPS (Let's Encrypt via Caddy,
auto-renewing; Cloudflare records are DNS-only — flipping the proxy back on
needs an origin cert first). Caddy also serves `/media/` from the shared
volume, since Django rightly refuses with DEBUG off. Everything after that is
done and proven on the **live** Bila account: a real failed payment (PIN
ignored → reconcile marked it failed) and a real successful K1 purchase
(paid in seconds → stock sold → receipt + seller alert delivered). Live
webhooks carry only Bila's collection id, no order reference — the webhook
matcher handles both shapes. HSTS is on (31536000, preload), Sentry is
receiving events, UptimeRobot pings every 5 min, legal pages published,
`check --deploy` clean in production.

## 7. Launch today — free (2026-08-16)

**Correction:** Fly.io retired free allowances for new accounts (new signups get
a ~7-day/2-VM-hour trial, then ~$2–5/mo). For a $0 launch the host is now
**Koyeb** (one free instance, 512 MB, Frankfurt, no card required). It scales
to zero after 1 h idle with a 1–5 s cold start — an UptimeRobot ping every
5 min keeps it warm. `Dockerfile` works unchanged; Koyeb builds it from GitHub.
Fly (`jnb`) remains the upgrade path once revenue covers ~$5/mo.

Stack: **Koyeb + Neon + Cloudflare R2 + Resend (done) + cron-job.org +
UptimeRobot**. Note R2 needs a card on file for billing verification even at
$0; if that blocks today, use the bucket's free `r2.dev` public URL and skip
the custom media domain for now.

Sequence: create Neon + R2 → deploy on Koyeb from GitHub with full env →
createsuperuser via Koyeb web terminal → register Bila sandbox webhook at the
`.koyeb.app` URL → cron-job.org POST to `/orders/cron/reconcile/` every 10 min
→ UptimeRobot on `/` every 5 min → sandbox test purchase → point
chainreactionjewelry.site at it and go live per Phase 4.

## 8. Rough running cost

| Stage | Monthly |
|---|---|
| Everything on free tiers | **$0** (domain ~$12/year) |
| After outgrowing free (≈1k visitors/day) | Fly ~$5, Neon ~$19, R2 ~$0–1, Resend ~$20 → **~$45** |

Bila takes its own cut per transaction — confirm the rate with them; it is not
included above.
