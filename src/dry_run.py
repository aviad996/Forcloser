"""Dry-run: scrape Miami-Dade and print results without touching Google Sheets.

Used by the `scraper-dry-run` GitHub Action to verify the scraper works against the
live site, without needing any credentials.
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import asdict

from src.scrapers import miami_dade


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    log = logging.getLogger("dry-run")

    lookahead = int(os.environ.get("LOOKAHEAD_DAYS", "14"))
    log.info("Scraping Miami-Dade for next %d days (dry-run, no Sheets write)...", lookahead)

    auctions = list(miami_dade.scrape(lookahead_days=lookahead))
    log.info("=" * 60)
    log.info("RESULT: found %d auctions", len(auctions))
    log.info("=" * 60)

    if not auctions:
        log.error("No auctions parsed — site markup likely changed or site unreachable.")
        log.error("Check the warnings above for which dates returned 0 rows.")
        return 1

    by_date: dict[str, int] = {}
    for a in auctions:
        by_date[a.sale_date] = by_date.get(a.sale_date, 0) + 1
    log.info("Breakdown by sale date:")
    for d in sorted(by_date):
        log.info("  %s: %d", d, by_date[d])

    log.info("Sample (first 3):")
    for a in auctions[:3]:
        for k, v in asdict(a).items():
            log.info("  %-20s %s", k, v)
        log.info("  ---")

    return 0


if __name__ == "__main__":
    sys.exit(main())
