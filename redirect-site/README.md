# redirect-site

A static redirect that lives alongside the Dockerized Flask app in this repo.
It permanently redirects the old Render URL `skipping-stones.onrender.com` to the
Pi-hosted app at `https://skipping-stones.duckdns.org`, preserving path + query.

This folder is **not** used by the Docker/Flask app or the Pi — it exists only so
Render can deploy it as a separate **Static Site** from the same repo.

## Deploy on Render (dashboard)

1. Free up the name: delete or rename the existing `skipping-stones` web service so
   the `skipping-stones.onrender.com` subdomain is released.
2. **New → Static Site**, connect this repo (`zvipo/skipping-stones`).
3. Settings:
   - **Name:** `skipping-stones` (to reclaim `skipping-stones.onrender.com`)
   - **Build Command:** *(leave empty)*
   - **Publish Directory:** `redirect-site`
4. Create. `skipping-stones.onrender.com/foo?x=1` then 301s to
   `skipping-stones.duckdns.org/foo?x=1`.

The Docker web service and this static site are two independent Render services that
happen to share one repo — they don't interfere.
