"""Google Sheets writer.

Each weekly run creates a NEW worksheet named like 'Miami-Dade 2026-05-05'. Previous
weeks' tabs are never touched — running again on the same day just refreshes that
day's tab in place.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date
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


def write(sheet_id: str, worksheet_base: str, header: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    client = gspread.authorize(_credentials())
    sheet = client.open_by_key(sheet_id)

    title = f"{worksheet_base} {date.today().isoformat()}"
    try:
        ws = sheet.worksheet(title)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=title, rows=max(len(rows) + 50, 200), cols=max(len(header) + 2, 12))

    ws.update("A1", [list(header)] + [list(r) for r in rows], value_input_option="USER_ENTERED")
    ws.format("A1:Z1", {"textFormat": {"bold": True}})
    ws.freeze(rows=1)

    log.info("Wrote %d rows to new tab '%s'", len(rows), title)
