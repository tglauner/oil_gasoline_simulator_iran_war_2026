from __future__ import annotations

import datetime as dt
import math


DEFAULT_LAGS = 8
DEFAULT_TRAINING_START = dt.date(2018, 5, 14)


def align_weekly_series(gasoline: list[dict], wti_weekly: list[dict]) -> list[dict]:
    gas_map = {item["date"]: item["value"] for item in gasoline}
    wti_map = {item["date"]: item["value"] for item in wti_weekly}
    common_dates = sorted(set(gas_map) & set(wti_map))
    return [{"date": date_value, "gas": gas_map[date_value], "crude": wti_map[date_value]} for date_value in common_dates]


def solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]

    for col in range(size):
        pivot = max(range(col, size), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) < 1e-12:
            raise ValueError("Singular matrix in regression solve.")
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]

        pivot_value = augmented[col][col]
        for j in range(col, size + 1):
            augmented[col][j] /= pivot_value

        for row in range(size):
            if row == col:
                continue
            factor = augmented[row][col]
            if factor == 0:
                continue
            for j in range(col, size + 1):
                augmented[row][j] -= factor * augmented[col][j]

    return [augmented[row][size] for row in range(size)]


def fit_ols(rows: list[list[float]], target: list[float], ridge: float = 1e-8) -> dict:
    if not rows or not target:
        raise ValueError("Regression requires at least one observation.")

    column_count = len(rows[0])
    xtx = [[0.0 for _ in range(column_count)] for _ in range(column_count)]
    xty = [0.0 for _ in range(column_count)]

    for row, y_value in zip(rows, target):
        for i in range(column_count):
            xty[i] += row[i] * y_value
            for j in range(column_count):
                xtx[i][j] += row[i] * row[j]

    for index in range(column_count):
        xtx[index][index] += ridge

    coefficients = solve_linear_system(xtx, xty)
    fitted = [sum(coef * value for coef, value in zip(coefficients, row)) for row in rows]
    residuals = [actual - predicted for actual, predicted in zip(target, fitted)]
    mean_target = sum(target) / len(target)
    ss_res = sum(residual * residual for residual in residuals)
    ss_tot = sum((value - mean_target) ** 2 for value in target)
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {
        "coefficients": coefficients,
        "fitted": fitted,
        "residuals": residuals,
        "r_squared": r_squared,
    }


def _seasonal_terms(index: int) -> list[float]:
    angle = 2.0 * math.pi * index / 52.0
    return [math.sin(angle), math.cos(angle), math.sin(2.0 * angle), math.cos(2.0 * angle)]


def _effective_training_slice(observations: list[dict], requested_start: dt.date) -> list[dict]:
    filtered = [item for item in observations if dt.date.fromisoformat(item["date"]) >= requested_start]
    if len(filtered) >= 120:
        return filtered
    if len(observations) >= 120:
        return observations[-min(len(observations), 260):]
    return observations[:]


def fit_pass_through_model(
    observations: list[dict],
    training_start: dt.date = DEFAULT_TRAINING_START,
    lags: int = DEFAULT_LAGS,
) -> dict:
    training = _effective_training_slice(observations, training_start)
    if len(training) <= lags + 4:
        raise ValueError("Not enough observations to fit the model.")

    long_rows = [[1.0, item["crude"]] for item in training]
    long_target = [item["gas"] for item in training]
    long_run = fit_ols(long_rows, long_target)
    long_alpha, long_beta = long_run["coefficients"]
    equilibrium_error = [
        item["gas"] - (long_alpha + long_beta * item["crude"]) for item in training
    ]

    crude_delta = [0.0]
    gas_delta = [0.0]
    for index in range(1, len(training)):
        crude_delta.append(training[index]["crude"] - training[index - 1]["crude"])
        gas_delta.append(training[index]["gas"] - training[index - 1]["gas"])

    short_rows = []
    short_target = []
    short_dates = []
    for index in range(lags, len(training)):
        row = [1.0, equilibrium_error[index - 1], gas_delta[index - 1], *_seasonal_terms(index)]
        for lag in range(lags):
            delta = crude_delta[index - lag]
            row.append(max(delta, 0.0))
            row.append(max(-delta, 0.0))
        short_rows.append(row)
        short_target.append(gas_delta[index])
        short_dates.append(training[index]["date"])

    short_run = fit_ols(short_rows, short_target)
    coefficient_offset = 7
    positive_coefficients = short_run["coefficients"][coefficient_offset::2]
    negative_coefficients = short_run["coefficients"][coefficient_offset + 1 :: 2]
    residual_std = math.sqrt(
        sum(value * value for value in short_run["residuals"]) / max(1, len(short_run["residuals"]) - len(short_run["coefficients"]))
    )

    return {
        "training_start": training[0]["date"],
        "training_end": training[-1]["date"],
        "observations": training,
        "lags": lags,
        "long_run": {
            "alpha": long_alpha,
            "beta": long_beta,
            "r_squared": long_run["r_squared"],
        },
        "short_run": {
            "coefficients": short_run["coefficients"],
            "r_squared": short_run["r_squared"],
            "residual_std": residual_std,
            "positive_coefficients": positive_coefficients,
            "negative_coefficients": negative_coefficients,
            "feature_dates": short_dates,
        },
    }


def build_crude_path(start: float, target: float, horizon_weeks: int, transition_weeks: int) -> list[float]:
    horizon_weeks = max(1, horizon_weeks)
    transition_weeks = max(1, min(transition_weeks, horizon_weeks))
    values = []
    for week in range(1, horizon_weeks + 1):
        if week <= transition_weeks:
            fraction = week / float(transition_weeks)
            value = start + (target - start) * fraction
        else:
            value = target
        values.append(value)
    return values


def project_gas_path(model: dict, history: list[dict], crude_path: list[float]) -> list[dict]:
    lags = model["lags"]
    long_alpha = model["long_run"]["alpha"]
    long_beta = model["long_run"]["beta"]
    coefficients = model["short_run"]["coefficients"]

    gas_history = [item["gas"] for item in history]
    crude_history = [item["crude"] for item in history]
    date_history = [dt.date.fromisoformat(item["date"]) for item in history]

    projections = []
    for step, projected_crude in enumerate(crude_path, start=1):
        index = len(gas_history)
        equilibrium_error = gas_history[-1] - (long_alpha + long_beta * crude_history[-1])
        gas_delta_prev = gas_history[-1] - gas_history[-2] if len(gas_history) >= 2 else 0.0
        row = [1.0, equilibrium_error, gas_delta_prev, *_seasonal_terms(index)]

        crude_delta_series = [0.0]
        for inner_index in range(1, len(crude_history)):
            crude_delta_series.append(crude_history[inner_index] - crude_history[inner_index - 1])
        crude_delta_series.append(projected_crude - crude_history[-1])

        for lag in range(lags):
            delta = crude_delta_series[-1 - lag]
            row.append(max(delta, 0.0))
            row.append(max(-delta, 0.0))

        gas_delta = sum(coef * value for coef, value in zip(coefficients, row))
        next_gas = max(0.5, gas_history[-1] + gas_delta)
        next_date = date_history[-1] + dt.timedelta(days=7)

        crude_history.append(projected_crude)
        gas_history.append(next_gas)
        date_history.append(next_date)
        projections.append(
            {
                "date": next_date.isoformat(),
                "crude": round(projected_crude, 4),
                "gas": round(next_gas, 4),
            }
        )

    return projections


def backtest_model(observations: list[dict], holdout_weeks: int = 52) -> dict:
    if len(observations) < 180:
        holdout_weeks = 26
    if len(observations) < 100:
        return {"weeks": 0, "mae": None, "rmse": None}

    holdout_weeks = min(holdout_weeks, max(12, len(observations) // 5))
    training = observations[:-holdout_weeks]
    testing = observations[-holdout_weeks:]

    model = fit_pass_through_model(training)
    projected = project_gas_path(model, training, [item["crude"] for item in testing])
    actual = [item["gas"] for item in testing]
    predicted = [item["gas"] for item in projected]
    errors = [pred - obs for pred, obs in zip(predicted, actual)]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors))
    return {"weeks": holdout_weeks, "mae": mae, "rmse": rmse}


def run_simulation(
    observations: list[dict],
    target_wti: float,
    horizon_weeks: int,
    transition_weeks: int,
) -> dict:
    model = fit_pass_through_model(observations)
    latest_crude = observations[-1]["crude"]
    latest_gas = observations[-1]["gas"]
    baseline_path = build_crude_path(latest_crude, latest_crude, horizon_weeks, 1)
    scenario_path = build_crude_path(latest_crude, target_wti, horizon_weeks, transition_weeks)

    baseline = project_gas_path(model, observations, baseline_path)
    scenario = project_gas_path(model, observations, scenario_path)

    comparison = []
    peak_delta = None
    peak_week = None
    for week_index, (base, alt) in enumerate(zip(baseline, scenario), start=1):
        delta = alt["gas"] - base["gas"]
        change_from_current = alt["gas"] - latest_gas
        comparison.append(
            {
                "week": week_index,
                "date": alt["date"],
                "baseline_wti": base["crude"],
                "scenario_wti": alt["crude"],
                "baseline_gas": base["gas"],
                "scenario_gas": alt["gas"],
                "delta_vs_baseline": round(delta, 4),
                "delta_vs_current": round(change_from_current, 4),
            }
        )
        if peak_delta is None or abs(delta) > abs(peak_delta):
            peak_delta = delta
            peak_week = week_index

    validation = backtest_model(observations)
    positive_pass = sum(model["short_run"]["positive_coefficients"][:4]) * 10.0 * 100.0
    negative_pass = -sum(model["short_run"]["negative_coefficients"][:8]) * 10.0 * 100.0

    return {
        "model": {
            "training_start": model["training_start"],
            "training_end": model["training_end"],
            "lag_weeks": model["lags"],
            "observations": len(model["observations"]),
            "long_run_beta": round(model["long_run"]["beta"], 4),
            "long_run_r_squared": round(model["long_run"]["r_squared"], 4),
            "short_run_r_squared": round(model["short_run"]["r_squared"], 4),
            "residual_std": round(model["short_run"]["residual_std"], 4),
            "validation_weeks": validation["weeks"],
            "validation_mae_cents": None if validation["mae"] is None else round(validation["mae"] * 100.0, 2),
            "validation_rmse_cents": None if validation["rmse"] is None else round(validation["rmse"] * 100.0, 2),
            "upside_pass_through_4w_cents_per_10_dollars": round(positive_pass, 2),
            "downside_pass_through_8w_cents_per_10_dollars": round(negative_pass, 2),
        },
        "current_basis": {
            "date": observations[-1]["date"],
            "weekly_wti": round(latest_crude, 4),
            "weekly_gas": round(latest_gas, 4),
        },
        "inputs": {
            "target_wti": round(target_wti, 4),
            "horizon_weeks": horizon_weeks,
            "transition_weeks": transition_weeks,
        },
        "baseline": baseline,
        "scenario": scenario,
        "comparison": comparison,
        "summary": {
            "peak_delta_cents": round((peak_delta or 0.0) * 100.0, 2),
            "peak_week": peak_week,
            "final_delta_cents": round(comparison[-1]["delta_vs_baseline"] * 100.0, 2),
            "final_price": round(comparison[-1]["scenario_gas"], 4),
        },
    }
