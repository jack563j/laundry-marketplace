# FreshFold — Laundry Pickup & Tracking (Prototype)

A working prototype of a Swiggy/Zomato-style app for a laundry pickup
business: customers sign up with an ID photo + a live selfie, an admin
verifies them, customers book a pickup slot and photograph every item
they're sending, the admin checks the photos match the bag before
approving pickup, laundry staff track the order from pickup through wash
to delivery — checking each item off against its photo on arrival — and
delivery is confirmed with an in-app OTP only the customer can see.

This is a **demo/prototype**: ID "verification" is an admin looking at
the uploaded photo (no real KYC/OCR), and there's no payment gateway.
Both are called out under **Next steps** below.

## The three roles

**Customer** — signs up with name, phone, address, password, an ID
photo, and a current photo of themselves → waits for admin approval →
books a pickup slot → uploads a photo + optional instructions for every
item → submits for approval → tracks the order on a live status
timeline → when the order is out for delivery, sees a 4-digit code
in-app to read out to the delivery person.

**Admin** (you) — approves or rejects new customer accounts after
checking their ID photo and selfie → opens pickup slots (date, time,
location, capacity) → reviews each order's item photos against
instructions → approves the pickup (optionally assigning a staff
member) or sends it back to the customer for correction → sees every
order at every stage.

**Staff** (your laundry team) — sees their work queue → before pickup,
can view the customer's live photo to confirm identity at the door →
confirms pickup → on arrival at the laundry, checks off every item
against its photo (the app won't let the order move to "washing" until
every item is checked) → marks washing → ready → out for delivery →
asks the customer for their 4-digit code and enters it to confirm
delivery — the order can't be marked delivered without it.

## Run it locally

```bash
cd laundry-marketplace
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Open **http://localhost:5050**. The database and an `instance/uploads`
folder are created automatically on first run, seeded with a demo
admin, a demo staff member, and three open pickup slots.

**Demo logins** (also shown on the login page):
- Admin — phone `9999900001`, password `admin123`
- Staff — phone `9999900002`, password `staff123`
- Customers sign up for themselves at `/auth/signup`

## Try the full flow
1. Sign up as a new customer — you'll need any two photos on hand (a
   phone will offer to open the camera for the "current photo" field).
2. Log out, log in as **admin**, go to *Customers*, approve the new signup.
3. Log out, log back in as the customer, *Book pickup*, pick a slot.
4. Upload one or two item photos with instructions, then submit.
5. Log in as **admin** → *Orders* → open the order → *Approve pickup*.
6. Log in as **staff** → open the order → advance: picked up → at
   laundry (check off every item) → washing → ready → out for delivery.
7. Log back in as the **customer**, open the order, and note the
   4-digit delivery code shown on the tracking page.
8. Log back in as **staff**, open the order, enter that code under
   *Confirm delivery*.

## What's been hardened, and why

| Risk | What's done about it |
|---|---|
| Guessable URLs exposing another customer's ID/selfie/item photos | Uploaded files are stored **outside** the public `static/` folder and served only through routes that check who's logged in and what they're allowed to see (`app/main.py`) |
| Cross-site request forgery (a malicious page submitting forms as a logged-in user) | Flask-WTF's `CSRFProtect` is on globally; every form carries a token |
| Brute-forcing the login form or spamming signups | Flask-Limiter caps login to 10/min and signup to 8/hour per IP |
| A renamed non-image file uploaded as a "photo" | Every upload is opened and verified with Pillow, not just checked by file extension |
| Session cookies stolen over an insecure network | `HttpOnly` + `SameSite=Lax` always; `Secure` (HTTPS-only) and HSTS switch on automatically once `FLASK_ENV=production` is set |
| Clickjacking / MIME-sniffing | `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` set on every response |
| Guessed delivery codes | OTP is a random 4-digit code generated with `secrets` (not predictable), shown only to the customer, and locks after 5 wrong attempts |
| Passwords in the database | Hashed with Werkzeug's `generate_password_hash` (never stored in plain text) |
| SQL injection | All queries go through SQLAlchemy's ORM — no raw string-built SQL anywhere |

None of this is a substitute for a real security review before you
launch to real customers with real payments — see **Next steps**.

## Deploying for testing (GitHub + a free host)

You don't "run it on GitHub" directly — GitHub hosts your code, and a
separate service runs it. The common free pattern is **GitHub → Render
(or Railway)**, so pushing to GitHub auto-deploys.

**1. Push the code to GitHub**
```bash
cd laundry-marketplace
git init
git add .
git commit -m "Initial commit"
```
Create an empty repo on github.com (no README/license, so it stays
empty), then:
```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```
`.gitignore` already excludes `venv/`, the database, and `instance/` —
so no uploaded photos or the local SQLite file get committed. **Never
commit a real `.env` file or the demo passwords once real customers use
this** — see the checklist below.

**2. Deploy on Render (free tier works for testing)**
1. Sign up at render.com, click **New → Web Service**, connect your GitHub repo.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn run:app` (already set in `Procfile`, Render picks it up automatically)
4. Add environment variables under the service's *Environment* tab:
   - `SECRET_KEY` — generate one locally with `python -c "import secrets; print(secrets.token_hex(32))"` and paste the output
   - `FLASK_ENV` = `production`
5. Deploy. Render gives you a `https://your-app.onrender.com` URL.

**Important limitation for testing on a free tier**: Render's free web
services use *ephemeral disk* — anything written after deploy (your
SQLite database, uploaded photos) is wiped on restart/redeploy. That's
fine for a first round of testing, but before real customers use it:
- Add Render's free Postgres add-on and set `DATABASE_URL` to its
  connection string (the app already handles this — no code change
  needed, just `pip install psycopg2-binary` and add it to
  `requirements.txt`).
- Move uploaded photos to persistent storage — a paid Render disk, or
  cloud storage like AWS S3 / Cloudflare R2 — instead of local disk.

Railway works the same way and also has a free trial tier, if you'd
rather compare.

## Before this touches a real customer's data

- [ ] Move off SQLite to Postgres (see above) — SQLite doesn't handle concurrent writes from multiple people well.
- [ ] Move uploaded photos off local disk to cloud storage.
- [ ] Change the demo admin/staff passwords (currently `admin123` / `staff123` — fine for local testing, not for anything public).
- [ ] Put a real KYC/ID-verification service behind signup instead of manual photo review, or at least encrypt ID photos at rest.
- [ ] Add a payment gateway if you're collecting money in-app.
- [ ] Get a second pair of eyes (or a paid security review) on the auth and file-access code before real customer data flows through it — this prototype follows good practices but hasn't been audited.
- [ ] Set up HTTPS (Render/Railway give you this automatically) and confirm `FLASK_ENV=production` is set so secure cookies are active.

## Project structure
```
laundry-marketplace/
├── run.py                   # entrypoint (loads .env locally, reads PORT)
├── config.py                 # env-driven config: DB, upload folders, cookie security
├── requirements.txt
├── Procfile                  # `gunicorn run:app` — used by Render/Railway/Heroku
├── .env.example                # copy to .env for local secrets
├── .gitignore                   # keeps venv/, the DB, and uploads out of git
├── app/
│   ├── __init__.py              # app factory, CSRF/rate-limit/security headers, blueprint registration
│   ├── models.py                # User, PickupSlot, Order, OrderItem, OrderStatusLog
│   ├── extensions.py             # db, login_manager, csrf, limiter
│   ├── utils.py                   # role_required decorator, verified image upload helper
│   ├── main.py                     # protected /uploads/* file-serving routes
│   ├── seed.py                      # demo admin/staff/slots
│   ├── auth/                         # signup, login, logout
│   ├── customer/                      # dashboard, book, item upload, tracking + OTP display
│   ├── admin/                          # KYC approval, slots, pickup approval, orders
│   ├── staff/                           # work queue, item checklist, status advance, OTP delivery confirm
│   ├── templates/                        # Jinja templates per blueprint
│   └── static/                            # css, js only — no user-uploaded files live here anymore
```
Uploaded photos are stored in `instance/uploads/` (outside `app/`
entirely), created automatically on first run.

## Order status pipeline
`AWAITING_ITEMS → PENDING_PICKUP_APPROVAL → PICKUP_APPROVED → PICKED_UP
→ AT_LAUNDRY → WASHING → READY → OUT_FOR_DELIVERY → DELIVERED`
(or `CANCELLED` before pickup). `OUT_FOR_DELIVERY → DELIVERED` requires
the customer's OTP — there's no button that skips it. Every transition
is logged with a timestamp in `OrderStatusLog`, which powers the
tracker.

## Other next steps worth considering
- **Notifications**: push/WhatsApp when status changes, so customers don't have to keep checking the app. (WhatsApp's own OTP/template messages aren't free at any real volume — they're billed per conversation by Meta — so in-app OTP, as built, is the zero-cost option you asked about.)
- **Live location** for delivery — real map tracking needs a geolocation-enabled staff app, a bigger addition than the rest of this list.
- **Admin-created staff accounts** currently need the seed script or a DB console — worth adding a simple "add staff" form in the admin panel.
