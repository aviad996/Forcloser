"""Google Sheets writer.

Authenticates with a Google service account and replaces the contents of a worksheet
with the latest scrape. Existing rows are kept on a sibling 'History' worksheet so
nothing is lost between runs.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Sequence

import gspread
from google.oauth2.service_account import Credentials

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _credentials() -> Credentials:
    inline = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if inline:
        info = json.loads(inline)
        return Credentials.from_service_account_info(info, scopes=SCOPES)

    path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "./service_account.json")
    return Credentials.from_service_account_file(path, scopes=SCOPES)


def _get_or_create_worksheet(sheet, title: str, rows: int = 1000, cols: int = 12):
    try:
        return sheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return sheet.add_worksheet(title=title, rows=rows, cols=cols)


def write(sheet_id: str, worksheet_name: str, header: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    client = gspread.authorize(_credentials())
    sheet = client.open_by_key(sheet_id)

    current = _get_or_create_worksheet(sheet, worksheet_name)
    history = _get_or_create_worksheet(sheet, f"{worksheet_name} – History")

    if history.row_count < 2:
        history.update("A1", [list(header) + ["Run At"]])

    run_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    history_rows = [list(r) + [run_at] for r in rows]
    if history_rows:
        history.append_rows(history_rows, value_input_option="USER_ENTERED")

    current.clear()
    current.update("A1", [list(header)] + [list(r) for r in rows], value_input_option="USER_ENTERED")
    current.format("A1:Z1", {"textFormat": {"bold": True}})

    log.info("Wrote %d rows to '%s' (and appended to history)", len(rows), worksheet_name)
