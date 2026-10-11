# Roam Atlas — publication checklist

The source is a complete runnable travel planner. The GitHub repository is https://github.com/TimurBegimkulov/roam-atlas. Public deployment is pending; no hosting URL is claimed.

1. Create a GitHub repository and push this project's `main` branch. Do not upload `data/`, credentials or `.env` files. The test workflow runs automatically.
2. Connect a Python web service to that repository. Select the Free plan, with no disk. `render.yaml.example` describes this configuration. Create a free Neon PostgreSQL database and save its private connection string as `DATABASE_URL` in Render, never in GitHub. Complete any required account authorization first.
3. Deploy with the provided start command and external `DATABASE_URL`. Check `/api/health`, then create, reload, edit and delete a test trip over HTTPS. Verify another visitor cannot access it.
4. Set `SITE_URL` to the actual assigned public HTTPS origin, with no subpath. Until this variable is valid, the site explicitly disables indexing. Set it through hosting environment settings, not a committed secrets file.
5. After restarting, verify the homepage canonical URL, `/robots.txt`, and `/sitemap.xml` all use the actual public origin. The public destination cards are server-rendered; personal trips and API responses are excluded from indexing.
6. Open the public URL on a phone using mobile data. Check EN/RU, the modal form, save/reload, light/dark mode, and image loading. Localhost is never the public phone link.
7. Add the public origin as a URL-prefix property in Google Search Console. Copy the HTML-tag verification value into `GOOGLE_SITE_VERIFICATION`, restart the service, and verify ownership. Submit `sitemap.xml` and request indexing of the homepage. This requires the owner's Google account access.

A normal hosted HTTPS subdomain is enough to open the app on phones. A custom domain is optional and requires availability checking, registration and DNS configuration. Neither Google indexing nor ranking is guaranteed; crawling may take days or weeks.

Official references:
- https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages (Pages hosts static websites, not a running Python backend)
- https://render.com/docs/free (free hosting limits)
- https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl (Search Console and indexing)
