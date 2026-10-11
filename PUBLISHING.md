# Roam Atlas — publication checklist

The source is a complete runnable travel planner. A public deployment is still pending account access. The repository name to use is `roam-atlas` (if available); no domain or provider URL has been reserved or claimed.

1. Create a GitHub repository and push this project's `main` branch. Do not upload `data/`, credentials or `.env` files. The test workflow runs automatically.
2. Connect a Python web service to that repository. `render.yaml.example` describes a single Render service with a persistent disk; it is an example, not a deployed resource. Confirm the current cost before selecting its paid plan.
3. Deploy with the provided start command and persistent `DATABASE_PATH`. Check `/api/health`, then create, reload, edit and delete a test trip over HTTPS. Verify another visitor cannot access it.
4. Set `SITE_URL` to the actual assigned public HTTPS origin, with no subpath. Until this variable is valid, the site explicitly disables indexing. Set it through hosting environment settings, not a committed secrets file.
5. After restarting, verify the homepage canonical URL, `/robots.txt`, and `/sitemap.xml` all use the actual public origin. The public destination cards are server-rendered; personal trips and API responses are excluded from indexing.
6. Open the public URL on a phone using mobile data. Check EN/RU, the modal form, save/reload, light/dark mode, and image loading. Localhost is never the public phone link.
7. Add the public origin as a URL-prefix property in Google Search Console. Copy the HTML-tag verification value into `GOOGLE_SITE_VERIFICATION`, restart the service, and verify ownership. Submit `sitemap.xml` and request indexing of the homepage. This requires the owner's Google account access.

A normal hosted HTTPS subdomain is enough to open the app on phones. A custom domain is optional and requires availability checking, registration and DNS configuration. Neither Google indexing nor ranking is guaranteed; crawling may take days or weeks.

Official references:
- https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages (Pages hosts static websites, not a running Python backend)
- https://render.com/docs/disks (persistent storage requirements)
- https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl (Search Console and indexing)
