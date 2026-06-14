# India Index & Stock Dashboard

This project generates a static HTML dashboard for Indian indices and your selected stock watchlist.

## What it does
- Fetches live index data from NSE India.
- Calculates the percentage down from the 52-week high and up from the 52-week low.
- Fetches live stock data for the configured watchlist using Yahoo Finance.
- Renders a static `public/index.html` page.
- Publishes the page to GitHub Pages using GitHub Actions.

## Files
- `fetch_dashboard.py`: Python script that fetches data and renders HTML.
- `dashboard_template.html`: HTML template used by the script.
- `.github/workflows/generate-dashboard.yml`: GitHub Actions flow to build and publish the page.
- `requirements.txt`: Python dependencies.

## Setup locally
1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the dashboard builder:
   ```bash
   python fetch_dashboard.py
   ```
4. Open the generated page:
   ```bash
   xdg-open public/index.html
   ```

## Change the tracked indexes or stocks
Edit `fetch_dashboard.py` and update:
- `NSE_INDEXES` for index names.
- `STOCKS` for ticker symbols like `RELIANCE.NS`, `TCS.NS`, `INFY.NS`.

> Note: The script currently uses `NIFTY SMALLCAP 100` because `NIFTY SMALLCAP 150` is not published in the same NSE index endpoint.

## GitHub Actions / GitHub Pages
- The workflow runs daily on weekdays after market hours and on manual dispatch.
- It generates `public/index.html`.
- `peaceiris/actions-gh-pages` deploys the `public/` folder to the `gh-pages` branch.

### Enable GitHub Pages
1. Go to your repository settings.
2. Under **Pages**, set the source to `gh-pages` branch and `/` root.
3. Save and wait for the site URL.

## Notes
- The NSE endpoint uses browser-style headers, so the script includes a standard `User-Agent` header.
- If the page does not update, run the script manually locally or trigger the workflow from GitHub.
