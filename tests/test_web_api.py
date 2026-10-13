"""Smoke tests for the standalone browser and REST density endpoint."""
import math
from pathlib import Path
import re
import shutil
import subprocess

import pytest
from fastapi import HTTPException

from agents.api import DensityRequest, api_density, health, index


def test_api_density_conversion():
    response = api_density(DensityRequest(mitotic_count=10, field_diameter_mm=0.5))
    assert response["mitoses_per_mm2"] == pytest.approx(10 / (10 * math.pi * (0.25 ** 2)))


def test_api_density_requires_single_area_source():
    with pytest.raises(HTTPException) as err:
        api_density(DensityRequest(mitotic_count=10))
    assert err.value.status_code == 422


def test_health_clearly_labels_demo_agent():
    assert health()["agent_workflow"] == "demonstration_only"


def test_index_returns_browser_app():
    assert index().path.endswith("web/index.html")


def test_browser_is_static_and_not_fabricated():
    root = Path(__file__).resolve().parents[1]
    versions = [(root / directory / "index.html").read_text(encoding="utf-8")
                for directory in ("", "docs", "web")]
    assert versions[0] == versions[1] == versions[2]
    assert "mitoses/mm²" in versions[0]
    assert "Processed locally in this browser" in versions[0]
    assert "fetch('/api/audit'" not in versions[0]
    assert "Air-Gapped Active" not in versions[0]


def test_browser_javascript_parses():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js not installed for browser syntax check")
    html = (Path(__file__).resolve().parents[1] / "index.html").read_text()
    javascript = re.search(r"<script>(.*?)</script>", html, re.DOTALL).group(1)
    result = subprocess.run([node, "--check"], input=javascript,
                            text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
