# DataCleaner

Upload a messy customer spreadsheet and download two verifiable results: `clean_customers.csv` with import-ready rows, and `errors.csv` with the row, column, and reason for every rejection. The fictional sample contains 18 records and produces **8 valid, 8 invalid, and 2 duplicate rows**.

## Try the fictional sample

1. Download [sample_customers.csv](examples/sample_customers.csv) or [sample_customers.xlsx](examples/sample_customers.xlsx). The demo page also offers both files.
2. Upload either file. The summary should show **18 received, 8 valid, 8 invalid, and 2 duplicates**.
3. Download both results and compare them with [expected_clean_customers.csv](examples/expected_clean_customers.csv) and [expected_errors.csv](examples/expected_errors.csv). The report has 11 issue entries because row 13 has two errors.

The [before-and-after image](portfolio/before_after.png) shows the source, summary, clean output, and selected report rows. See the [upload screenshot](portfolio/01_upload.png), [results screenshot](portfolio/02_results.png), and [short demo video](portfolio/demo.webm) for the interface flow.

## Install and test

Requires Python 3.9 or later. On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app:app --reload
```

Open `http://127.0.0.1:8000`. On macOS or Linux, use `.venv/bin/python` in place of `.\.venv\Scripts\python.exe`. The same test command runs in [GitHub Actions](.github/workflows/tests.yml) after a push.

## Deploy on Render's free tier

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Alex-Lize/DataCleaner)

The [render.yaml](render.yaml) Blueprint defines one Python web service on the `free` plan. Click the button, sign in to Render, review the service, and deploy. Later updates require a manual deploy. The app binds to Render's `PORT` and needs no database. [Render's free web services](https://render.com/docs/free) sleep after 15 minutes without traffic, so the first visit after inactivity can take about a minute. No real customer data is included in this repository; use fictional data in the public demo.

## Rules and API

The full cleaning contract is in [RULES_V1.md](RULES_V1.md). `name` and `email` are required; `phone` and `birth_date` may be empty. The first valid normalized email enters the clean file. Later rows with that email appear in the error report, which points to the first accepted row.

`POST /api/process?filename=customers.csv` receives file bytes in the request body with `Content-Type: application/octet-stream`. It returns the summary and download URLs:

```json
{
  "job_id": "<identifier>",
  "summary": {"received": 18, "valid": 8, "invalid": 8, "duplicate": 2},
  "downloads": {
    "clean": "/api/result/<identifier>/clean",
    "errors": "/api/result/<identifier>/errors"
  }
}
```

`GET /api/sample/csv` and `GET /api/sample/xlsx` download the fictional inputs. `GET /api/result/{job_id}/clean` returns `clean_customers.csv`; `GET /api/result/{job_id}/errors` returns `errors.csv`. Results remain in memory for one hour. Restarting the server removes them. Run one server process for this version.

## Version 1 limits

- Each upload is limited to 5 MB and 10,000 data rows.
- Email validation supports a practical subset of addresses and does not contact the provider.
- Phone normalization covers Brazilian numbers with area codes and does not verify that a number exists.
- Name capitalization does not restore accents or special personal spelling.
- Processing is synchronous. Larger files, job history, authentication, and persistent storage are outside this version.