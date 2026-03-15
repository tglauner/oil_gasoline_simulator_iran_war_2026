from app.services.market_data import generate_fallback_history
from app.services.simulation import align_weekly_series, fit_pass_through_model, run_simulation


def test_fit_pass_through_model():
    dataset = generate_fallback_history()
    observations = align_weekly_series(dataset["gasoline"], dataset["wti_weekly"])
    model = fit_pass_through_model(observations)

    assert model["long_run"]["r_squared"] > 0.6
    assert model["short_run"]["r_squared"] > 0.1
    assert model["training_start"] == "2018-05-14"


def test_run_simulation():
    dataset = generate_fallback_history()
    observations = align_weekly_series(dataset["gasoline"], dataset["wti_weekly"])
    latest_crude = observations[-1]["crude"]
    simulation = run_simulation(observations, latest_crude + 10.0, 8, 2)

    assert len(simulation["comparison"]) == 8
    assert simulation["summary"]["final_delta_cents"] > 0.0
    assert simulation["current_basis"]["date"] == observations[-1]["date"]
