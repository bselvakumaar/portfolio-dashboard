import json
import logging
from typing import Sequence

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class GoogleSheetsService:
    def __init__(
        self,
        sheets_id: str,
        target_range: str,
        service_account_file: str = "",
        service_account_json: str = "",
    ) -> None:
        self.sheets_id = sheets_id
        self.target_range = target_range
        self.service_account_file = service_account_file
        self.service_account_json = service_account_json
        self.client = self._build_client()

    def _build_client(self):
        if self.service_account_json:
            info = json.loads(self.service_account_json)
            credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        elif self.service_account_file:
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=SCOPES,
            )
        else:
            raise ValueError("Missing service account credentials for Google Sheets API")
        return build("sheets", "v4", credentials=credentials, cache_discovery=False)

    def batch_update_rows(self, rows: Sequence[Sequence[object]]) -> dict:
        if not self.sheets_id:
            raise ValueError("GOOGLE_SHEETS_ID is required")
        if not rows:
            return {"updated": False, "reason": "no_rows"}

        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [{"range": self.target_range, "majorDimension": "ROWS", "values": list(rows)}],
        }
        response = (
            self.client.spreadsheets()
            .values()
            .batchUpdate(spreadsheetId=self.sheets_id, body=body)
            .execute()
        )
        total_cells = response.get("totalUpdatedCells", 0)
        logger.info(
            "Google Sheets update complete",
            extra={"sheets_id": self.sheets_id, "target_range": self.target_range, "updated_cells": total_cells},
        )
        return {"updated": True, "updated_cells": total_cells}
