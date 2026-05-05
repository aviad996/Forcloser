"""Miami-Dade foreclosure auction scraper.

Source: https://www.miamidade.realforeclose.com (Grant Street RealAuction platform).
The site exposes an internal AJAX endpoint that returns JSON for a given auction date.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from typing import Iterator

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

BASE_URL = "https://www.miamidade.realforeclose.com"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


@dataclass
class Auction:
    county: str
    sale_date: str
    case_number: str
    property_address: str
    folio: str
    plaintiff: str
    opening_bid: str
    status: str
    auction_url: str
    scraped_at: str

    def as_row(self) -> list[str]:
        d = asdict(self)
        return [d[k] for k in (
            "county", "sale_date", "case_number", "property_address",
            "folio", "plaintiff", "opening_bid", "status",
            "auction_url", "scraped_at",
        )]

    @staticmethod
    def header() -> list[str]:
        return [
            "County", "Sale Date", "Case #", "Property Address",
            "Folio", "Plaintiff", "Opening Bid", "Status",
            "Auction URL", "Scraped At",
        ]


def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/json"})
    # The site sets a session cookie after the disclaimer page. A blind GET to root
    # is enough to receive it for subsequent requests.
    s.get(f"{BASE_URL}/index.cfm", timeout=20)
    return s


def _fetch_day(session: requests.Session, day: date) -> list[dict]:
    date_str = day.strftime("%m/%d/%Y")
    url = f"{BASE_URL}/index.cfm"
    params = {
        "zaction": "AUCTION",
        "Zmethod": "PREVIEW",
        "AUCTIONDATE": date_str,
    }
    r = session.get(url, params=params, timeout=30)
    r.raise_for_status()
    return _parse_day_html(r.text, day)


_LABEL_MAP = {
    "case #": "case_number",
    "case number": "case_number",
    "property address": "property_address",
    "folio": "folio",
    "parcel id": "folio",
    "plaintiff": "plaintiff",
    "plaintiff max bid": "opening_bid",
    "opening bid": "opening_bid",
    "auction starts": "status",
    "auction sold": "status",
    "auction status": "status",
}


def _parse_day_html(html: str, day: date) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict] = []

    # RealAuction renders each auction as a .AUCTION_ITEM block. Field rows inside use
    # .AD_LBL (label) and .AD_DTA (data) classes. We tolerate both old and new markup.
    items = soup.select(".AUCTION_ITEM, div[id^='Auction_']")
    for item in items:
        record = {
            "case_number": "",
            "property_address": "",
            "folio": "",
            "plaintiff": "",
            "opening_bid": "",
            "status": "",
            "auction_url": "",
        }
        for label_el in item.select(".AD_LBL"):
            label = label_el.get_text(strip=True).rstrip(":").lower()
            data_el = label_el.find_next(class_="AD_DTA")
            if not data_el:
                continue
            key = _LABEL_MAP.get(label)
            if key:
                record[key] = data_el.get_text(" ", strip=True)

        link = item.find("a", href=re.compile(r"AUCTIONID|Zmethod=DETAILS", re.I))
        if link and link.get("href"):
            href = link["href"]
            record["auction_url"] = href if href.startswith("http") else f"{BASE_URL}/{href.lstrip('/')}"

        if any(record.values()):
            results.append(record)

    if not results:
        log.warning("No auctions parsed for %s — site markup may have changed", day)
    return results


def scrape(lookahead_days: int = 14) -> Iterator[Auction]:
    """Yield auctions scheduled within the next `lookahead_days` days."""
    session = _make_session()
    today = date.today()
    now_iso = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    for offset in range(lookahead_days + 1):
        day = today + timedelta(days=offset)
        if day.weekday() >= 5:  # Sat/Sun — Miami-Dade doesn't hold auctions on weekends.
            continue
        try:
            day_records = _fetch_day(session, day)
        except requests.RequestException as e:
            log.error("Failed to fetch %s: %s", day, e)
            continue
        for rec in day_records:
            yield Auction(
                county="Miami-Dade",
                sale_date=day.isoformat(),
                scraped_at=now_iso,
                **rec,
            )
