from __future__ import annotations

import datetime as dt
import html
import math
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from app.config import settings
from app.logging_setup import get_logger


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
LOGGER = get_logger("market_data")


class DataUnavailableError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        url: str | None = None,
        error_type: str = "unavailable",
        elapsed_ms: float | None = None,
        metadata: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.error_type = error_type
        self.elapsed_ms = elapsed_ms
        self.metadata = metadata or {}


def _classify_fetch_error(reason: object) -> str:
    if isinstance(reason, socket.gaierror):
        return "dns_resolution_error"
    if isinstance(reason, ssl.SSLError):
        return "tls_error"
    if isinstance(reason, TimeoutError):
        return "timeout_error"
    if isinstance(reason, ConnectionRefusedError):
        return "connection_refused"
    message = str(reason).lower()
    if "timed out" in message:
        return "timeout_error"
    return "url_error"


def _build_url_metadata(url: str) -> dict[str, object]:
    parsed = urllib.parse.urlparse(url)
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    return {
        "scheme": parsed.scheme,
        "host": parsed.hostname,
        "port": port,
        "path": parsed.path,
    }


def fetch_url_payload(url: str, timeout: float | None = None) -> tuple[str, dict]:
    timeout = timeout or settings.source_fetch_timeout_seconds
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    started = time.perf_counter()
    base_meta = _build_url_metadata(url)
    LOGGER.info("source_fetch_start url=%s timeout_seconds=%.1f", url, timeout)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
            metadata = {
                **base_meta,
                "elapsed_ms": elapsed_ms,
                "http_status": getattr(response, "status", None),
                "content_type": response.headers.get("Content-Type"),
                "content_length": response.headers.get("Content-Length"),
                "bytes_read": len(raw),
                "final_url": response.geturl(),
            }
            LOGGER.info(
                "source_fetch_success url=%s status=%s elapsed_ms=%s bytes_read=%s final_url=%s",
                url,
                metadata["http_status"],
                elapsed_ms,
                metadata["bytes_read"],
                metadata["final_url"],
            )
            LOGGER.debug(
                "source_fetch_headers url=%s content_type=%s content_length=%s cache_control=%s server=%s",
                url,
                metadata["content_type"],
                metadata["content_length"],
                response.headers.get("Cache-Control"),
                response.headers.get("Server"),
            )
            return raw.decode("utf-8", errors="replace"), metadata
    except urllib.error.HTTPError as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
        metadata = {
            **base_meta,
            "http_status": exc.code,
        }
        LOGGER.warning(
            "source_fetch_failed url=%s error_type=http_error status=%s elapsed_ms=%s host=%s port=%s",
            url,
            exc.code,
            elapsed_ms,
            metadata["host"],
            metadata["port"],
        )
        raise DataUnavailableError(
            f"Unable to fetch {url}: HTTP {exc.code}",
            url=url,
            error_type="http_error",
            elapsed_ms=elapsed_ms,
            metadata=metadata,
        ) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
        reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
        metadata = {
            **base_meta,
            "reason_type": type(reason).__name__,
            "reason_errno": getattr(reason, "errno", None),
            "reason_strerror": getattr(reason, "strerror", None),
        }
        LOGGER.warning(
            "source_fetch_failed url=%s error_type=%s elapsed_ms=%s host=%s port=%s reason_type=%s reason_errno=%s detail=%s",
            url,
            _classify_fetch_error(reason),
            elapsed_ms,
            metadata["host"],
            metadata["port"],
            metadata["reason_type"],
            metadata["reason_errno"],
            reason,
        )
        raise DataUnavailableError(
            f"Unable to fetch {url}: {reason}",
            url=url,
            error_type=_classify_fetch_error(reason),
            elapsed_ms=elapsed_ms,
            metadata=metadata,
        ) from exc
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
        LOGGER.exception(
            "source_fetch_failed url=%s error_type=unexpected_fetch_error elapsed_ms=%s host=%s port=%s",
            url,
            elapsed_ms,
            base_meta["host"],
            base_meta["port"],
        )
        raise DataUnavailableError(
            f"Unexpected fetch failure for {url}: {type(exc).__name__}: {exc}",
            url=url,
            error_type="unexpected_fetch_error",
            elapsed_ms=elapsed_ms,
            metadata=base_meta,
        ) from exc


def html_to_text(raw_html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw_html)
    text = re.sub(r"(?i)</?(?:td|th)[^>]*>", " ", text)
    text = re.sub(r"(?i)</?tr[^>]*>", "\n", text)
    text = re.sub(
        r"(?i)</?(?:br|p|div|li|ul|ol|table|tbody|thead|tfoot|section|article|h\d|pre)[^>]*>",
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
    raise DataUnavailableError(
        f"Unsupported named date format: {value}",
        error_type="parse_error",
        metadata={"field": "named_date"},
    )


def compact_debug_snippet(text: str, limit: int = 480) -> str:
    return " ".join(text.split())[:limit]


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def extract_current_page_date(text: str, lines: list[str]) -> str:
    heading_match = re.search(r"([A-Z][a-z]{2,8} \d{1,2}, \d{4})\s+Daily Prices\b", text)
    if heading_match:
        return parse_named_date(heading_match.group(1))

    for index, line in enumerate(lines[:-1]):
        if lines[index + 1] == "Daily Prices" and re.fullmatch(
            r"[A-Z][a-z]{2,8} \d{1,2}, \d{4}",
            line,
        ):
            return parse_named_date(line)

    for line in lines:
        if re.fullmatch(r"[A-Z][a-z]{2,8} \d{1,2}, \d{4}", line):
            return parse_named_date(line)

    raise DataUnavailableError(
        "Unable to locate the EIA daily prices page date.",
        error_type="parse_error",
        metadata={"parser": "current_prices", "field": "page_date"},
    )


def extract_current_prices_section(text: str) -> str:
    match = re.search(
        r"Daily Prices\s+(Wholesale Spot Petroleum Prices,.*?)(?=\s+Financial Indicators,|\Z)",
        text,
        flags=re.DOTALL,
    )
    return match.group(1) if match else text


def parse_current_prices(raw_html: str) -> dict:
    text = html_to_text(raw_html)
    lines = text.splitlines()
    section = normalize_whitespace(extract_current_prices_section(text))

    current_date = extract_current_page_date(text, lines)
    spot_date = None
    aaa_date = None
    wti = None
    gas = None
    diesel = None

    spot_match = re.search(
        r"Wholesale Spot Petroleum Prices,\s*(\d{1,2}/\d{1,2}/\d{2})\s*Close",
        section,
    )
    if spot_match:
        spot_date = parse_mmddyy(spot_match.group(1))

    aaa_match = re.search(
        r"Retail Petroleum Prices\s*\(\s*AAA\s*\)\s*,\s*(\d{1,2}/\d{1,2}/\d{2})(?:\s+\(\$/gallon\))?",
        section,
    )
    if aaa_match:
        aaa_date = parse_mmddyy(aaa_match.group(1))

    wti_match = re.search(r"(?:\(\$/barrel\)\s+)?WTI\s+([0-9.]+)\s+([+\-]?[0-9.]+)", section)
    if wti_match:
        wti = {
            "value": float(wti_match.group(1)),
            "pct_change": float(wti_match.group(2)),
            "date": spot_date,
        }

    gas_match = re.search(
        r"Regular Gasoline U\.S\. Average\s+([0-9.]+)\s+([+\-]?[0-9.]+)",
        section,
    )
    if gas_match:
        gas = {
            "value": float(gas_match.group(1)),
            "pct_change": float(gas_match.group(2)),
            "date": aaa_date,
        }

    diesel_match = re.search(r"Diesel U\.S\. Average\s+([0-9.]+)\s+([+\-]?[0-9.]+)", section)
    if diesel_match:
        diesel = {
            "value": float(diesel_match.group(1)),
            "pct_change": float(diesel_match.group(2)),
            "date": aaa_date,
        }

    if not (current_date and spot_date and aaa_date and wti and gas):
        LOGGER.warning(
            "source_parse_failed source=current_prices page_date_found=%s spot_date_found=%s aaa_date_found=%s wti_found=%s gas_found=%s diesel_found=%s section_snippet=%s",
            bool(current_date),
            bool(spot_date),
            bool(aaa_date),
            bool(wti),
            bool(gas),
            bool(diesel),
            compact_debug_snippet(section),
        )
        raise DataUnavailableError(
            "Unable to parse the EIA daily prices page.",
            error_type="parse_error",
            metadata={
                "parser": "current_prices",
                "page_date_found": bool(current_date),
                "spot_date_found": bool(spot_date),
                "aaa_date_found": bool(aaa_date),
                "wti_found": bool(wti),
                "gas_found": bool(gas),
                "diesel_found": bool(diesel),
            },
        )

    LOGGER.info(
        "source_parse_success source=current_prices page_date=%s spot_close_date=%s aaa_date=%s",
        current_date,
        spot_date,
        aaa_date,
    )
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
    normalized = normalize_whitespace(text)
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
        row_pattern = re.compile(
            r"(\d{4})-([A-Za-z]{3})\s+(.+?)(?=(?:\d{4}-[A-Za-z]{3}\b)|$)"
        )
        for match in row_pattern.finditer(normalized):
            year = int(match.group(1))
            row_body = match.group(3)
            matches = re.findall(r"(\d{2}/\d{2})\s+([0-9.]+)", row_body)
            for mmdd, value in matches:
                series.append({"date": parse_mmdd_with_year(mmdd, year), "value": float(value)})

    if not series:
        LOGGER.warning(
            "source_parse_failed source=weekly_gas_history line_count=%s snippet=%s",
            len(text.splitlines()),
            compact_debug_snippet(normalized),
        )
        raise DataUnavailableError(
            "Unable to parse the weekly gasoline history page.",
            error_type="parse_error",
            metadata={"parser": "weekly_gas_history", "line_count": len(text.splitlines())},
        )

    series.sort(key=lambda item: item["date"])
    LOGGER.info(
        "source_parse_success source=weekly_gas_history observations=%s first_date=%s last_date=%s",
        len(series),
        series[0]["date"],
        series[-1]["date"],
    )
    return series


def parse_wti_history(raw_html: str) -> list[dict]:
    text = html_to_text(raw_html)
    normalized = normalize_whitespace(text)
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
        row_pattern = re.compile(
            r"(\d{4})\s+([A-Za-z]{3})-\s*(\d{1,2})\s+to\s+([A-Za-z]{3})-\s*(\d{1,2})\s+(.+?)(?=(?:\d{4}\s+[A-Za-z]{3}-\s*\d{1,2}\s+to\s+[A-Za-z]{3}-\s*\d{1,2})|$)"
        )
        for match in row_pattern.finditer(normalized):
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
        LOGGER.warning(
            "source_parse_failed source=wti_history line_count=%s snippet=%s",
            len(text.splitlines()),
            compact_debug_snippet(normalized),
        )
        raise DataUnavailableError(
            "Unable to parse the WTI history page.",
            error_type="parse_error",
            metadata={"parser": "wti_history", "line_count": len(text.splitlines())},
        )

    series.sort(key=lambda item: item["date"])
    LOGGER.info(
        "source_parse_success source=wti_history observations=%s first_date=%s last_date=%s",
        len(series),
        series[0]["date"],
        series[-1]["date"],
    )
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
    diagnostics: dict[str, dict] = {}
    live_current = None
    live_gas = None
    live_wti = None

    def capture_source(
        source_name: str,
        url: str,
        loader,
        summary_builder,
    ):
        fetched_at = dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")
        try:
            payload, fetch_meta = loader()
            diagnostic = {
                "name": source_name,
                "url": url,
                "ok": True,
                "used_fallback": False,
                "fetched_at": fetched_at,
                "error_type": None,
                "error": None,
                **fetch_meta,
                **summary_builder(payload),
            }
            diagnostics[source_name] = diagnostic
            return payload
        except DataUnavailableError as exc:
            diagnostic = {
                "name": source_name,
                "url": url,
                "ok": False,
                "used_fallback": True,
                "fetched_at": fetched_at,
                "error_type": exc.error_type,
                "error": str(exc),
                "elapsed_ms": exc.elapsed_ms,
                **exc.metadata,
            }
            diagnostics[source_name] = diagnostic
            errors.append(
                f"{source_name}: {diagnostic['error_type']} ({diagnostic.get('elapsed_ms')} ms) - {diagnostic['error']}"
            )
            LOGGER.warning(
                "source_fallback source=%s error_type=%s elapsed_ms=%s detail=%s",
                source_name,
                diagnostic["error_type"],
                diagnostic.get("elapsed_ms"),
                diagnostic["error"],
            )
            return None
        except Exception as exc:
            diagnostic = {
                "name": source_name,
                "url": url,
                "ok": False,
                "used_fallback": True,
                "fetched_at": fetched_at,
                "error_type": "unexpected_exception",
                "error": f"{type(exc).__name__}: {exc}",
            }
            diagnostics[source_name] = diagnostic
            errors.append(f"{source_name}: unexpected_exception - {diagnostic['error']}")
            LOGGER.exception("source_fallback_unexpected source=%s", source_name)
            return None

    def load_current_prices():
        raw_html, fetch_meta = fetch_url_payload(CURRENT_PRICES_URL)
        try:
            parsed = parse_current_prices(raw_html)
        except DataUnavailableError as exc:
            raise DataUnavailableError(
                str(exc),
                url=exc.url or CURRENT_PRICES_URL,
                error_type=exc.error_type,
                elapsed_ms=exc.elapsed_ms or fetch_meta.get("elapsed_ms"),
                metadata={**fetch_meta, **exc.metadata},
            ) from exc
        return parsed, fetch_meta

    def load_weekly_gas():
        raw_html, fetch_meta = fetch_url_payload(WEEKLY_GAS_HISTORY_URL)
        try:
            parsed = parse_weekly_gas_history(raw_html)
        except DataUnavailableError as exc:
            raise DataUnavailableError(
                str(exc),
                url=exc.url or WEEKLY_GAS_HISTORY_URL,
                error_type=exc.error_type,
                elapsed_ms=exc.elapsed_ms or fetch_meta.get("elapsed_ms"),
                metadata={**fetch_meta, **exc.metadata},
            ) from exc
        return parsed, fetch_meta

    def load_wti_history():
        raw_html, fetch_meta = fetch_url_payload(WTI_HISTORY_URL)
        try:
            parsed = parse_wti_history(raw_html)
        except DataUnavailableError as exc:
            raise DataUnavailableError(
                str(exc),
                url=exc.url or WTI_HISTORY_URL,
                error_type=exc.error_type,
                elapsed_ms=exc.elapsed_ms or fetch_meta.get("elapsed_ms"),
                metadata={**fetch_meta, **exc.metadata},
            ) from exc
        return parsed, fetch_meta

    live_current = capture_source(
        "current_prices",
        CURRENT_PRICES_URL,
        load_current_prices,
        lambda payload: {
            "page_date": payload["page_date"],
            "spot_close_date": payload["spot_close_date"],
            "aaa_date": payload["aaa_date"],
        },
    )
    live_gas = capture_source(
        "weekly_gas_history",
        WEEKLY_GAS_HISTORY_URL,
        load_weekly_gas,
        lambda payload: {
            "observations": len(payload),
            "first_date": payload[0]["date"],
            "last_date": payload[-1]["date"],
        },
    )
    live_wti = capture_source(
        "wti_history",
        WTI_HISTORY_URL,
        load_wti_history,
        lambda payload: {
            "observations": len(payload),
            "first_date": payload[0]["date"],
            "last_date": payload[-1]["date"],
        },
    )

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
            "diagnostics": diagnostics,
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

    fallback["diagnostics"] = diagnostics
    fallback["errors"] = errors or fallback["errors"]

    if live_current or live_gas or live_wti:
        fallback["mode"] = "hybrid"
    LOGGER.warning(
        "market_dataset_fallback mode=%s diagnostics=%s",
        fallback["mode"],
        {name: details["ok"] for name, details in diagnostics.items()},
    )
    return fallback
