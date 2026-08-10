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
| 1 | **`STATIC_ROOT` is not set** | `collectstatic` fails, so the admin loads with no CSS in production | Set `STATIC_ROOT` + add WhiteNoise |
| 2 | **SQLite on an ephemeral disk** | Every redeploy wipes orders, customers, products | Managed Postgres |
| 3 | **`MEDIA_ROOT` is a local folder** | Every product photo disappears on redeploy | Object storage (R2 / Cloudinary) |
| 4 | **`SECRET_KEY` still the `django-insecure-` default** | Session and password-reset tokens are forgeable. It is also **already public in git history** | Generate a new one, set via env |
| 5 | **No WSGI server** | `runserver` is not safe or fast enough for production | `gunicorn` in requirements |
| 6 | **`TIME_ZONE = 'UTC'`** | Order times in the admin and receipts read 2 hours behind Lusaka | `Africa/Lusaka` |
| 7 | **No `LOGGING` config** | Every `logger.exception` in the payment code goes nowhere. You would be blind to failed payments | Console logging + Sentry |
| 8 | **No password reset** | A customer who forgets their password is locked out forever, with no self-service route | Django's built-in reset views + Resend |
| 9 | **No stuck-order reconciliation** | If a customer approves the PIN then closes the tab *and* the webhook is missed, the order sits `pending` forever. You have been paid and do not know | Management command on a cron |
| 10 | **Product images are served raw** | A 4 MB phone photo × 12 on the browse grid = a ~50 MB page. On Zambian mobile data that is unusable | Resize on upload, or Cloudinary transforms |

### Security — do before taking real payments

| # | Gap | Fix |
|---|-----|-----|
| 11 | **No rate limiting anywhere** | See §5 |
| 12 | `SECURE_HSTS_SECONDS` unset | Set once HTTPS is confirmed working |
| 13 | No upload size/type limit | A visitor with an account can upload a 500 MB file |
| 14 | Admin is at the guessable `/admin/` | Move it, and/or put Cloudflare Access in front |
| 15 | No error monitoring | Sentry free tier |

### Trust and legal — customers and payment providers expect these

| # | Gap |
|---|-----|
| 16 | No Terms of Service, Privacy Policy, or Returns/Refunds page. Bila may ask for these during onboarding, and taking money without a refund policy is a dispute waiting to happen |
| 17 | No 404 / 500 templates — errors show Django's bare pages, which look broken |
| 18 | No favicon, `robots.txt`, or sitemap |
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

### Phase 1 — make it deployable (code, no accounts needed)
- [ ] `STATIC_ROOT` + WhiteNoise + `gunicorn`
- [ ] `TIME_ZONE = 'Africa/Lusaka'`
- [ ] `LOGGING` to console
- [ ] `dj-database-url` so `DATABASE_URL` switches to Postgres
- [ ] 404 / 500 templates in the editorial style
- [ ] Password reset views + editorial templates
- [ ] Upload size and type validation
- [ ] `Dockerfile` or `render.yaml` / `fly.toml`

### Phase 2 — accounts (you do these, then hand me the keys)
- [ ] Buy a domain, point it at Cloudflare
- [ ] Neon → copy `DATABASE_URL`
- [ ] Cloudflare R2 (or Cloudinary) → copy credentials
- [ ] Resend → verify domain, copy API key
- [ ] Sentry → copy DSN
- [ ] Generate a fresh `DJANGO_SECRET_KEY`

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

## 7. Rough running cost

| Stage | Monthly |
|---|---|
| Everything on free tiers | **$0** (domain ~$12/year) |
| After outgrowing free (≈1k visitors/day) | Fly ~$5, Neon ~$19, R2 ~$0–1, Resend ~$20 → **~$45** |

Bila takes its own cut per transaction — confirm the rate with them; it is not
included above.
