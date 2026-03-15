from app.services.market_data import (
    generate_fallback_history,
    parse_current_prices,
    parse_weekly_gas_history,
    parse_wti_history,
)


CURRENT_PRICES_HTML = """
<html>
  <body>
    <p>March 13, 2026</p>
    <h2>Daily Prices</h2>
    <p>Wholesale Spot Petroleum Prices, 3/12/26 Close</p>
    <p>Crude Oil</p>
    <p>($/barrel) WTI 95.61 10.1</p>
    <p>Retail Petroleum Prices (AAA), 3/12/26</p>
    <p>($/gallon)</p>
    <p>Regular Gasoline U.S. Average 3.63 0.9</p>
    <p>Diesel U.S. Average 4.89 0.7</p>
  </body>
</html>
"""

CURRENT_PRICES_WITH_EXTRA_DATES_HTML = """
<html>
  <body>
    <p>Mar 12, 2026</p>
    <p>Some unrelated updated note</p>
    <p>March 13, 2026</p>
    <h2>Daily Prices</h2>
    <p>Wholesale Spot Petroleum Prices, 3/12/26 Close</p>
    <p>Crude Oil</p>
    <p>($/barrel) WTI 95.61 10.1</p>
    <p>Retail Petroleum Prices (AAA), 3/12/26</p>
    <p>($/gallon)</p>
    <p>Regular Gasoline U.S. Average 3.63 0.9</p>
    <p>Diesel U.S. Average 4.89 0.7</p>
    <p>Feb 4, 2013</p>
  </body>
</html>
"""

WEEKLY_GAS_HISTORY_HTML = """
<html>
  <body>
    <pre>
2025-Dec 12/15 3.011 12/22 3.002 12/29 3.004
2026-Jan 01/05 3.008 01/12 3.014 01/19 3.022 01/26 3.046
2026-Feb 02/02 3.061 02/09 3.087 02/16 3.121 02/23 3.265
2026-Mar 03/02 3.415 03/09 3.502
    </pre>
  </body>
</html>
"""

WTI_HISTORY_HTML = """
<html>
  <body>
    <pre>
2026 Feb-16 to Feb-20 82.80 83.05 82.94 83.11
2026 Feb-23 to Feb-27 83.74 83.61 83.19 82.96 83.07
2026 Mar- 2 to Mar- 6 85.82 87.08 88.26 87.16 88.38
    </pre>
  </body>
</html>
"""


def test_parse_current_prices():
    parsed = parse_current_prices(CURRENT_PRICES_HTML)
    assert parsed["page_date"] == "2026-03-13"
    assert parsed["spot_close_date"] == "2026-03-12"
    assert parsed["wti_daily"]["value"] == 95.61
    assert parsed["aaa_regular_gasoline"]["value"] == 3.63


def test_parse_current_prices_uses_daily_prices_heading_date():
    parsed = parse_current_prices(CURRENT_PRICES_WITH_EXTRA_DATES_HTML)
    assert parsed["page_date"] == "2026-03-13"
    assert parsed["spot_close_date"] == "2026-03-12"


def test_parse_weekly_gas_history():
    parsed = parse_weekly_gas_history(WEEKLY_GAS_HISTORY_HTML)
    assert parsed[0]["date"] == "2025-12-15"
    assert parsed[-1]["date"] == "2026-03-09"
    assert parsed[-1]["value"] == 3.502


def test_parse_wti_history():
    parsed = parse_wti_history(WTI_HISTORY_HTML)
    assert parsed[0]["date"] == "2026-02-23"
    assert parsed[-1]["date"] == "2026-03-09"
    assert round(parsed[-1]["value"], 2) == 87.34


def test_generate_fallback_history():
    dataset = generate_fallback_history()
    assert len(dataset["gasoline"]) > 300
    assert dataset["current"]["page_date"] == "2026-03-13"
