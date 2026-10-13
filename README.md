# ShortLink — Self-Hosted URL Shortener

A simple URL shortener like bitly / shortus.io, built with Python (Flask) + SQLite.
You host it yourself, on your own domain — no monthly fees, your data stays yours.

**Features**
- 🔗 Shorten any URL (auto short code, or your own custom name)
- 📊 Click counter for every link
- 📱 QR code for every short link
- 🗑️ Delete links anytime
- 📋 One-click copy button

---

## Run on your computer (testing)

Needs Python 3.10+.

```bash
cd shortus
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000 in your browser.

## Put it on the internet (free hosting — Render)

1. **Put the code on GitHub**
   - Create a free account at github.com, make a new repository, upload this folder's files.

2. **Create a free Render account** at render.com, then:
   - Dashboard → **New +** → **Web Service** → connect your GitHub repo.
   - Render auto-detects `render.yaml`. Or set manually:
     - Build command: `pip install -r requirements.txt`
     - Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
   - Click **Create Web Service**. In 2–3 minutes you get a public URL like
     `https://shortlink-xyz.onrender.com` — your shortener is live. 🎉

3. **Use your own domain (optional, recommended)**
   - Buy a domain (e.g. from Hostinger, GoDaddy, Namecheap — `.link` / `.io` / `.in`
     domains are cheap and look great for shorteners).
   - In Render: your service → **Settings → Custom Domains** → add your domain.
   - At your domain registrar, add the DNS records Render shows you.
   - Set env var `BASE_URL=https://your-domain.com` in Render
     (service → Environment) so generated short links use your domain.

## Important notes

- **Free hosting sleeps & resets:** on Render's free plan the service sleeps after
  inactivity and its disk resets — saved links can disappear. For a serious
  shortener use a host with persistent storage (Render paid disk, PythonAnywhere,
  or any VPS) — the app needs zero code changes, just a server where `links.db`
  survives restarts.
- **Environment variables**
  - `BASE_URL` — your public domain, e.g. `https://go.example.com` (so short links
    and QR codes use it instead of the auto hostname).
  - `DB_PATH` — where to store `links.db` (default: next to `app.py`).
  - `PORT` — port to listen on (default 5000; hosts set this automatically).

## API (for developers)

| Method | Endpoint            | Body / response |
|--------|---------------------|-----------------|
| POST   | `/api/shorten`      | `{"url": "...", "custom": "optional"}` → `{"code", "short_url", "url"}` |
| GET    | `/api/links`        | list all links with click counts |
| DELETE | `/api/links/<code>` | delete a link |
| GET    | `/<code>`           | redirect to the long URL (counts a click) |
| GET    | `/qr/<code>.png`    | QR code image for the short link |
