# Verification — 2026-10-16

This pre-deployment report describes the upgraded source and its local checks. Public deployment is verified separately against the deployed commit.

## Passed

- Python backend regression suite: 89 tests passed in 43.246 seconds. Coverage: persistence, CRUD, account/guest isolation, login/logout and expiry, CSRF/origin checks, validation, admin access, static allowlist, JPEG GET/HEAD MIME handling, search and pagination.
- Exactly 250 current countries/territories have readable bundled JPEGs and author/source/licence metadata. Retired codes AN/CS are excluded.
- JavaScript syntax checks.
- Happy DOM interaction checks with mocked APIs: 250 countries in both selectors; local atlas before delayed backend; EN/RU; system/light/dark themes; searches including Timor-Leste/Antarctica; favourites; comparison; details; remote city picker; itinerary/packing; create/edit/delete; unsupported territory empty state; account mode, invalid login, login/logout. These are DOM tests, not browser rendering tests.
- Follow-up DOM regression checks: a failed city page is retried without skipping it; the load-more label recovers; a delayed search from a closed form does not reset the next trip's destination.
- Real local Python HTTP server with disposable SQLite: homepage, health, all 250 countries, Dili search, Antarctica empty state, local JPEG responses, trip create/reload/edit/delete and isolation between two visitors passed.
- Windows local launcher isolation checked with temporary SQLite and inherited sentinel production settings. Local database/port overrides are correct and the caller's environment is restored.
- Sites artifact: executable ESM, working homepage, all 250 JPEGs, country endpoint, denied private/admin paths and CSRF rejection.
- Sites proxy: application-cookie allowlist, secure session flags, private no-store responses, checked upstream origin, photo attribution without replacing city descriptions, request-size limits and explicit upstream errors.
- Local previews returned HTTP 200; the native browser panel was queued to show the full Python app. Temporary QA servers are stopped after checks. Use start-local.cmd for an independent local session.
- GitHub and Render integrations are now connected and authorized. The user confirmed Render's My Workspace. Read-only service/deployment inspection succeeded; the existing Render release remains live at commit `82ce2fda31bb6e46b79158c4cbd37ba0c4a24327`.
- On 2026-10-16, the original Render homepage `/` and `/api/health` both returned HTTP 200, and the health response reported `status: ok`. These results verify availability of the existing release, not deployment of this upgraded source.

- Real browser checks at desktop 1280×900 and mobile 390×844: country photographs rendered, both country selectors contained all 250 entries, Timor-Leste discovery found Dili, Antarctica remained discoverable with a clear empty city state, EN/RU and light/dark/system controls worked, favourites survived reload, and country comparison displayed the selected facts and images. Mobile content fit the viewport without horizontal overflow.
- In an isolated local browser session, a Dili trip with dates, budget, itinerary and packing state was created, reloaded, edited and deleted successfully. The calendar download contained the expected all-day dates and trip details.
- Registration, logout and subsequent login succeeded in the isolated local database; no production account was created during these checks.
- Country-photo recovery regression checks: a simulated first-request failure recovered automatically; a persistent failure stopped after one retry while the country catalogue remained usable.
- The ChatGPT Codex Connector installation is now confirmed for the owner account with access restricted to `roam-atlas`. Uploading a prepared photo blob succeeded; the previous GitHub write-access blocker is resolved.

## Deployment follow-up

- Earlier automated browser-rendering attempts failed under Windows pipe restrictions; the subsequent real-browser checks above passed. Print/PDF output has not been visually verified.
- The original Render availability checks now pass, following HTTP 502 responses observed on 2026-10-15. No successful live account/trip integration is claimed for this upgraded release.
- Public-release checks must confirm the complete source commit is live on Render and public health, catalogue and photo checks pass.
- Sites access was changed to public at the user's explicit request (access revision 2). No version was published. Automatic approval review previously rejected source preparation because required approval was disabled, including after narrow filesystem/network permissions were granted. A fresh standard Node child-process check still failed with Windows EPERM on 2026-10-15.
- Python source runs independently with local SQLite. Production PostgreSQL must be checked when deployed with the owner's existing hosting settings.

## Reproduce

    python -m unittest discover -q
    node --check app.js
    node --check world.js

Tests use disposable databases. No production password or database connection string is included.
