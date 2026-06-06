"""
Tests for the CLI module.

Tests the imperative shell: argument parsing, JSON output, and summary output.
"""

import json
import sys

import pytest

from portfolio_risk.cli import build_parser, main


class TestBuildParser:

    def test_no_args_prints_error(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["portfolio_risk"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "error"
        assert "--config" in output["message"]

    def test_parses_basic_args(self):
        parser = build_parser()
        args = parser.parse_args(["--csv", "test.csv", "--weights", "0.6", "0.4", "--risk-free-rate", "0.02"])
        assert args.csv == "test.csv"
        assert args.weights == [0.6, 0.4]
        assert args.risk_free_rate == 0.02

    def test_default_risk_free_rate(self):
        parser = build_parser()
        args = parser.parse_args(["--csv", "test.csv", "--weights", "1.0"])
        assert args.risk_free_rate == 0.0


class TestMain:

    def _make_csv(self, tmp_path):
        """Helper: create a simple 2-asset CSV and return its path."""
        import polars as pl
        csv_path = tmp_path / "test.csv"
        pl.DataFrame({
            "date": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"],
            "ASSET_01": [0.01, 0.03, -0.01, 0.02],
            "ASSET_02": [0.02, 0.04, 0.01, -0.01],
        }).write_csv(str(csv_path))
        return csv_path

    def test_bad_file_prints_error(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", [
            "portfolio_risk", "--csv", "/nonexistent.csv", "--weights", "0.5", "0.5",
        ])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        assert json.loads(capsys.readouterr().out)["status"] == "error"

    def test_success_output_is_valid_json(self, capsys, monkeypatch, tmp_path):
        csv_path = self._make_csv(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "portfolio_risk", "--csv", str(csv_path), "--weights", "0.6", "0.4", "--json",
        ])
        main()
        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert "metrics" in output

    def test_wrong_weight_count_prints_friendly_error(self, capsys, monkeypatch, tmp_path):
        import polars as pl
        csv_path = tmp_path / "test.csv"
        pl.DataFrame({
            "date": ["2023-01-01", "2023-01-02"],
            "ASSET_01": [0.01, 0.02], "ASSET_02": [0.03, 0.04], "ASSET_03": [0.05, 0.06],
        }).write_csv(str(csv_path))

        monkeypatch.setattr(sys, "argv", [
            "portfolio_risk", "--csv", str(csv_path), "--weights", "0.5", "0.5",
        ])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        output = json.loads(capsys.readouterr().out)
        assert "3" in output["message"] and "2" in output["message"]

    def test_config_file_mode(self, capsys, monkeypatch, tmp_path):
        csv_path = self._make_csv(tmp_path)
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "csv": str(csv_path), "weights": [0.6, 0.4], "risk_free_rate": 0.02,
        }))

        monkeypatch.setattr(sys, "argv", [
            "portfolio_risk", "--config", str(config_path), "--json",
        ])
        main()
        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "success"
        assert output["config"]["risk_free_rate"] == 0.02

    def test_default_output_is_summary(self, capsys, monkeypatch, tmp_path):
        csv_path = self._make_csv(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "portfolio_risk", "--csv", str(csv_path), "--weights", "0.6", "0.4",
        ])
        main()
        output = capsys.readouterr().out
        assert "Portfolio Risk Analysis" in output
        assert "Sharpe Ratio" in output
        assert "Asset Volatilities" in output
