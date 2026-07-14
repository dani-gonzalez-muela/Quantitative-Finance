"""
Tests for data and weight validators.

Validators return result objects instead of raising exceptions (FP error handling).
"""

import pytest
import polars as pl

from portfolio_risk.validators import validate_data, validate_weights


# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def clean_data() -> pl.DataFrame:
    return pl.DataFrame({
        "date": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"],
        "ASSET_01": [0.01, 0.03, -0.01, 0.02],
        "ASSET_02": [0.02, 0.04, 0.01, -0.01],
    })


@pytest.fixture
def data_with_few_nans() -> pl.DataFrame:
    """1 NaN out of 30 rows = 3.3% — below the 5% threshold."""
    return pl.DataFrame({
        "date": [f"2023-01-{i:02d}" for i in range(1, 31)],
        "ASSET_01": [0.01, 0.03, -0.01, 0.02, 0.01, -0.02, 0.03, 0.01,
                     None, 0.02, 0.01, -0.01, 0.02, 0.03, -0.01, 0.01,
                     0.02, -0.01, 0.03, 0.01, 0.02, -0.01, 0.01, 0.03,
                     -0.02, 0.01, 0.02, -0.01, 0.03, 0.01],
        "ASSET_02": [0.02, 0.04, 0.01, -0.01, 0.02, 0.01, -0.03, 0.02,
                     0.01, -0.01, 0.02, 0.03, -0.01, 0.01, 0.02, -0.02,
                     0.01, 0.03, -0.01, 0.02, 0.01, -0.01, 0.02, 0.01,
                     0.03, -0.01, 0.02, 0.01, -0.02, 0.03],
    })


@pytest.fixture
def data_with_bad_asset() -> pl.DataFrame:
    """ASSET_02 has 2/20 = 10% NaN — above the 5% threshold, should be dropped."""
    return pl.DataFrame({
        "date": [f"2023-01-{i:02d}" for i in range(1, 21)],
        "ASSET_01": [0.01, 0.03, -0.01, 0.02, 0.01, -0.02, 0.03, 0.01,
                     0.02, -0.01, 0.01, 0.03, -0.01, 0.02, 0.01, -0.02,
                     0.03, 0.01, 0.02, -0.01],
        "ASSET_02": [0.02, None, 0.01, -0.01, 0.02, None, -0.03, 0.02,
                     0.01, -0.01, 0.02, 0.03, -0.01, 0.01, 0.02, -0.02,
                     0.01, 0.03, -0.01, 0.02],
        "ASSET_03": [0.01, 0.02, -0.02, 0.01, 0.03, -0.01, 0.02, 0.01,
                     -0.01, 0.02, 0.01, -0.02, 0.03, 0.01, 0.02, -0.01,
                     0.01, 0.02, -0.01, 0.03],
    })


# ── Data Validation ──────────────────────────────────────────

class TestValidateData:

    def test_clean_data_passes(self, clean_data):
        result = validate_data(clean_data)
        assert result.is_valid is True
        assert result.data is not None
        assert "date" not in result.data.asset_names

    def test_empty_dataframe_fails(self):
        result = validate_data(pl.DataFrame())
        assert result.is_valid is False

    def test_no_rows_fails(self):
        no_rows = pl.DataFrame({"ASSET_01": [], "ASSET_02": []}).cast(pl.Float64)
        result = validate_data(no_rows)
        assert result.is_valid is False

    def test_single_row_rejected(self):
        """std(ddof=1) is undefined for n=1."""
        result = validate_data(pl.DataFrame({"ASSET_01": [0.01], "ASSET_02": [0.02]}))
        assert result.is_valid is False

    def test_non_numeric_column_excluded(self):
        df = pl.DataFrame({
            "date": ["2023-01-01", "2023-01-02", "2023-01-03"],
            "ASSET_01": [0.01, 0.02, 0.03],
            "notes": ["good", "bad", "ok"],
        })
        result = validate_data(df)
        assert result.is_valid is True
        assert "notes" not in result.data.asset_names
        assert "ASSET_01" in result.data.asset_names

    def test_only_date_column_fails(self):
        result = validate_data(pl.DataFrame({"date": ["2023-01-01", "2023-01-02"]}))
        assert result.is_valid is False

    def test_few_nans_filled_with_zero(self, data_with_few_nans):
        result = validate_data(data_with_few_nans)
        assert result.is_valid is True
        assert result.data.data.null_count().sum_horizontal().item() == 0
        assert "filled" in result.message.lower() or "nan" in result.message.lower()

    def test_bad_asset_dropped(self, data_with_bad_asset):
        result = validate_data(data_with_bad_asset)
        assert result.is_valid is True
        assert "ASSET_02" not in result.data.asset_names
        assert "ASSET_01" in result.data.asset_names
        assert "ASSET_03" in result.data.asset_names
        assert "ASSET_02" in result.message

    def test_all_nan_column_dropped(self):
        df = pl.DataFrame({
            "date": [f"2023-01-{i:02d}" for i in range(1, 21)],
            "ASSET_01": [0.01] * 20,
            "ASSET_02": [None] * 20,
        })
        result = validate_data(df)
        assert result.is_valid is True
        assert "ASSET_02" not in result.data.asset_names
        assert "ASSET_02" in result.message

    def test_all_assets_dropped_fails(self):
        """If ALL assets exceed the NaN threshold, validation fails."""
        bad_data = pl.DataFrame({
            "date": [f"2023-01-{i:02d}" for i in range(1, 21)],
            "ASSET_01": [None, None, None, None] + [0.01] * 16,
            "ASSET_02": [None, None, None, None] + [0.02] * 16,
        })
        result = validate_data(bad_data)
        assert result.is_valid is False

    def test_returns_correct_metadata(self, clean_data):
        result = validate_data(clean_data)
        assert result.data.n_days == 4
        assert result.data.n_assets == 2
        assert result.data.asset_names == ("ASSET_01", "ASSET_02")


# ── Weight Validation ────────────────────────────────────────

class TestValidateWeights:

    def test_valid_weights(self):
        result = validate_weights((0.6, 0.4), ("ASSET_01", "ASSET_02"), ("ASSET_01", "ASSET_02"))
        assert result.is_valid is True
        assert result.config.weights == (0.6, 0.4)

    def test_weights_sum_greater_than_one(self):
        result = validate_weights((0.6, 0.6), ("ASSET_01", "ASSET_02"), ("ASSET_01", "ASSET_02"))
        assert result.is_valid is False

    def test_weights_sum_less_than_one(self):
        result = validate_weights((0.3, 0.2), ("ASSET_01", "ASSET_02"), ("ASSET_01", "ASSET_02"))
        assert result.is_valid is False

    def test_wrong_number_of_weights(self):
        result = validate_weights((0.5, 0.5), ("A", "B", "C"), ("A", "B", "C"))
        assert result.is_valid is False

    def test_renormalize_after_asset_drop(self):
        """ASSET_02 dropped → weights 0.4, 0.4 renormalized to 0.5, 0.5."""
        result = validate_weights(
            (0.4, 0.2, 0.4),
            ("ASSET_01", "ASSET_02", "ASSET_03"),
            ("ASSET_01", "ASSET_03"),
        )
        assert result.is_valid is True
        assert result.config.weights[0] == pytest.approx(0.5)
        assert result.config.weights[1] == pytest.approx(0.5)
        assert result.config.asset_names == ("ASSET_01", "ASSET_03")
        assert "renormalize" in result.message.lower() or "adjusted" in result.message.lower()

    def test_renormalize_unequal_weights(self):
        """Renormalization should preserve relative proportions."""
        result = validate_weights(
            (0.5, 0.3, 0.2),
            ("ASSET_01", "ASSET_02", "ASSET_03"),
            ("ASSET_01", "ASSET_03"),  # ASSET_02 dropped
        )
        assert result.is_valid is True
        # Surviving: 0.5, 0.2 → sum=0.7 → 0.5/0.7, 0.2/0.7
        assert result.config.weights[0] == pytest.approx(0.5 / 0.7, rel=1e-4)
        assert result.config.weights[1] == pytest.approx(0.2 / 0.7, rel=1e-4)
        assert sum(result.config.weights) == pytest.approx(1.0)

    def test_floating_point_tolerance(self):
        """1/3 + 1/3 + 1/3 = 0.9999999999999999 should still pass."""
        result = validate_weights(
            (1/3, 1/3, 1/3),
            ("ASSET_01", "ASSET_02", "ASSET_03"),
            ("ASSET_01", "ASSET_02", "ASSET_03"),
        )
        assert result.is_valid is True
