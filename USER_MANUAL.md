# User Manual - Steward Quant Intelligence Platform

## 1. Purpose
Use this system to:
- Score NSE stocks with quant + sentiment model
- Generate predictions and top picks
- Build synthetic portfolio allocations
- Push results to Google Sheets

## 2. Start the Application (Local)
```powershell
cd "D:\Steward FinTech Platform\steward-quant"
.\.venv\Scripts\Activate.ps1
python -m app.main --serve
```

## 3. Main Interfaces
- Dashboard UI: `http://127.0.0.1:8080/dashboard/ui`
- Health check: `http://127.0.0.1:8080/health`
- Scoring trigger: `http://127.0.0.1:8080/run`
- Top picks: `http://127.0.0.1:8080/top-picks?top_n=5`
- Market pulse: `http://127.0.0.1:8080/market/snapshot?top_n=10`
- Portfolio analyze API: `http://127.0.0.1:8080/portfolio/analyze`

## 4. Dashboard Workflow
1. Open `/dashboard/ui`
2. Enter tickers (comma separated, `.NS` format)
3. Set:
   - `Top Picks` count
   - `Capital` for synthetic portfolio
4. Click `Run Dashboard`
5. Review:
   - Market overview metrics
   - Top picks table
   - Portfolio allocation table
   - Projection board (3D/5D/7D/21D)
   - Top gainers and losers (10+ scripts)
   - Sector-wise performance
   - Score vs return chart
   - Recommendation mix chart

## 5. API Usage

### POST `/run`
Request:
```json
{
  "tickers": ["RELIANCE.NS", "TCS.NS", "INFY.NS"],
  "push_to_sheets": true
}
```

### POST `/dashboard`
Request:
```json
{
  "tickers": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"],
  "top_n": 5,
  "capital": 1000000,
  "push_to_sheets": false
}
```

## 6. CLI Usage

### Scoring only
```powershell
python -m app.main --tickers RELIANCE.NS,TCS.NS --no-sheets
```

### Dashboard + top picks + synthetic portfolio
```powershell
python -m app.main --tickers RELIANCE.NS,TCS.NS,HDFCBANK.NS,INFY.NS,ICICIBANK.NS --dashboard --top-n 5 --capital 1000000 --no-sheets
```

## 7. Understanding Outputs
- `final_score`: Steward score (0-100)
- `prediction.predicted_return_pct`: 21-day expected return
- `prediction.downside_risk_pct`: 21-day downside estimate
- `prediction.confidence`: model confidence (0-1)
- `recommendation`: `STRONG_BUY`, `BUY`, `HOLD`, `AVOID`

## 8. Google Sheets Updates
To enable sheet writes:
- Set `ENABLE_SHEETS_UPDATE=true`
- Set valid:
  - `GOOGLE_SHEETS_ID`
  - `GOOGLE_SHEETS_RANGE`
  - `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_SERVICE_ACCOUNT_FILE`
- Share sheet with service account email as `Editor`

## 9. Troubleshooting
- `ModuleNotFoundError`: activate `.venv` and run `pip install -r requirements.txt`
- `FileNotFoundError` on service account key: fix path in `GOOGLE_SERVICE_ACCOUNT_FILE`
- `Google Sheets update failed`: verify API enabled, sheet shared, credentials valid
- No ticker data: ensure `.NS` suffix and market-hours/network availability

## 10. Recommended Daily Process
1. Run `/dashboard/ui`
2. Check top picks and recommendation mix
3. Review synthetic portfolio summary
4. Trigger `/run` if you want Google Sheets to be refreshed
