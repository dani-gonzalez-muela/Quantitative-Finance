"""
Integration tests for the full pipeline.

Tests the complete flow: CSV → validate → compute → output.
Verifies that all pieces compose correctly together.
"""

import pytest
import polars as pl

from portfolio_risk.pipeline import run_pipeline, load_csv, detect_assets


# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def simple_csv(tmp_path) -> str:
    csv_path = tmp_path / "simple.csv"
    pl.DataFrame({
        "date": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"],
        "ASSET_01": [0.01, 0.03, -0.01, 0.02],
        "ASSET_02": [0.02, 0.04, 0.01, -0.01],
    }).write_csv(str(csv_path))
    return str(csv_path)


@pytest.fixture
def csv_with_nans(tmp_path) -> str:
    csv_path = tmp_path / "with_nans.csv"
    pl.DataFrame({
        "date": [f"2023-01-{i:02d}" for i in range(1, 31)],
        "ASSET_01": [0.01 if i != 5 else None for i in range(30)],
        "ASSET_02": [0.02 if i != 10 else None for i in range(30)],
    }).write_csv(str(csv_path))
    return str(csv_path)



# -- Detect Assets --

class TestDetectAssets:

    def test_basic_detection(self):
        df = pl.DataFrame({
            "date": ["2023-01-01", "2023-01-02"],
            "ASSET_01": [0.01, 0.02],
            "ASSET_02": [0.03, 0.04],
        })
        assert detect_assets(df) == ("ASSET_01", "ASSET_02")

    def test_excludes_date_column(self):
        df = pl.DataFrame({
            "date": ["2023-01-01", "2023-01-02"],
            "ASSET_01": [0.01, 0.02],
        })
        assert "date" not in detect_assets(df)

    def test_excludes_non_numeric_columns(self):
        df = pl.DataFrame({
            "date": ["2023-01-01", "2023-01-02"],
            "ASSET_01": [0.01, 0.02],
            "notes": ["good", "bad"],
        })
        result = detect_assets(df)
        assert "notes" not in result
        assert "ASSET_01" in result

    def test_no_numeric_columns(self):
        df = pl.DataFrame({"date": ["2023-01-01"], "notes": ["ok"]})
        assert detect_assets(df) == ()

    def test_preserves_column_order(self):
        df = pl.DataFrame({
            "date": ["2023-01-01"],
            "BETA": [0.01],
            "ALPHA": [0.02],
        })
        assert detect_assets(df) == ("BETA", "ALPHA")


# ── Pipeline Tests ───────────────────────────────────────────

class TestRunPipeline:

    def test_success_simple(self, simple_csv):
        result = run_pipeline(file_path=simple_csv, weights=(0.6, 0.4), asset_names=("ASSET_01", "ASSET_02"))
        assert result.status == "success"
        assert result.metrics is not None
        result_dict = result.to_dict()
        for key in ("portfolio_variance", "annualized_return", "sharpe_ratio",
                     "max_drawdown", "asset_volatilities", "correlation_matrix"):
            assert key in result_dict["metrics"]

    def test_success_with_nans(self, csv_with_nans):
        result = run_pipeline(file_path=csv_with_nans, weights=(0.5, 0.5), asset_names=("ASSET_01", "ASSET_02"))
        assert result.status == "success"
        assert len(result.warnings) > 0
        assert any("filled" in w.lower() or "nan" in w.lower() for w in result.warnings)

    def test_config_in_output(self, simple_csv):
        result = run_pipeline(
            file_path=simple_csv, weights=(0.6, 0.4),
            asset_names=("ASSET_01", "ASSET_02"), risk_free_rate=0.02,
        )
        assert result.config.asset_names == ("ASSET_01", "ASSET_02")
        assert result.config.weights == (0.6, 0.4)
        assert result.config.risk_free_rate == 0.02

    def test_error_bad_file(self):
        result = run_pipeline(file_path="/nonexistent.csv", weights=(0.5, 0.5), asset_names=("A", "B"))
        assert result.status == "error"
        assert "could not read" in result.message.lower()

    def test_error_bad_weights(self, simple_csv):
        result = run_pipeline(file_path=simple_csv, weights=(0.6, 0.6), asset_names=("ASSET_01", "ASSET_02"))
        assert result.status == "error"
        assert "weight" in result.message.lower()

    def test_error_wrong_weight_count(self, simple_csv):
        result = run_pipeline(
            file_path=simple_csv, weights=(0.5, 0.3, 0.2),
            asset_names=("ASSET_01", "ASSET_02", "ASSET_03"),
        )
        assert result.status == "error"
        assert "ASSET_03" in result.message


class TestLoadCsv:

    def test_valid_file(self, simple_csv):
        df = load_csv(simple_csv)
        assert df is not None
        assert df.height == 4
        assert df.width == 3

    def test_nonexistent_file(self):
        assert load_csv("/nonexistent/file.csv") is None
