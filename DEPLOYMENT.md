# Deployment Runbook - Steward Quant Intelligence Platform

## 1. Prerequisites
- GCP project with billing enabled
- `gcloud` CLI installed and authenticated
- Docker/Cloud Build access
- Service account JSON secret prepared for Google Sheets write access

## 2. Enable Required GCP Services
```bash
gcloud config set project <PROJECT_ID>
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com cloudscheduler.googleapis.com
```

## 3. Create Secret for Google Service Account JSON
```bash
gcloud secrets create steward-quant-sa-json --replication-policy=automatic
gcloud secrets versions add steward-quant-sa-json --data-file=steward-quant-key.json
```

## 4. Build and Push Container
```bash
gcloud builds submit --tag gcr.io/<PROJECT_ID>/steward-quant:latest
```

## 5. Deploy Cloud Run Service
```bash
gcloud run deploy steward-quant \
  --image gcr.io/<PROJECT_ID>/steward-quant:latest \
  --region <REGION> \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars APP_NAME="Steward Quant Intelligence Platform",APP_ENV=prod,LOG_LEVEL=INFO,ENABLE_SHEETS_UPDATE=true,DEFAULT_TICKERS=RELIANCE.NS,TCS.NS,HDFCBANK.NS,INFY.NS,ICICIBANK.NS,DATA_PERIOD=6mo,DATA_INTERVAL=1d,RETRY_ATTEMPTS=3,RETRY_BACKOFF_SECONDS=1.5,AI_SENTIMENT_PROVIDER=stub,GOOGLE_SHEETS_ID=15V2Ns_aFbjtYyHbncSb0jMo98WEetNene4Yv_T5bPOI,GOOGLE_SHEETS_RANGE=Sheet1!A1 \
  --set-secrets GOOGLE_SERVICE_ACCOUNT_JSON=steward-quant-sa-json:latest
```

## 6. Grant Cloud Run Runtime Access to Secret
```bash
gcloud secrets add-iam-policy-binding steward-quant-sa-json \
  --member=serviceAccount:<PROJECT_NUMBER>-compute@developer.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

If you deploy Cloud Run with a custom runtime service account, grant access to that account instead.

## 7. Validate Deployment
```bash
curl https://<CLOUD_RUN_URL>/health
curl https://<CLOUD_RUN_URL>/run
curl https://<CLOUD_RUN_URL>/dashboard
```

## 8. Configure Scheduler (Automated Daily Run)
```bash
gcloud scheduler jobs create http steward-quant-daily \
  --location <REGION> \
  --schedule "0 16 * * 1-5" \
  --http-method GET \
  --uri https://<CLOUD_RUN_URL>/run \
  --time-zone "Asia/Kolkata"
```

For private Cloud Run services, configure Scheduler with OIDC token:
- `--oidc-service-account-email=<INVOKER_SA_EMAIL>`
- `--oidc-token-audience=https://<CLOUD_RUN_URL>`

## 9. Operational Checks
- Cloud Run logs: verify no `Google Sheets update failed` errors
- Sheet updates: ensure new rows are appended/updated at configured range
- Latency: monitor per-run duration and external API delays (`yfinance`)

## 10. Rollback
```bash
gcloud run revisions list --service steward-quant --region <REGION>
gcloud run services update-traffic steward-quant --region <REGION> --to-revisions <GOOD_REVISION>=100
```
