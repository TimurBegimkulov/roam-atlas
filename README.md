# Roam Atlas — Travel Planner

An independent, responsive travel planner with English and Russian interfaces and a Python WSGI backend. The redesigned discovery experience includes country photography, a shared country catalogue, saved favourites, comparisons, and light, dark or system appearance.

## Release and hosting status

This folder contains the complete updated Python application and its frontend. The prepared, not-yet-published Sites edition uses the redesigned frontend and connects to the existing `https://roam-atlas.onrender.com` Python API through a restricted same-origin proxy. Publishing the Sites edition does **not** update the original Render deployment. Backend improvements in this folder take effect on Render only after this source is deployed there.

Accounts and trips in the Sites edition are handled by the existing Python service. Browser cookies are scoped to each website, so a guest session on the original Render website is not automatically the guest session on the Sites website. Sign in with an existing account to access that account's plans. Country favourites and appearance preferences remain on the current device.

## Run locally

Python 3.10+; no dependencies required for local preview:

```sh
python app.py
```

Open http://127.0.0.1:8080. This is a local preview URL, not a public deployment.

On Windows, double-click `start-local.cmd` to use an isolated local configuration. It selects this folder's `data/orbit.sqlite3`, fixes the port at 8080, and clears inherited production database, indexing and administrator settings for that process only. It checks for Python 3.10+ and explains how to install it if unavailable. Direct `python app.py` intentionally continues to respect your environment variables; use that command when you want a custom configuration.

## Features

- A shared catalogue of 250 current countries and territories powers discovery and the trip country picker. Retired GeoNames codes AN and CS are excluded.
- 34,160 indexed cities across 244 of those countries and territories, with country/city search, pagination, sorting and alternate-name matching. Territories without indexed cities stay visible and return an honest empty city list.
- A local JPEG for every current country/territory, with Wikimedia source, author and licence metadata. Individual city photographs take precedence; country fallback photographs are identified as country images.
- Search countries by name, code or capital; filter by continent, save favourites, compare up to three countries, or discover a random destination.
- Country detail panels with capital, currency, maps and links to Wikivoyage.
- Registration and login required for saved trips, with 30-day revocable sessions and cross-device access. Existing legacy guest trips transfer when a new account is created in the same browser.
- Create, edit and delete trips persisted in PostgreSQL in production or SQLite locally.
- Account-scoped trip access; unauthenticated trip API requests are rejected by the server. Public destination browsing and an unsaved draft remain available.
- Dates, day-by-day itinerary, budget allocation, packing checklist and notes.
- JSON export for backups, calendar `.ics` export, and print/PDF layout for a trip.
- EN/RU translation and persistent light, dark or system theme that responds to system changes.
- Responsive layout, labelled forms, native modal focus handling, reduced motion support.
- Server validation, parameterized SQL, same-origin mutation checks, security headers.
- Docker configuration and Python regression tests.

Budgets are illustrative USD planning estimates, not live prices. Country photographs are bundled in `assets-country/`; some city and legacy journey photographs still load from Wikimedia Commons or Unsplash. This is a planner, not a booking service. Register or sign in to save, retrieve or export trips. Public browsing and unsaved planning remain available; the current draft is retained while signing in, but is not stored for guests. Existing guest records are preserved and can transfer when registering from the same browser with its original cookie. Registered users can sign in on another device to retrieve saved trips. Passwords are hashed with PBKDF2; raw passwords are not stored. No email collection or password recovery is provided: use a password manager. Owner administration is available at `/admin` on the Python deployment. Exported JSON files are backups, with no import UI currently implemented. Other visitors cannot list or edit your trips. The deployment operator can access the database.

## Production

See `PUBLISHING.md` for GitHub, public hosting and Google Search Console setup. `SITE_URL` must be set to the actual assigned HTTPS origin to enable indexing and the dynamic sitemap. `GOOGLE_SITE_VERIFICATION` optionally enables HTML-tag ownership verification. `.env.example` lists settings; this app reads real environment variables, not `.env` files automatically.

Use the Dockerfile or install `requirements.txt` and run:

```sh
gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 4 app:application
```

For free hosting, use a Render Python web service with an external Neon PostgreSQL database. Set `DATABASE_URL` to the private connection string in Render environment settings. Never commit this value. The application requires PostgreSQL when running on Render and refuses to silently store production data on its temporary filesystem. No paid disk is needed. See `render.yaml.example` for configuration.

Free Render services sleep after inactivity, so the first visit can take longer. Database and hosting free tiers have usage limits; review each provider's current terms. PostgreSQL data survives web-server restarts; maintain separate backups for recovery. Local development uses SQLite through `DATABASE_PATH` and needs no PostgreSQL dependency.

Terminate HTTPS at the host proxy, which must sanitize forwarding headers. Gunicorn is intended for Linux production; the included preview server is development-only. GitHub Pages cannot run this Python backend.

Original website: https://roam-atlas.onrender.com. Original owner console: https://roam-atlas.onrender.com/admin. Original source repository: https://github.com/TimurBegimkulov/roam-atlas. This source folder does not claim that any of those remote services have been updated. Google indexing is separate from publication and is not guaranteed.

## Verify

```sh
python -m unittest discover -v
node --check app.js
node --check world.js
```

Backend tests cover persistence, CRUD, visitor/account isolation, invalid data, CSRF, static file restrictions, image MIME types, security headers, secure cookies, complete country coverage, city/country photo attribution, search and pagination. Test fixtures explicitly disable inherited production database settings and use disposable local databases. See `VERIFICATION.md` for checks actually performed.


## Owner administration
Open /admin. Set ADMIN_USERNAME and ADMIN_PASSWORD_HASH as hosting environment variables. Generate the hash with admin.password_hash using Python; never commit the password. Login uses PBKDF2-SHA256 (600,000 rounds), one-hour server sessions, five-attempt lockout, same-origin mutation checks and an audit log. Changing the configured password hash invalidates existing sessions. Sessions and lockouts are stored in the persistent database. No claim of a formal security audit is made. The reverse proxy must sanitize forwarding headers; place edge rate limits in front of a high-traffic public deployment.


## Catalog sources and coverage

GeoNames cities15000, countryInfo and alternateNamesV2, downloaded October 2026: https://download.geonames.org/export/dump/ (CC BY 4.0). The bundled derived index covers cities above 15,000 residents and selected administrative centres, not every settlement. Search includes alternate names; Russian labels use language-tagged names where available and fall back to the source name. Country display names use browser Intl data. Geographic inclusion is not a travel safety recommendation.

Selected city photographs use Wikipedia summary metadata matched against city coordinates, with Wikimedia Commons author and licence attribution in `photos.json`. Country photography and source credits are in `country-photos.json`; resized JPEGs are bundled in `assets-country/`. A country photograph may depict one city or landscape in that country; it is not presented as a photograph of every city using the fallback. Source and licence links are available in the country detail panel. A neutral illustration is used if an image cannot load. Daily budgets are generic editable planning scenarios, excluding flights, visas and insurance.
