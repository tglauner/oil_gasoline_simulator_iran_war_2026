from app.services import market_data
from app.services.market_data import generate_fallback_history, parse_current_prices, parse_weekly_gas_history, parse_wti_history


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

CURRENT_PRICES_LIVE_LAYOUT_HTML = """
<html>
  <body>
    <p>March 13, 2026</p>
    <h1>Daily Prices</h1>
    <p>
      Daily wholesale and retail prices for various energy products are shown below,
      including spot prices and select futures prices at national or regional levels.
    </p>
    <h2>Daily Prices</h2>
    <p>Wholesale Spot Petroleum Prices, 3/12/26 Close</p>
    <p>Product Area Price Percent Change*</p>
    <p>Crude Oil</p>
    <p>($/barrel) WTI 95.61 +10.1</p>
    <p>Retail Petroleum Prices (AAA), 3/12/26 ($/gallon)</p>
    <p>Regular Gasoline U.S. Average 3.63 +0.9</p>
    <p>Diesel U.S. Average 4.89 +0.7</p>
    <p>Financial Indicators, 3/12/26 Close</p>
  </body>
</html>
"""

CURRENT_PRICES_TABLE_HTML = """
<html>
  <body>
    <p>March 13, 2026</p>
    <h2>Daily Prices</h2>
    <table>
      <tr><td>Wholesale Spot Petroleum Prices, 3/12/26 Close</td></tr>
      <tr><td>Crude Oil</td></tr>
      <tr><td>($/barrel)</td><td>WTI</td><td>95.61</td><td>+10.1</td></tr>
      <tr><td>Retail Petroleum Prices (AAA), 3/12/26</td><td>($/gallon)</td></tr>
      <tr><td>Regular Gasoline</td><td>U.S. Average</td><td>3.63</td><td>+0.9</td></tr>
      <tr><td>Diesel</td><td>U.S. Average</td><td>4.89</td><td>+0.7</td></tr>
    </table>
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

WEEKLY_GAS_HISTORY_TABLE_HTML = """
<html>
  <body>
    <table>
      <tr><td>2025-Dec</td><td>12/15</td><td>3.011</td><td>12/22</td><td>3.002</td><td>12/29</td><td>3.004</td></tr>
      <tr><td>2026-Jan</td><td>01/05</td><td>3.008</td><td>01/12</td><td>3.014</td><td>01/19</td><td>3.022</td><td>01/26</td><td>3.046</td></tr>
      <tr><td>2026-Feb</td><td>02/02</td><td>3.061</td><td>02/09</td><td>3.087</td><td>02/16</td><td>3.121</td><td>02/23</td><td>3.265</td></tr>
      <tr><td>2026-Mar</td><td>03/02</td><td>3.415</td><td>03/09</td><td>3.502</td></tr>
    </table>
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

WTI_HISTORY_TABLE_HTML = """
<html>
  <body>
    <table>
      <tr><td>2026</td><td>Feb-16 to Feb-20</td><td>82.80</td><td>83.05</td><td>82.94</td><td>83.11</td></tr>
      <tr><td>2026</td><td>Feb-23 to Feb-27</td><td>83.74</td><td>83.61</td><td>83.19</td><td>82.96</td><td>83.07</td></tr>
      <tr><td>2026</td><td>Mar- 2 to Mar- 6</td><td>85.82</td><td>87.08</td><td>88.26</td><td>87.16</td><td>88.38</td></tr>
    </table>
  </body>
</html>
"""

WEEKLY_GAS_HISTORY_FLAT_HTML = """
<html>
  <body>
    <p>
      Weekly U.S. Regular All Formulations Retail Gasoline Prices (Dollars per Gallon)
      1990-Aug 08/20 1.191 08/27 1.245
      1990-Sep 09/03 1.242 09/10 1.252 09/17 1.266 09/24 1.272
      2026-Mar 03/02 3.415 03/09 3.502
    </p>
  </body>
</html>
"""

WTI_HISTORY_FLAT_HTML = """
<html>
  <body>
    <p>
      Cushing, OK WTI Spot Price FOB (Dollars per Barrel)
      2026 Feb-16 to Feb-20 82.80 83.05 82.94 83.11
      2026 Feb-23 to Feb-27 83.74 83.61 83.19 82.96 83.07
      2026 Mar- 2 to Mar- 6 85.82 87.08 88.26 87.16 88.38
    </p>
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


def test_parse_current_prices_handles_live_2026_layout():
    parsed = parse_current_prices(CURRENT_PRICES_LIVE_LAYOUT_HTML)
    assert parsed["page_date"] == "2026-03-13"
    assert parsed["spot_close_date"] == "2026-03-12"
    assert parsed["aaa_date"] == "2026-03-12"
    assert parsed["wti_daily"]["pct_change"] == 10.1
    assert parsed["aaa_regular_gasoline"]["pct_change"] == 0.9


def test_parse_current_prices_handles_table_cells():
    parsed = parse_current_prices(CURRENT_PRICES_TABLE_HTML)
    assert parsed["page_date"] == "2026-03-13"
    assert parsed["aaa_regular_gasoline"]["value"] == 3.63
    assert parsed["aaa_diesel"]["value"] == 4.89


def test_parse_weekly_gas_history():
    parsed = parse_weekly_gas_history(WEEKLY_GAS_HISTORY_HTML)
    assert parsed[0]["date"] == "2025-12-15"
    assert parsed[-1]["date"] == "2026-03-09"
    assert parsed[-1]["value"] == 3.502


def test_parse_weekly_gas_history_handles_table_cells():
    parsed = parse_weekly_gas_history(WEEKLY_GAS_HISTORY_TABLE_HTML)
    assert parsed[0]["date"] == "2025-12-15"
    assert parsed[-1]["date"] == "2026-03-09"
    assert parsed[-1]["value"] == 3.502


def test_parse_weekly_gas_history_handles_flattened_rows():
    parsed = parse_weekly_gas_history(WEEKLY_GAS_HISTORY_FLAT_HTML)
    assert parsed[0]["date"] == "1990-08-20"
    assert parsed[-1]["date"] == "2026-03-09"
    assert parsed[-1]["value"] == 3.502


def test_parse_wti_history():
    parsed = parse_wti_history(WTI_HISTORY_HTML)
    assert parsed[0]["date"] == "2026-02-23"
    assert parsed[-1]["date"] == "2026-03-09"
    assert round(parsed[-1]["value"], 2) == 87.34


def test_parse_wti_history_handles_table_cells():
    parsed = parse_wti_history(WTI_HISTORY_TABLE_HTML)
    assert parsed[0]["date"] == "2026-02-23"
    assert parsed[-1]["date"] == "2026-03-09"
    assert round(parsed[-1]["value"], 2) == 87.34


def test_parse_wti_history_handles_flattened_rows():
    parsed = parse_wti_history(WTI_HISTORY_FLAT_HTML)
    assert parsed[0]["date"] == "2026-02-23"
    assert parsed[-1]["date"] == "2026-03-09"
    assert round(parsed[-1]["value"], 2) == 87.34


def test_generate_fallback_history():
    dataset = generate_fallback_history()
    assert len(dataset["gasoline"]) > 300
    assert dataset["current"]["page_date"] == "2026-03-13"


def test_build_market_dataset_collects_diagnostics_on_fetch_failure(monkeypatch):
    def fail_fetch(url, timeout=None):
        raise market_data.DataUnavailableError(
            f"Unable to fetch {url}: DNS failed",
            url=url,
            error_type="dns_resolution_error",
            elapsed_ms=12.5,
        )

    monkeypatch.setattr(market_data, "fetch_url_payload", fail_fetch)
    dataset = market_data.build_market_dataset()

    assert dataset["mode"] == "fallback"
    assert len(dataset["diagnostics"]) == 3
    assert all(not item["ok"] for item in dataset["diagnostics"].values())
    assert any("dns_resolution_error" in message for message in dataset["errors"])
