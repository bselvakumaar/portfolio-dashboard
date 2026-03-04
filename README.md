# Steward Quant Intelligence Platform

## Documentation
- Deployment runbook: `DEPLOYMENT.md`
- User operations manual: `USER_MANUAL.md`

## What it does
- Pulls NSE OHLCV data using `yfinance` (`.NS` tickers)
- Computes RSI, SMA20/50, MACD, ATR, 52-week high proximity, volume spike ratio
- Generates AI sentiment score stub (0-10)
- Computes configurable Steward Score (0-100)
- Pushes batch results to Google Sheets
- Supports FastAPI endpoints and CLI mode

## Run local
```bash
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m app.main --tickers RELIANCE.NS,TCS.NS
python -m app.main --serve
```

## Endpoints
- `GET /health`
- `GET /run`
- `POST /run`
- `GET /dashboard`
- `POST /dashboard`
- `GET /dashboard/ui`
- `GET /top-picks?top_n=5`
- `GET /market/snapshot?top_n=10`
- `POST /portfolio/analyze`

## Dashboard Features
- Prediction metrics: 21-day return forecast, downside risk, confidence, recommendation
- Top picks ranking across requested universe
- Synthetic portfolio allocation with risk-adjusted weights
- Portfolio metrics: expected 21-day return, expected PnL, average score, diversification index

## CLI Dashboard Mode
```bash
python -m app.main --tickers RELIANCE.NS,TCS.NS,HDFCBANK.NS,INFY.NS,ICICIBANK.NS --dashboard --top-n 5 --capital 1000000 --no-sheets
```

## Google Sheets setup
1. Enable Google Sheets API in your GCP project.
2. Create service account and grant sheet edit access to its email.
3. Set `GOOGLE_SHEETS_ID`, `GOOGLE_SHEETS_RANGE`.
4. Provide auth via `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_SERVICE_ACCOUNT_FILE`.

## Cloud Run deploy
```bash
gcloud builds submit --tag gcr.io/<PROJECT_ID>/steward-quant:latest
gcloud run deploy steward-quant \
  --image gcr.io/<PROJECT_ID>/steward-quant:latest \
  --region <REGION> \
  --platform managed \
  --allow-unauthenticated
```

## Cloud Scheduler
```bash
gcloud scheduler jobs create http steward-quant-daily \
  --location <REGION> \
  --schedule "0 16 * * 1-5" \
  --http-method GET \
  --uri https://<CLOUD_RUN_URL>/run \
  --time-zone "Asia/Kolkata"
```


