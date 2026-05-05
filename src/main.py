"""Weekly entrypoint: scrape Miami-Dade auctions and push to Google Sheets."""
from __future__ import annotations

import logging
import os
import sys

from src.scrapers import miami_dade
from src.sheets import google_sheets


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    log = logging.getLogger("forcloser")

    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    worksheet = os.environ.get("GOOGLE_WORKSHEET_NAME", "Miami-Dade")
    lookahead = int(os.environ.get("LOOKAHEAD_DAYS", "14"))

    log.info("Scraping Miami-Dade for next %d days...", lookahead)
    auctions = list(miami_dade.scrape(lookahead_days=lookahead))
    log.info("Got %d auctions", len(auctions))

    rows = [a.as_row() for a in auctions]
    google_sheets.write(sheet_id, worksheet, miami_dade.Auction.header(), rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
