# Roam Atlas — publication checklist

The source is a complete runnable travel planner. The GitHub repository is https://github.com/TimurBegimkulov/roam-atlas and the Python service is https://roam-atlas.onrender.com. A source update becomes public after its complete commit has successfully deployed to that service.

The prepared, not-yet-published Sites version is designed to host the redesigned frontend and uses a restricted same-origin proxy to the existing Render Python API. It does not replace or redeploy that Python service. The new catalogue and validation logic in this source become active on the original service only after a separate deployment. The frontend retains compatibility with the original API, including a bundled country list and country-photo fallback.

Browser guest cookies belong to each website separately. A visitor should sign in to an existing account to access its saved plans across the Sites and original Render websites. Do not claim that guest sessions or device-local favourites have been automatically migrated.

## Update the existing Roam Atlas service

Use this path to upgrade `roam-atlas.onrender.com` while keeping its existing accounts, trips and public address.

1. Open the existing Render service and confirm its connected repository, branch and deployed commit. Retain the current `DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`, `SITE_URL` and any `GOOGLE_SITE_VERIFICATION` value in the hosting environment. Do not copy private values into this source or the chat. Keep the service connected to its existing PostgreSQL database; a newly created database starts empty.
2. Take a restorable backup of that existing database through its provider and record the current deployed commit for rollback. This update does not require a replacement database or a data migration.
3. Run the checks in `README.md`, then update the connected repository with this project, including `country-photos.json` and all of `assets-country/`. Do not upload `data/`, credentials or `.env` files. Preserve any service-specific configuration already maintained in the repository.
4. Keep the existing service's database and environment settings. For the Python runtime, the build command is `pip install -r requirements.txt`; the start command is `gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 app:application`. For an existing Docker service, use the included Dockerfile. Do not use `start-local.cmd` in production: it deliberately selects a separate local SQLite database.
5. Deploy the updated commit on the existing service. If deployment fails, inspect the Render build/runtime logs and use its previous deployed commit for rollback. Do not recreate or clear the database to address an application startup failure.
6. Perform the post-deployment checks below, including signing in to an existing account and confirming that its earlier trips are still present.

## Create a separate new installation

Use this path only when you intentionally want a separate site and an empty database. Connect a Python web service to the intended repository, then create its PostgreSQL database and store the private connection string as `DATABASE_URL` in hosting settings. `render.yaml.example` is a configuration example; rename it to `render.yaml` only when choosing Render's Blueprint workflow. Manual service setup can use the build/start commands above without renaming it.

Set `SITE_URL` to the actual assigned public HTTPS origin, with no subpath. Until this variable is valid, the Python site disables indexing. Configure `ADMIN_USERNAME` and `ADMIN_PASSWORD_HASH` if this separate installation needs the owner console. Keep credentials in hosting settings, not committed files. Review the provider's current plan and database limits when choosing hosting.

## Post-deployment checks

### Operation while the owner's laptop is off

Run the complete Python application as the Render web service, with its existing durable PostgreSQL database. Do not configure production to call a localhost URL, a laptop tunnel or a local SQLite file. A successfully deployed Render service and hosted database operate independently of the owner's laptop.

If the existing service uses Render's Free compute plan, it sleeps after 15 minutes without inbound traffic and starts again on the next request, which can take about a minute. This is a hosting-plan limitation, not a dependence on the laptop. Render Free Postgres expires after 30 days; confirm the existing database provider and plan before treating it as long-term storage. Preserve the current database and its records while checking these settings. See [Render's current free-instance limits](https://render.com/docs/free).

For each release, verify the public Render address with the local preview stopped. The atlas release published on 2026-10-18 passed public photograph, search and trip-persistence checks after its local server was stopped. The account-required update must additionally pass the authorization checks below. A phone on mobile data can independently confirm public access; an actual laptop power-off test is optional and has not been claimed by the automated checks.

### Application checks

1. Check `/api/health` and public destination discovery. Unauthenticated `/api/trips` GET/POST/PUT/DELETE requests must return HTTP 401 with `authentication_required`, including requests with a legacy guest cookie or an expired user session. Then sign in with a test account and verify saved trips, create a temporary test trip, reload it and edit it over HTTPS. Confirm a separate account cannot access that trip, then delete only the test trip from its owner session. The health endpoint alone does not test the database connection. Preserve existing accounts, guest records and production credentials.
2. Verify `/api/countries` has 250 current entries and `/assets-country/fr.jpg` returns a photograph. Check country/city search and an empty territory such as Antarctica.
3. Verify the homepage canonical URL, `/robots.txt`, and `/sitemap.xml` use the actual public origin. Personal trips and API responses are excluded from indexing.
4. Open the public URL on a phone using mobile data. Check EN/RU, the trip picker, save/reload, light/dark/system appearance, image loading, favourites and comparison. Check calendar and print export separately. Localhost is never the public phone link.
5. If Search Console is not already configured and indexing is wanted, add the public origin as a URL-prefix property. Set `GOOGLE_SITE_VERIFICATION` to the supplied HTML-tag value, restart, verify ownership and submit `sitemap.xml`. Preserve an existing verified property and verification value when updating the same site. This step requires the owner's Google account access.

A normal hosted HTTPS subdomain is enough to open the app on phones. A custom domain is optional and requires availability checking, registration and DNS configuration. Neither Google indexing nor ranking is guaranteed; crawling may take days or weeks.

Official references:
- https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages (Pages hosts static websites, not a running Python backend)
- https://render.com/docs/free (free hosting limits)
- https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl (Search Console and indexing)
