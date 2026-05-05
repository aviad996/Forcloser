# Forcloser

Weekly pipeline that scrapes Miami-Dade County foreclosure auctions and writes them to a
Google Sheet. Designed to run free on GitHub Actions (no server).

## What it does

1. Hits `miamidade.realforeclose.com` for each weekday in the next 14 days.
2. Parses the auction items (case #, address, folio, plaintiff, opening bid, status).
3. Replaces the contents of the configured Google Sheet worksheet with the latest run,
   and appends the same rows to a sibling `… – History` worksheet so nothing is lost.

## One-time setup

### 1. Create a Google Cloud service account

1. Go to <https://console.cloud.google.com> → create (or pick) a project.
2. Enable the **Google Sheets API**.
3. **IAM & Admin → Service Accounts → Create service account**. Skip role assignment.
4. Open the new service account → **Keys → Add Key → JSON**. Download the file.
5. Note the `client_email` from the JSON — looks like `name@project.iam.gserviceaccount.com`.

### 2. Create the Google Sheet and share it

1. Create a new Google Sheet. Copy its ID from the URL:
   `https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit`.
2. Click **Share** and add the service account `client_email` as **Editor**.

### 3. Add GitHub secrets

In the repo, **Settings → Secrets and variables → Actions**:

| Type   | Name                            | Value                                    |
|--------|---------------------------------|------------------------------------------|
| Secret | `GOOGLE_SHEET_ID`               | the sheet ID from step 2                 |
| Secret | `GOOGLE_SERVICE_ACCOUNT_JSON`   | full contents of the downloaded JSON key |
| Var    | `GOOGLE_WORKSHEET_NAME` *(opt)* | default `Miami-Dade`                     |
| Var    | `LOOKAHEAD_DAYS` *(opt)*        | default `14`                             |

### 4. Trigger the first run

**Actions → Weekly Foreclosure Scrape → Run workflow**. After it finishes (~1 min),
the sheet should be populated.

## Local development

```bash
pip install -r requirements.txt
cp .env.example .env       # fill in values
export $(cat .env | xargs)
export GOOGLE_SERVICE_ACCOUNT_FILE=./service_account.json   # save the JSON key here
python -m src.main
```

## Schedule

Runs every Monday at 08:00 UTC via `.github/workflows/weekly-scrape.yml`. Adjust the
cron expression there to change the cadence.

## Roadmap

- [ ] Texas counties (Harris, Dallas, Tarrant, Bexar) — much harder, each county is its
      own scraper. Will add one at a time.
- [ ] Owner contact enrichment (skip-tracing) — defendant phone/email lookup. Requires
      a paid third-party API (BeenVerified, IDI Data, etc.).
- [ ] Filtering by ZIP / owner type (individual vs LLC) once we have richer data.

## Notes

- Florida foreclosures are **judicial**, so the auction site is the cleanest single
  source for sale data. For pre-sale leads (Lis Pendens), we'd add a separate scraper
  against the Miami-Dade Clerk of Courts CCIS system.
- If a run produces zero rows, the site's HTML structure likely changed — check the
  workflow logs for the warning, then update selectors in `src/scrapers/miami_dade.py`.
