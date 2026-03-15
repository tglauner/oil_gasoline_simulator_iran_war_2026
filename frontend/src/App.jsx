import { startTransition, useEffect, useRef, useState } from "react";


const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";


function formatMoney(value, decimals = 2) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}


function formatPercent(value, decimals = 1) {
  return `${(value * 100).toFixed(decimals)}%`;
}


function formatSignedPercent(value, decimals = 1) {
  const sign = value >= 0 ? "+" : "-";
  return `${sign}${Math.abs(value * 100).toFixed(decimals)}%`;
}


function signedCents(value) {
  const sign = value >= 0 ? "+" : "-";
  return `${sign}${Math.abs(value).toFixed(1)}c`;
}


function formatDate(value) {
  const date = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}


function formatTimestamp(value) {
  const date = new Date(value);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}


async function fetchJson(path, options) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }

  if (!response.ok) {
    throw new Error(payload.detail || payload.error || `Request failed with ${response.status}`);
  }
  return payload;
}


function LineChart({ series, height = 250, marker = null }) {
  if (!series.length || !series[0].points.length) {
    return <div className="chart-empty">No chart data available.</div>;
  }

  const width = 760;
  const padding = { top: 18, right: 20, bottom: 26, left: 18 };
  const allValues = series.flatMap((item) => item.points.map((point) => point.y));
  const minValue = Math.min(...allValues);
  const maxValue = Math.max(...allValues);
  const span = maxValue - minValue || 1;
  const paddedMin = minValue - span * 0.12;
  const paddedMax = maxValue + span * 0.12;
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const count = Math.max(...series.map((item) => item.points.length));
  const firstDate = series[0].points[0].x;
  const lastDate = series[0].points[series[0].points.length - 1].x;
  const firstDateMs = new Date(`${firstDate}T00:00:00Z`).getTime();
  const lastDateMs = new Date(`${lastDate}T00:00:00Z`).getTime();
  const markerDateMs = marker ? new Date(`${marker.date}T00:00:00Z`).getTime() : null;
  const markerInRange = markerDateMs != null && markerDateMs >= firstDateMs && markerDateMs <= lastDateMs;
  const markerRatio = markerInRange && lastDateMs > firstDateMs ? (markerDateMs - firstDateMs) / (lastDateMs - firstDateMs) : null;
  const markerX = markerRatio != null ? padding.left + innerWidth * markerRatio : null;
  const markerTextAnchor = markerRatio != null && markerRatio > 0.76 ? "end" : "start";
  const markerLabelX = markerX == null ? null : markerTextAnchor === "start" ? markerX + 6 : markerX - 6;

  const grid = Array.from({ length: 5 }, (_, index) => {
    const y = padding.top + (innerHeight / 4) * index;
    return (
      <line
        key={`grid-${y}`}
        x1={padding.left}
        y1={y}
        x2={width - padding.right}
        y2={y}
        stroke="rgba(31,26,22,0.08)"
        strokeWidth="1"
      />
    );
  });

  return (
    <>
      <div className="chart-labels">
        <div className="legend">
          {series.map((item) => (
            <span className="legend-item" key={item.label}>
              <span className="legend-swatch" style={{ background: item.color }} />
              {item.label}
            </span>
          ))}
          {markerInRange ? (
            <span className="legend-item">
              <span className="legend-swatch marker-swatch" />
              {marker.label}
            </span>
          ) : null}
        </div>
        <div>
          {formatDate(firstDate)} to {formatDate(lastDate)}
        </div>
      </div>
      <div className="chart-labels">
        <div>Low {formatMoney(paddedMin, paddedMax < 10 ? 3 : 2)}</div>
        <div>High {formatMoney(paddedMax, paddedMax < 10 ? 3 : 2)}</div>
      </div>
      <svg className="chart-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Line chart">
        {grid}
        {markerInRange ? (
          <g>
            <line
              x1={markerX}
              y1={padding.top}
              x2={markerX}
              y2={height - padding.bottom}
              stroke="rgba(157, 77, 47, 0.9)"
              strokeWidth="2"
              strokeDasharray="6 6"
            />
            <text
              x={markerLabelX}
              y={padding.top + 12}
              textAnchor={markerTextAnchor}
              fill="#9d4d2f"
              fontSize="11"
              fontWeight="700"
            >
              {marker.label}
            </text>
          </g>
        ) : null}
        {series.map((line) => {
          const points = line.points
            .map((point, index) => {
              const x = padding.left + (count === 1 ? innerWidth / 2 : (innerWidth * index) / (count - 1));
              const y = padding.top + innerHeight - ((point.y - paddedMin) / (paddedMax - paddedMin)) * innerHeight;
              return `${x.toFixed(2)},${y.toFixed(2)}`;
            })
            .join(" ");

          return (
            <g key={line.label}>
              {line.fill ? (
                <polygon
                  points={`${padding.left},${height - padding.bottom} ${points} ${width - padding.right},${height - padding.bottom}`}
                  fill={line.fill}
                />
              ) : null}
              <polyline
                points={points}
                fill="none"
                stroke={line.color}
                strokeWidth="4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </g>
          );
        })}
      </svg>
    </>
  );
}


function MetricCard({ label, value, note }) {
  return (
    <article className="metric-card">
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
      <p className="metric-note">{note}</p>
    </article>
  );
}


function ResultCard({ label, value }) {
  return (
    <article className="result-card">
      <p className="result-label">{label}</p>
      <p className="result-value">{value}</p>
    </article>
  );
}


export default function App() {
  const [dashboard, setDashboard] = useState(null);
  const [simulation, setSimulation] = useState(null);
  const [status, setStatus] = useState("Loading market data and model diagnostics.");
  const initialLoadStarted = useRef(false);
  const [calculatorInputs, setCalculatorInputs] = useState({
    miles: "300",
    mpg: "26",
    tankGallons: "15",
  });
  const [scenarioInputs, setScenarioInputs] = useState({
    targetWti: "",
    horizonWeeks: "8",
    transitionWeeks: "2",
  });

  useEffect(() => {
    if (initialLoadStarted.current) {
      return;
    }
    initialLoadStarted.current = true;
    void loadDashboard(false);
  }, []);

  async function loadDashboard(forceRefresh) {
    setStatus("Loading market data and model diagnostics.");
    try {
      const payload = await fetchJson(forceRefresh ? "/api/refresh" : "/api/dashboard");
      const defaultTargetWti = payload.current.daily_wti.value * 1.25;
      const nextScenario = {
        targetWti: defaultTargetWti.toFixed(1),
        horizonWeeks: "8",
        transitionWeeks: "2",
      };

      startTransition(() => {
        setDashboard(payload);
        setCalculatorInputs({
          miles: String(payload.calculator.defaults.miles),
          mpg: String(payload.calculator.defaults.mpg),
          tankGallons: String(payload.calculator.defaults.tank_gallons),
        });
        setScenarioInputs(nextScenario);
      });

      await loadSimulation(nextScenario);
      setStatus(payload.mode === "live" ? "Live EIA data loaded successfully." : "Running with live fallback or mixed data.");
    } catch (error) {
      setStatus(`Unable to load dashboard data: ${error.message}`);
    }
  }

  async function loadSimulation(inputs) {
    try {
      const payload = await fetchJson("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_wti: Number(inputs.targetWti),
          horizon_weeks: Number(inputs.horizonWeeks),
          transition_weeks: Number(inputs.transitionWeeks),
        }),
      });
      startTransition(() => {
        setSimulation(payload);
      });
    } catch (error) {
      setStatus(`Simulation error: ${error.message}`);
    }
  }

  function handleCalculatorChange(event) {
    const { name, value } = event.target;
    setCalculatorInputs((current) => ({ ...current, [name]: value }));
  }

  function handleScenarioChange(event) {
    const { name, value } = event.target;
    setScenarioInputs((current) => ({ ...current, [name]: value }));
  }

  async function handleSimulationSubmit(event) {
    event.preventDefault();
    setStatus("Running crude-price scenario.");
    await loadSimulation(scenarioInputs);
    setStatus("Simulation updated.");
  }

  const gasPrice = dashboard?.current.aaa_regular_gasoline.value || 0;
  const wtiPrice = dashboard?.current.daily_wti.value || 0;
  const miles = Number(calculatorInputs.miles || 0);
  const mpg = Number(calculatorInputs.mpg || 0);
  const tankGallons = Number(calculatorInputs.tankGallons || 0);
  const gallonsForTrip = mpg > 0 ? miles / mpg : 0;
  const tripCost = gallonsForTrip * gasPrice;
  const fillUpCost = tankGallons * gasPrice;
  const crudeCostPerGallon = wtiPrice / 42.0;
  const crudeShare = gasPrice > 0 ? crudeCostPerGallon / gasPrice : 0;
  const targetWtiValue = Number(scenarioInputs.targetWti || 0);
  const oilTargetDelta = wtiPrice > 0 ? targetWtiValue / wtiPrice - 1 : 0;
  const modeledGasDelta = simulation?.current_basis?.weekly_gas
    ? simulation.summary.final_price / simulation.current_basis.weekly_gas - 1
    : 0;
  const eventMarker = dashboard?.historical_event
    ? {
        date: dashboard.historical_event.date,
        label: `${dashboard.historical_event.label} ${formatDate(dashboard.historical_event.date)}`,
      }
    : null;

  return (
    <div className="page-shell">
      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Crude To Pump Lab</p>
          <h1>Track live oil and gasoline prices, then stress-test the pass-through.</h1>
          <p className="hero-text">
            This React frontend pairs with a FastAPI backend and models how a crude-price shock can reach the U.S.
            gasoline market over the following weeks.
          </p>
        </div>
        <div className="hero-panel">
          <div className="status-row">
            <span className="badge">{dashboard ? dashboard.mode.toUpperCase() : "LOADING"}</span>
            <button className="ghost-button" type="button" onClick={() => void loadDashboard(true)}>
              Refresh data
            </button>
          </div>
          <p className="status-text">{status}</p>
          {dashboard?.errors?.length ? (
            <div className="warning-box">
              <p className="warning-title">Live source diagnostics</p>
              <ul className="warning-list">
                {dashboard.errors.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              {dashboard.diagnostics?.sources?.length ? (
                <details className="debug-details">
                  <summary>Open source diagnostics</summary>
                  <ul className="debug-list">
                    {dashboard.diagnostics.sources.map((item) => (
                      <li key={item.name}>
                        <strong>{item.name}</strong>
                        <span>{item.ok ? "live" : "fallback"}</span>
                        <span>{item.error_type || "ok"}</span>
                        <span>{item.elapsed_ms != null ? `${item.elapsed_ms} ms` : "n/a"}</span>
                        <span>{item.error || item.url}</span>
                      </li>
                    ))}
                  </ul>
                  {dashboard.diagnostics.log_file ? (
                    <p className="debug-note">Backend log file: {dashboard.diagnostics.log_file}</p>
                  ) : null}
                </details>
              ) : null}
            </div>
          ) : null}
        </div>
      </header>

      <main>
	        <section className="panel">
          <div className="section-head">
            <div>
              <p className="eyebrow">Current Snapshot</p>
              <h2>Market dashboard</h2>
            </div>
            <p className="stamp">{dashboard ? `Generated ${formatTimestamp(dashboard.generated_at)}` : ""}</p>
          </div>

          <div className="metric-grid">
            <MetricCard
              label="WTI crude"
              value={dashboard ? formatMoney(dashboard.current.daily_wti.value, 2) : "--"}
              note={dashboard ? `WTI close on ${formatDate(dashboard.current.daily_wti.date)}` : ""}
            />
            <MetricCard
              label="AAA U.S. regular"
              value={dashboard ? formatMoney(dashboard.current.aaa_regular_gasoline.value, 3) : "--"}
              note={dashboard ? `AAA U.S. average on ${formatDate(dashboard.current.aaa_regular_gasoline.date)}` : ""}
            />
            <MetricCard
              label="EIA weekly regular"
              value={dashboard ? formatMoney(dashboard.current.weekly_regular_gasoline.value, 3) : "--"}
              note={dashboard ? `EIA release for ${formatDate(dashboard.current.weekly_regular_gasoline.date)}` : ""}
            />
            <MetricCard
              label="Model weekly WTI basis"
              value={dashboard ? formatMoney(dashboard.current.weekly_wti_for_model.value, 2) : "--"}
              note={dashboard ? `Basis week ending ${formatDate(dashboard.current.weekly_wti_for_model.date)}` : ""}
            />
          </div>

          <div className="chart-grid">
            <article className="chart-card">
              <div className="card-head">
                <h3>WTI, last 104 weeks</h3>
                <p>Weekly average aligned to Monday gas release</p>
              </div>
	              <div className="chart-frame">
	                {dashboard ? (
	                  <LineChart
	                    marker={eventMarker}
	                    series={[
	                      {
	                        label: "WTI weekly",
                        color: "#9d4d2f",
                        fill: "rgba(157, 77, 47, 0.10)",
                        points: dashboard.history.weekly_pairs.map((item) => ({ x: item.date, y: item.crude })),
                      },
                    ]}
                  />
                ) : null}
              </div>
            </article>
            <article className="chart-card">
              <div className="card-head">
                <h3>U.S. gasoline, last 104 weeks</h3>
                <p>EIA regular all-formulations retail price</p>
              </div>
	              <div className="chart-frame">
	                {dashboard ? (
	                  <LineChart
	                    marker={eventMarker}
	                    series={[
	                      {
	                        label: "Gasoline weekly",
                        color: "#1d6f72",
                        fill: "rgba(29, 111, 114, 0.12)",
                        points: dashboard.history.weekly_pairs.map((item) => ({ x: item.date, y: item.gas })),
                      },
                    ]}
                  />
                ) : null}
              </div>
            </article>
          </div>
        </section>

	        <section className="panel">
	          <div className="section-head">
	            <div>
              <p className="eyebrow">Simulation</p>
              <h2>Run a crude-price scenario</h2>
            </div>
            <p className="stamp">Scenario output is weekly.</p>
          </div>

          <div className="simulation-grid">
	            <form className="simulation-form" onSubmit={handleSimulationSubmit}>
	              <label>
	                Target WTI ($/barrel)
                <input name="targetWti" type="number" min="1" step="0.1" value={scenarioInputs.targetWti} onChange={handleScenarioChange} />
              </label>
              <label>
                Horizon (weeks)
                <input name="horizonWeeks" type="number" min="1" max="26" step="1" value={scenarioInputs.horizonWeeks} onChange={handleScenarioChange} />
              </label>
              <label>
                Transition window (weeks)
                <input
                  name="transitionWeeks"
                  type="number"
                  min="1"
                  max="26"
                  step="1"
                  value={scenarioInputs.transitionWeeks}
                  onChange={handleScenarioChange}
                />
              </label>
              <button className="action-button" type="submit">
                Run simulation
              </button>
            </form>

	            <div className="simulation-summary">
	              <div className="summary-grid">
	                <ResultCard
	                  label="Spot oil"
	                  value={dashboard ? formatMoney(dashboard.current.daily_wti.value, 2) : "--"}
	                />
	                <ResultCard
	                  label="Target oil"
	                  value={
	                    dashboard
	                      ? `${formatMoney(targetWtiValue, 2)} ${formatSignedPercent(oilTargetDelta, 1)}`
	                      : "--"
	                  }
	                />
	                <ResultCard
	                  label="Current gas"
	                  value={
	                    simulation
	                      ? formatMoney(simulation.current_basis.weekly_gas, 3)
	                      : "--"
	                  }
	                />
	                <ResultCard
	                  label="Scenario gas"
	                  value={
	                    simulation
	                      ? `${formatMoney(simulation.summary.final_price, 3)} ${formatSignedPercent(modeledGasDelta, 1)}`
	                      : "--"
	                  }
	                />
	                <ResultCard
	                  label="Peak gasoline move"
	                  value={simulation ? `${signedCents(simulation.summary.peak_delta_cents)} in week ${simulation.summary.peak_week}` : "--"}
	                />
	                <ResultCard
	                  label="Validation MAE"
	                  value={
	                    simulation?.model.validation_mae_cents != null
                      ? `${simulation.model.validation_mae_cents.toFixed(1)}c`
                      : dashboard?.model.validation_mae_cents != null
                        ? `${dashboard.model.validation_mae_cents.toFixed(1)}c`
                        : "--"
                  }
                />
              </div>

              <div className="chart-frame tall">
                {simulation ? (
                  <LineChart
                    height={320}
                    series={[
                      {
                        label: "Baseline gasoline",
                        color: "#1d6f72",
                        points: simulation.baseline.map((item) => ({ x: item.date, y: item.gas })),
                      },
                      {
                        label: "Scenario gasoline",
                        color: "#9d4d2f",
                        points: simulation.scenario.map((item) => ({ x: item.date, y: item.gas })),
                      },
                    ]}
                  />
                ) : null}
              </div>
            </div>
          </div>

          <div className="table-shell">
            <table>
              <thead>
                <tr>
                  <th>Week</th>
                  <th>Date</th>
                  <th>WTI scenario</th>
                  <th>Gas baseline</th>
                  <th>Gas scenario</th>
                  <th>Delta</th>
                </tr>
              </thead>
              <tbody>
                {simulation?.comparison?.map((item) => (
                  <tr key={item.week}>
                    <td>{item.week}</td>
                    <td>{formatDate(item.date)}</td>
                    <td>{formatMoney(item.scenario_wti, 2)}</td>
                    <td>{formatMoney(item.baseline_gas, 3)}</td>
                    <td>{formatMoney(item.scenario_gas, 3)}</td>
                    <td>{signedCents(item.delta_vs_baseline * 100)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
	          </div>
	        </section>

	        <section className="panel split-panel">
	          <article className="calculator-card">
	            <div className="section-head compact">
	              <div>
	                <p className="eyebrow">Calculator</p>
	                <h2>Trip and fill-up cost</h2>
	              </div>
	            </div>
	            <p className="panel-text">
	              Uses the current AAA U.S. regular gasoline price for the pump estimate and the current WTI close for the
	              crude-only input cost.
	            </p>
	            <form className="form-grid">
	              <label>
	                Miles to drive
	                <input name="miles" type="number" min="1" step="1" value={calculatorInputs.miles} onChange={handleCalculatorChange} />
	              </label>
	              <label>
	                Vehicle mpg
	                <input name="mpg" type="number" min="1" step="0.1" value={calculatorInputs.mpg} onChange={handleCalculatorChange} />
	              </label>
	              <label>
	                Tank size (gallons)
	                <input
	                  name="tankGallons"
	                  type="number"
	                  min="1"
	                  step="0.1"
	                  value={calculatorInputs.tankGallons}
	                  onChange={handleCalculatorChange}
	                />
	              </label>
	            </form>
	            <div className="result-grid">
	              <ResultCard label="Gallons for trip" value={gallonsForTrip ? gallonsForTrip.toFixed(2) : "--"} />
	              <ResultCard label="Trip pump cost" value={tripCost ? formatMoney(tripCost, 2) : "--"} />
	              <ResultCard label="Full tank cost" value={fillUpCost ? formatMoney(fillUpCost, 2) : "--"} />
	              <ResultCard label="Crude share per gallon" value={dashboard ? formatPercent(crudeShare, 1) : "--"} />
	            </div>
	          </article>

	          <article className="calculator-card emphasis-card">
	            <div className="section-head compact">
	              <div>
	                <p className="eyebrow">Reference Mix</p>
	                <h2>Pump-price anatomy</h2>
	              </div>
	            </div>
	            <p className="panel-text">
	              EIA's current weekly page reports that January 2026 gasoline prices were split roughly into crude oil,
	              refining, distribution and marketing, and taxes.
	            </p>
	            <div className="stack-list">
	              <div className="stack-item">
	                <span>Crude oil</span>
	                <strong>{dashboard ? formatPercent(dashboard.calculator.eia_reference_crude_share, 1) : "--"}</strong>
	              </div>
	              <div className="stack-item">
	                <span>Refining</span>
	                <strong>17.5%</strong>
	              </div>
	              <div className="stack-item">
	                <span>Distribution + marketing</span>
	                <strong>16.6%</strong>
	              </div>
	              <div className="stack-item">
	                <span>Taxes</span>
	                <strong>16.4%</strong>
	              </div>
	            </div>
	            <p className="metric-note">
	              {dashboard ? `Current WTI implies ${formatMoney(dashboard.calculator.daily_wti_per_gallon, 3)} per gallon of crude input before refining, distribution, and taxes.` : ""}
	            </p>
	          </article>
	        </section>

        <section className="panel methodology-panel">
          <div className="section-head">
            <div>
              <p className="eyebrow">Methodology</p>
              <h2>Model and source notes</h2>
            </div>
          </div>

          <div className="method-grid">
            <article className="method-card">
              <h3>Why this model</h3>
              <p className="panel-text">{dashboard?.methodology.summary}</p>
              <ul className="plain-list">
                {dashboard?.methodology.assumptions.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </article>
            <article className="method-card">
              <h3>Model diagnostics</h3>
              <div className="stack-list compact-stack">
                <div className="stack-item">
                  <span>Training window</span>
                  <strong>
                    {dashboard ? `${formatDate(dashboard.model.training_start)} to ${formatDate(dashboard.model.training_end)}` : "--"}
                  </strong>
                </div>
                <div className="stack-item">
                  <span>Observations</span>
                  <strong>{dashboard ? `${dashboard.model.observations} weekly points` : "--"}</strong>
                </div>
                <div className="stack-item">
                  <span>Upside pass-through</span>
                  <strong>{dashboard ? `${signedCents(dashboard.model.upside_pass_through_4w_cents_per_10_dollars)} after +$10 WTI` : "--"}</strong>
                </div>
                <div className="stack-item">
                  <span>Downside pass-through</span>
                  <strong>{dashboard ? `${signedCents(-dashboard.model.downside_pass_through_8w_cents_per_10_dollars)} after -$10 WTI` : "--"}</strong>
                </div>
              </div>
            </article>
            <article className="method-card">
              <h3>Sources</h3>
              <ul className="link-list">
                {dashboard?.methodology.sources.map((item) => (
                  <li key={item.url}>
                    <a href={item.url} target="_blank" rel="noreferrer">
                      {item.name}
                    </a>
                    <br />
                    <span>{item.description}</span>
                  </li>
                ))}
              </ul>
            </article>
          </div>
        </section>
      </main>
    </div>
  );
}
