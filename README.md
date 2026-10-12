# Roam Atlas — Travel Planner

An independent, responsive travel planner with an English-first frontend and a Python WSGI backend. Russian translations and a persistent dark theme are included.

## Run locally

Python 3.10+; no dependencies required for local preview:

```sh
python app.py
```

Open http://127.0.0.1:8080. This is a local preview URL, not a public deployment.

## Features

- Six curated destinations with search and category filters.
- Create, edit and delete trips persisted in PostgreSQL in production or SQLite locally.
- Per-browser visitor isolation using a random HttpOnly session cookie.
- Dates, day-by-day itinerary, budget allocation, packing checklist and notes.
- JSON export for backups; EN/RU translation and light/dark theme.
- Responsive layout, labelled forms, native modal focus handling, reduced motion support.
- Server validation, parameterized SQL, same-origin mutation checks, security headers.
- Docker configuration and GitHub Actions backend checks.

Budgets are illustrative USD estimates, not live prices. Images are loaded from Unsplash and require network access. This is a planner, not a booking service. Visitor accounts and cross-device synchronization are not implemented. Owner administration is available at /admin. Clearing the session cookie loses access to that browser's trips; export first. Exported files are backups, with no import UI currently implemented. Other visitors cannot list or edit your trips. The deployment operator can access the database.

## Production

See `PUBLISHING.md` for GitHub, public hosting and Google Search Console setup. `SITE_URL` must be set to the actual assigned HTTPS origin to enable indexing and the dynamic sitemap. `GOOGLE_SITE_VERIFICATION` optionally enables HTML-tag ownership verification. `.env.example` lists settings; this app reads real environment variables, not `.env` files automatically.

Use the Dockerfile or install `requirements.txt` and run:

```sh
gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 4 app:application
```

For free hosting, use a Render Python web service with an external Neon PostgreSQL database. Set `DATABASE_URL` to the private connection string in Render environment settings. Never commit this value. The application requires PostgreSQL when running on Render and refuses to silently store production data on its temporary filesystem. No paid disk is needed. See `render.yaml.example` for configuration.

Free Render services sleep after inactivity, so the first visit can take longer. Database and hosting free tiers have usage limits; review each provider's current terms. PostgreSQL data survives web-server restarts; maintain separate backups for recovery. Local development uses SQLite through `DATABASE_PATH` and needs no PostgreSQL dependency.

Terminate HTTPS at the host proxy, which must sanitize forwarding headers. Gunicorn is intended for Linux production; the included preview server is development-only. GitHub Pages cannot run this Python backend.

Live website: https://roam-atlas.onrender.com. Owner console: https://roam-atlas.onrender.com/admin. Source repository: https://github.com/TimurBegimkulov/roam-atlas. A public URL can open in Chrome after deployment; Google indexing is separate and not guaranteed.

## Verify

```sh
python -m unittest discover -v
node --check app.js
```

Backend tests cover persistence, CRUD, visitor isolation, invalid data, CSRF, static file restrictions, security headers, and secure cookies. See `VERIFICATION.md` for checks actually performed.


## Owner administration
Open /admin. Set ADMIN_USERNAME and ADMIN_PASSWORD_HASH as hosting environment variables. Generate the hash with admin.password_hash using Python; never commit the password. Login uses PBKDF2-SHA256 (600,000 rounds), one-hour server sessions, five-attempt lockout, same-origin mutation checks and an audit log. Changing the configured password hash invalidates existing sessions. Sessions and lockouts are stored in the persistent database. No claim of a formal security audit is made. The reverse proxy must sanitize forwarding headers; place edge rate limits in front of a high-traffic public deployment.

