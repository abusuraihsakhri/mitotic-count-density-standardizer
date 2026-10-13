import csv
import pytest
from mitotic_density import calculate_metrics, process_batch


def test_single_mitotic_density():
    result = calculate_metrics(mitotic_count=12, field_diameter_mm=0.5)
    assert result["mitoses_per_mm2"] == pytest.approx(12 / (10 * 3.141592653589793 * .25**2))
    assert result["classification"].startswith("Not assigned")


def test_batch_mitotic_density(tmp_path):
    source = tmp_path / "input.csv"
    target = tmp_path / "output.csv"
    source.write_text("specimen_id,mitotic_count,field_diameter_mm,fields_counted\nA,15,0.5,10\nB,5,0.5,10\n")
    assert process_batch(str(source), str(target)) == 2
    with target.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert float(rows[0]["mitoses_per_mm2"]) == pytest.approx(float(rows[1]["mitoses_per_mm2"]) * 3)
