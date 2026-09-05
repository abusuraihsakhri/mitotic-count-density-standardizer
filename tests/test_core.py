"""
Core functionality tests for Mitotic Count Density Standardizer.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mitotic_density import calculate_metrics, process_batch


class TestCalculateMetrics:
    """Tests for the core calculate_metrics function."""

    def test_basic_calculation(self):
        res = calculate_metrics(v1=10.0, v2=5.0, v3=2.0)
        assert res["tool"] == "mitotic-count-density-standardizer"
        assert res["score"] > 0
        assert "classification" in res
        assert "clinical_recommendation" in res

    def test_single_value(self):
        res = calculate_metrics(v1=15.0)
        assert res["score"] == 15.0
        assert res["inputs_evaluated"] == 1

    def test_low_score_classification(self):
        res = calculate_metrics(v1=5.0)
        assert res["score"] < 10.0
        assert "Low" in res["classification"]
        assert "Standard monitoring" in res["clinical_recommendation"]

    def test_moderate_score_classification(self):
        res = calculate_metrics(v1=15.0)
        assert 10.0 <= res["score"] < 25.0
        assert "Moderate" in res["classification"]
        assert "Close observation" in res["clinical_recommendation"]

    def test_high_score_classification(self):
        res = calculate_metrics(v1=30.0)
        assert res["score"] >= 25.0
        assert "High" in res["classification"]
        assert "Urgent clinical intervention" in res["clinical_recommendation"]

    def test_string_values_filtered(self):
        res = calculate_metrics(v1=10.0, name="test")
        # String values should not affect numeric calculation
        assert res["score"] == 10.0

    def test_none_values_ignored(self):
        res = calculate_metrics(v1=10.0, v2=None, v3=None)
        assert res["score"] == 10.0
        assert res["inputs_evaluated"] == 1

    def test_no_numeric_defaults_to_one(self):
        res = calculate_metrics(name="test", label="abc")
        assert res["score"] == 1.0

    def test_weighted_calculation(self):
        # v1 is primary, v2 gets weight 1/2, v3 gets weight 1/3
        res = calculate_metrics(v1=10.0, v2=4.0, v3=3.0)
        # expected: 10.0 + 4.0*(1/2) + 3.0*(1/3) = 10 + 2 + 1 = 13.0
        assert res["score"] == 13.0

    def test_rounding(self):
        res = calculate_metrics(v1=10.0, v2=3.333)
        # score = 10.0 + 3.333*0.5 = 11.6665 -> rounds to 11.67
        assert res["score"] == 11.67


class TestProcessBatch:
    """Tests for batch CSV processing."""

    def test_batch_creates_output(self, tmp_path):
        csv_in = tmp_path / "input.csv"
        csv_out = tmp_path / "output.csv"
        csv_in.write_text("Patient_ID,v1,v2,v3\nPT-001,14.5,4.2,1.8\n", encoding="utf-8")

        process_batch(str(csv_in), str(csv_out))
        assert csv_out.exists()

    def test_batch_output_has_score_columns(self, tmp_path):
        csv_in = tmp_path / "input.csv"
        csv_out = tmp_path / "output.csv"
        csv_in.write_text("v1,v2\n10.0,5.0\n", encoding="utf-8")

        process_batch(str(csv_in), str(csv_out))
        content = csv_out.read_text(encoding="utf-8")
        assert "score" in content
        assert "classification" in content
        assert "clinical_recommendation" in content

    def test_batch_empty_csv(self, tmp_path):
        csv_in = tmp_path / "input.csv"
        csv_out = tmp_path / "output.csv"
        csv_in.write_text("v1,v2\n", encoding="utf-8")

        process_batch(str(csv_in), str(csv_out))
        assert csv_out.exists()
        content = csv_out.read_text(encoding="utf-8")
        assert "score" in content  # header should exist
