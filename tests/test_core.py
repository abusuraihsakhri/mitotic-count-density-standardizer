"""Regression tests for geometric mitotic density normalization."""
import csv
import math
import pytest

from mitotic_density import calculate_metrics, process_batch, main


class TestDensity:
    def test_calibrated_ten_fields(self):
        result = calculate_metrics(mitotic_count=12, field_diameter_mm=0.55, fields_counted=10)
        field_area = math.pi * (0.55 / 2) ** 2
        assert result["field_area_mm2"] == pytest.approx(field_area)
        assert result["total_area_mm2"] == pytest.approx(field_area * 10)
        assert result["mitoses_per_mm2"] == pytest.approx(12 / (field_area * 10))
        assert result["score"] == result["mitoses_per_mm2"]

    def test_measured_area_digital_pathology(self):
        result = calculate_metrics(mitotic_count=6, measured_area_mm2=2)
        assert result["mitoses_per_mm2"] == 3
        assert result["field_area_mm2"] is None

    def test_zero_mitoses(self):
        assert calculate_metrics(0, field_diameter_mm=0.5)["mitoses_per_mm2"] == 0

    def test_field_count_changes_examined_area(self):
        ten = calculate_metrics(10, field_diameter_mm=0.5, fields_counted=10)
        five = calculate_metrics(10, field_diameter_mm=0.5, fields_counted=5)
        assert five["mitoses_per_mm2"] == pytest.approx(ten["mitoses_per_mm2"] * 2)

    @pytest.mark.parametrize("count", [-1, 1.5, "wrong", float("nan"), True])
    def test_invalid_counts(self, count):
        with pytest.raises(ValueError, match="mitotic_count"):
            calculate_metrics(count, field_diameter_mm=0.5)

    @pytest.mark.parametrize("value", [0, -0.5, float("nan"), float("inf"), "abc", True])
    def test_invalid_calibrations(self, value):
        with pytest.raises(ValueError, match="field_diameter_mm"):
            calculate_metrics(10, field_diameter_mm=value)

    @pytest.mark.parametrize("value", [0, -1, 1.5, float("inf"), True])
    def test_invalid_field_counts(self, value):
        with pytest.raises(ValueError, match="fields_counted"):
            calculate_metrics(10, field_diameter_mm=0.5, fields_counted=value)

    def test_exactly_one_area_source(self):
        with pytest.raises(ValueError, match="exactly one"):
            calculate_metrics(5)
        with pytest.raises(ValueError, match="exactly one"):
            calculate_metrics(5, field_diameter_mm=0.5, measured_area_mm2=1)

    def test_area_must_be_positive_finite(self):
        with pytest.raises(ValueError, match="measured_area_mm2"):
            calculate_metrics(5, measured_area_mm2=0)
        with pytest.raises(ValueError, match="measured_area_mm2"):
            calculate_metrics(5, measured_area_mm2=float("inf"))

    def test_no_clinical_triage_from_density(self):
        result = calculate_metrics(500, field_diameter_mm=0.5)
        assert "Not assigned" in result["classification"]
        assert "None;" in result["clinical_recommendation"]

    def test_cli_single(self, capsys):
        assert main(["single", "--mitotic-count", "10", "--measured-area-mm2", "2"]) == 0
        assert '"mitoses_per_mm2": 5.0' in capsys.readouterr().out


class TestCSV:
    def test_batch_preserves_identifiers(self, tmp_path):
        infile = tmp_path / "observations.csv"
        outfile = tmp_path / "result.csv"
        infile.write_text("specimen_id,mitotic_count,field_diameter_mm,fields_counted\n"
                          "S1,10,0.5,10\nS2,0,0.55,5\n", encoding="utf-8")
        assert process_batch(str(infile), str(outfile)) == 2
        with outfile.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert [r["specimen_id"] for r in rows] == ["S1", "S2"]
        assert float(rows[0]["mitoses_per_mm2"]) == pytest.approx(10 / (10 * math.pi * .25 ** 2))
        assert float(rows[1]["mitoses_per_mm2"]) == 0

    def test_csv_direct_area(self, tmp_path):
        src = tmp_path / "src.csv"
        dst = tmp_path / "dst.csv"
        src.write_text("mitotic_count,measured_area_mm2\n4,2\n")
        process_batch(str(src), str(dst))
        assert "2.0" in dst.read_text()

    def test_empty_with_header(self, tmp_path):
        src = tmp_path / "src.csv"
        dst = tmp_path / "dst.csv"
        src.write_text("mitotic_count,field_diameter_mm\n")
        assert process_batch(str(src), str(dst)) == 0
        assert "mitoses_per_mm2" in dst.read_text()

    def test_invalid_row_leaves_no_partial_output(self, tmp_path):
        src = tmp_path / "src.csv"
        dst = tmp_path / "dst.csv"
        src.write_text("mitotic_count,field_diameter_mm\n10,0.5\nabc,0.5\n")
        with pytest.raises(ValueError, match="Row 3"):
            process_batch(str(src), str(dst))
        assert not dst.exists()

    def test_reject_inplace_write(self, tmp_path):
        src = tmp_path / "src.csv"
        src.write_text("mitotic_count,field_diameter_mm\n4,0.5\n")
        with pytest.raises(ValueError, match="must differ"):
            process_batch(str(src), str(src))

    def test_reject_missing_required_headers(self, tmp_path):
        src = tmp_path / "src.csv"
        with pytest.raises(ValueError, match="mitotic_count"):
            src.write_text("name,field_diameter_mm\nS1,0.5\n")
            process_batch(str(src), str(tmp_path / "out.csv"))

    def test_csv_formula_injection_escaped(self, tmp_path):
        src = tmp_path / "src.csv"
        dst = tmp_path / "dst.csv"
        src.write_text("specimen_id,mitotic_count,measured_area_mm2\n=HYPERLINK(1),5,2\n")
        process_batch(str(src), str(dst))
        assert "'=HYPERLINK(1)" in dst.read_text()

    def test_reject_extra_cells(self, tmp_path):
        src = tmp_path / "src.csv"
        src.write_text("mitotic_count,measured_area_mm2\n5,2,extra\n")
        with pytest.raises(ValueError, match="more fields"):
            process_batch(str(src), str(tmp_path / "out.csv"))
