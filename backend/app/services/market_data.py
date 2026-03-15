from __future__ import annotations

import datetime as dt
import html
import math
import re
import urllib.error
import urllib.request


CURRENT_PRICES_URL = "https://www.eia.gov/todayinenergy/prices.php"
WEEKLY_GAS_HISTORY_URL = (
    "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?f=W&n=PET&s=EMM_EPMR_PTE_NUS_DPG"
)
WTI_HISTORY_URL = "https://www.eia.gov/dnav/pet/hist/RWTCD.htm"

MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
NAMED_DATE_PATTERNS = ("%B %d, %Y", "%b %d, %Y")


class DataUnavailableError(RuntimeError):
    pass


def fetch_url_text(url: str, timeout: float = 20.0) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise DataUnavailableError(f"Unable to fetch {url}: {exc}") from exc
    return raw.decode("utf-8", errors="replace")


def html_to_text(raw_html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw_html)
    text = re.sub(
        r"(?i)</?(?:br|p|div|tr|td|th|li|ul|ol|table|tbody|thead|tfoot|section|article|h\d)[^>]*>",
        "\n",
        text,
    )
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text).replace("\xa0", " ")
    lines = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if line:
            lines.append(line)
    return "\n".join(lines)


def parse_mmddyy(value: str) -> str:
    month, day, year = value.split("/")
    year_int = int(year)
    if year_int < 100:
        year_int += 2000
    return dt.date(year_int, int(month), int(day)).isoformat()


def parse_mmdd_with_year(mmdd: str, year: int) -> str:
    month, day = mmdd.split("/")
    return dt.date(year, int(month), int(day)).isoformat()


def parse_named_date(value: str) -> str:
    for pattern in NAMED_DATE_PATTERNS:
        try:
            return dt.datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            continue
    raise DataUnavailableError(f"Unsupported named date format: {value}")


def extract_current_page_date(lines: list[str]) -> str:
    for index, line in enumerate(lines[:-1]):
        if lines[index + 1] == "Daily Prices":
            return parse_named_date(line)

    for line in lines:
        if re.fullmatch(r"[A-Z][a-z]{2,8} \d{1,2}, \d{4}", line):
            return parse_named_date(line)

    raise DataUnavailableError("Unable to locate the EIA daily prices page date.")


def parse_current_prices(raw_html: str) -> dict:
    text = html_to_text(raw_html)
    lines = text.splitlines()

    current_date = extract_current_page_date(lines)
    spot_date = None
    aaa_date = None
    wti = None
    gas = None
    diesel = None

    for line in lines:
        if line.startswith("Wholesale Spot Petroleum Prices,"):
            match = re.search(r"(\d{1,2}/\d{1,2}/\d{2})", line)
            if match:
                spot_date = parse_mmddyy(match.group(1))
            continue

        if line.startswith("Retail Petroleum Prices (AAA),"):
            match = re.search(r"(\d{1,2}/\d{1,2}/\d{2})", line)
            if match:
                aaa_date = parse_mmddyy(match.group(1))
            continue

        if wti is None:
            match = re.match(r"(?:\(\$/barrel\)\s+)?WTI\s+([0-9.]+)\s+([+\-]?[0-9.]+)", line)
            if match:
                wti = {
                    "value": float(match.group(1)),
                    "pct_change": float(match.group(2)),
                    "date": spot_date,
                }
                continue

        if gas is None:
            match = re.match(
                r"Regular Gasoline U\.S\. Average\s+([0-9.]+)\s+([+\-]?[0-9.]+)",
                line,
            )
            if match:
                gas = {
                    "value": float(match.group(1)),
                    "pct_change": float(match.group(2)),
                    "date": aaa_date,
                }
                continue

        if diesel is None:
            match = re.match(r"Diesel U\.S\. Average\s+([0-9.]+)\s+([+\-]?[0-9.]+)", line)
            if match:
                diesel = {
                    "value": float(match.group(1)),
                    "pct_change": float(match.group(2)),
                    "date": aaa_date,
                }

    if not (current_date and spot_date and aaa_date and wti and gas):
        raise DataUnavailableError("Unable to parse the EIA daily prices page.")

    return {
        "page_date": current_date,
        "spot_close_date": spot_date,
        "aaa_date": aaa_date,
        "wti_daily": wti,
        "aaa_regular_gasoline": gas,
        "aaa_diesel": diesel,
        "source_url": CURRENT_PRICES_URL,
    }


def parse_weekly_gas_history(raw_html: str) -> list[dict]:
    text = html_to_text(raw_html)
    series = []

    for line in text.splitlines():
        stripped = line.strip()
        if not re.match(r"^\d{4}-[A-Za-z]{3}\b", stripped):
            continue

        year = int(stripped[:4])
        matches = re.findall(r"(\d{2}/\d{2})\s+([0-9.]+)", stripped)
        for mmdd, value in matches:
            series.append({"date": parse_mmdd_with_year(mmdd, year), "value": float(value)})

    if not series:
        raise DataUnavailableError("Unable to parse the weekly gasoline history page.")

    series.sort(key=lambda item: item["date"])
    return series


def parse_wti_history(raw_html: str) -> list[dict]:
    text = html_to_text(raw_html)
    series = []
    pattern = re.compile(
        r"^\s*(\d{4})\s+([A-Za-z]{3})-\s*(\d{1,2})\s+to\s+([A-Za-z]{3})-\s*(\d{1,2})\s+(.+)$"
    )

    for line in text.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue

        year = int(match.group(1))
        start_month = MONTHS.get(match.group(2))
        start_day = int(match.group(3))
        value_tokens = re.findall(r"\d+\.\d+", match.group(6))
        if not start_month or not value_tokens:
            continue

        start_date = dt.date(year, start_month, start_day)
        aligned_monday = start_date + dt.timedelta(days=7)
        average_value = sum(float(token) for token in value_tokens) / len(value_tokens)
        series.append({"date": aligned_monday.isoformat(), "value": round(average_value, 4)})

    if not series:
        raise DataUnavailableError("Unable to parse the WTI history page.")

    series.sort(key=lambda item: item["date"])
    return series


def _shock_component(index: int) -> float:
    if 94 <= index <= 120:
        return -28.0 + 0.35 * (index - 94)
    if 180 <= index <= 230:
        return 22.0 * math.sin((index - 180) / 50.0 * math.pi)
    if 265 <= index <= 305:
        return -10.0 + 0.2 * (index - 265)
    if index >= 360:
        return 8.0 + 0.25 * (index - 360)
    return 0.0


def generate_fallback_history(
    start_date: dt.date = dt.date(2018, 5, 14),
    end_date: dt.date = dt.date(2026, 3, 9),
) -> dict:
    gas_series = []
    wti_series = []

    weeks = ((end_date - start_date).days // 7) + 1
    crude_values = []

    for index in range(weeks):
        date_value = start_date + dt.timedelta(days=7 * index)
        seasonal = 8.5 * math.sin(2.0 * math.pi * index / 52.0)
        cyclical = 4.0 * math.cos(2.0 * math.pi * index / 104.0)
        trend = 0.02 * index
        crude = 63.0 + seasonal + cyclical + trend + _shock_component(index)
        crude = max(22.0, crude)
        crude_values.append(crude)
        wti_series.append({"date": date_value.isoformat(), "value": round(crude, 4)})

    gas_prev = 2.42
    for index in range(weeks):
        date_value = start_date + dt.timedelta(days=7 * index)
        crude = crude_values[index]
        crude_lag_1 = crude_values[index - 1] if index >= 1 else crude
        crude_lag_2 = crude_values[index - 2] if index >= 2 else crude_lag_1
        spring = 0.13 * math.sin(2.0 * math.pi * (index - 8) / 52.0)
        holiday = 0.04 * math.cos(2.0 * math.pi * index / 26.0)
        gas_value = (
            0.58
            + 0.0115 * crude
            + 0.0070 * crude_lag_1
            + 0.0045 * crude_lag_2
            + 0.42 * gas_prev
            + spring
            + holiday
            + 0.022 * math.sin(2.0 * math.pi * index / 17.0)
        )
        gas_value = round(gas_value, 4)
        gas_prev = gas_value
        gas_series.append({"date": date_value.isoformat(), "value": gas_value})

    last_weekly = gas_series[-1]
    last_wti = wti_series[-1]
    return {
        "gasoline": gas_series,
        "wti_weekly": wti_series,
        "current": {
            "page_date": "2026-03-13",
            "spot_close_date": "2026-03-12",
            "aaa_date": "2026-03-12",
            "wti_daily": {"value": 95.61, "pct_change": 10.1, "date": "2026-03-12"},
            "aaa_regular_gasoline": {
                "value": 3.63,
                "pct_change": 0.9,
                "date": "2026-03-12",
            },
            "aaa_diesel": {"value": 4.89, "pct_change": 0.7, "date": "2026-03-12"},
            "weekly_regular_gasoline": {
                "value": round(last_weekly["value"], 3),
                "date": last_weekly["date"],
            },
            "weekly_wti_for_model": {
                "value": round(last_wti["value"], 3),
                "date": last_wti["date"],
            },
            "source_url": CURRENT_PRICES_URL,
        },
        "mode": "fallback",
        "errors": [
            "Live EIA data could not be reached from this environment. Synthetic fallback history is being used for local testing."
        ],
    }


def build_market_dataset() -> dict:
    errors = []
    live_current = None
    live_gas = None
    live_wti = None

    try:
        live_current = parse_current_prices(fetch_url_text(CURRENT_PRICES_URL))
    except Exception as exc:
        errors.append(f"Unable to load current prices from EIA: {exc}")

    try:
        live_gas = parse_weekly_gas_history(fetch_url_text(WEEKLY_GAS_HISTORY_URL))
    except Exception as exc:
        errors.append(f"Unable to load weekly gasoline history from EIA: {exc}")

    try:
        live_wti = parse_wti_history(fetch_url_text(WTI_HISTORY_URL))
    except Exception as exc:
        errors.append(f"Unable to load WTI history from EIA: {exc}")

    if live_current and live_gas and live_wti:
        latest_weekly_gas = live_gas[-1]
        latest_weekly_wti = live_wti[-1]
        live_current["weekly_regular_gasoline"] = {
            "value": latest_weekly_gas["value"],
            "date": latest_weekly_gas["date"],
        }
        live_current["weekly_wti_for_model"] = {
            "value": latest_weekly_wti["value"],
            "date": latest_weekly_wti["date"],
        }
        return {
            "current": live_current,
            "gasoline": live_gas,
            "wti_weekly": live_wti,
            "mode": "live",
            "errors": [],
        }

    fallback = generate_fallback_history()
    if live_current:
        fallback["current"].update(live_current)
    if live_gas:
        fallback["gasoline"] = live_gas
        latest_weekly_gas = live_gas[-1]
        fallback["current"]["weekly_regular_gasoline"] = {
            "value": latest_weekly_gas["value"],
            "date": latest_weekly_gas["date"],
        }
    if live_wti:
        fallback["wti_weekly"] = live_wti
        latest_weekly_wti = live_wti[-1]
        fallback["current"]["weekly_wti_for_model"] = {
            "value": latest_weekly_wti["value"],
            "date": latest_weekly_wti["date"],
        }

    if live_current or live_gas or live_wti:
        fallback["mode"] = "hybrid"
        fallback["errors"] = errors
    return fallback
