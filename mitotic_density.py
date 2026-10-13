#!/usr/bin/env python3
"""Calibrated mitotic density calculation for microscopy and digital pathology.

This module performs geometric area normalization only. It does not assign
histological grades, diagnoses, prognoses, or treatment recommendations.
"""
import argparse
import csv
import json
import math
import os
from pathlib import PureWindowsPath
import tempfile


def _nonnegative_integer(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a non-negative integer")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a non-negative integer") from exc
    if not math.isfinite(number) or not number.is_integer() or number < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return int(number)


def _positive_finite(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite positive number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite positive number") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return number


def calculate_metrics(mitotic_count, field_diameter_mm=None, fields_counted=10,
                      measured_area_mm2=None):
    """Express observed mitoses per square millimetre of *assessed tissue*.

    Specify exactly one area calibration:
      * field_diameter_mm: diameter of a calibrated circular high-power field;
        counted fields must not overlap and should be fully assessable.
      * measured_area_mm2: directly measured total assessed tissue area (WSI).

    Values are not rounded internally. Reporting/rounding rules vary by tumour.
    """
    count = _nonnegative_integer(mitotic_count, "mitotic_count")
    fields = _nonnegative_integer(fields_counted, "fields_counted")
    if fields == 0:
        raise ValueError("fields_counted must be greater than zero")
    if (field_diameter_mm is None) == (measured_area_mm2 is None):
        raise ValueError("Provide exactly one of field_diameter_mm or measured_area_mm2")

    diameter = None
    field_area = None
    if field_diameter_mm is not None:
        diameter = _positive_finite(field_diameter_mm, "field_diameter_mm")
        field_area = math.pi * (diameter / 2.0) ** 2
        total_area = field_area * fields
    else:
        total_area = _positive_finite(measured_area_mm2, "measured_area_mm2")

    if not math.isfinite(total_area) or total_area <= 0:
        raise ValueError("Calculated area is outside the supported numeric range")
    density = count / total_area
    if not math.isfinite(density):
        raise ValueError("Calculated density is outside the supported numeric range")

    return {
        "tool": "mitotic-count-density-standardizer",
        "mitotic_count": count,
        "fields_counted": fields,
        "field_diameter_mm": diameter,
        "field_area_mm2": field_area,
        "total_area_mm2": total_area,
        "mitoses_per_mm2": density,
        "score": density,  # Backward-compatible alias; units are mitoses/mm².
        "classification": "Not assigned (tissue-specific)",
        "clinical_recommendation": "None; measurement conversion only.",
        "inputs_evaluated": 3,
    }


def _validate_safe_path(path, must_exist=False):
    """Reject null bytes and protected OS paths; allow normal local CSV paths."""
    if not path or "\x00" in str(path):
        raise ValueError("Invalid file path: empty or contains null bytes")
    path = os.fspath(path)
    win = PureWindowsPath(path)
    if win.drive and win.root:
        parts = [part.casefold() for part in win.parts]
        if parts[0].casefold().startswith("c:") and len(parts) > 1 and parts[1] in (
            "windows", "program files", "programdata"
        ):
            raise ValueError(f"Access denied: restricted system location: {path}")
    normalized = os.path.realpath(os.path.abspath(path))
    if os.name != "nt":
        for system_dir in ("/etc", "/proc", "/sys", "/dev"):
            if normalized == system_dir or normalized.startswith(system_dir + os.sep):
                raise ValueError(f"Access denied: restricted system location: {path}")
    if must_exist and not os.path.isfile(normalized):
        raise FileNotFoundError(f"Input file not found: {path}")
    return normalized


def _safe_csv_cell(value):
    """Avoid spreadsheet formula execution when exported CSV is opened in Excel."""
    text = "" if value is None else str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def process_batch(input_csv, output_csv):
    source = _validate_safe_path(input_csv, must_exist=True)
    destination = _validate_safe_path(output_csv)
    if os.path.normcase(source) == os.path.normcase(destination):
        raise ValueError("Input and output files must differ")
    computed = ["mitoses_per_mm2", "total_area_mm2", "field_area_mm2"]
    output_dir = os.path.dirname(destination)
    os.makedirs(output_dir, exist_ok=True)
    temp_name = None
    try:
        with open(source, encoding="utf-8-sig", newline="") as inp:
            reader = csv.DictReader(inp)
            headers = reader.fieldnames
            if not headers or len(set(headers)) != len(headers) or any(not h for h in headers):
                raise ValueError("CSV needs a header row with unique, nonempty columns")
            if "mitotic_count" not in headers:
                raise ValueError("CSV requires a mitotic_count column")
            if not ("field_diameter_mm" in headers or "measured_area_mm2" in headers):
                raise ValueError("CSV requires field_diameter_mm or measured_area_mm2")
            if any(c in headers for c in computed):
                raise ValueError("Input already has reserved computed output columns")

            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="",
                                             dir=output_dir, prefix=".mitotic-", suffix=".csv",
                                             delete=False) as out:
                temp_name = out.name
                writer = csv.DictWriter(out, fieldnames=headers + computed)
                writer.writerow({name: _safe_csv_cell(name) for name in headers + computed})
                processed = 0
                for row_number, row in enumerate(reader, 2):
                    if None in row:
                        raise ValueError(f"Row {row_number}: more fields than CSV headers")
                    try:
                        result = calculate_metrics(
                            mitotic_count=row.get("mitotic_count"),
                            field_diameter_mm=row.get("field_diameter_mm") or None,
                            fields_counted=row.get("fields_counted") or 10,
                            measured_area_mm2=row.get("measured_area_mm2") or None,
                        )
                    except ValueError as exc:
                        raise ValueError(f"Row {row_number}: {exc}") from exc
                    safe_row = {k: _safe_csv_cell(v) for k, v in row.items()}
                    safe_row.update({k: result[k] for k in computed})
                    writer.writerow(safe_row)
                    processed += 1
        os.replace(temp_name, destination)
        temp_name = None
    finally:
        if temp_name is not None and os.path.exists(temp_name):
            os.unlink(temp_name)
    print(f"Processed {processed} records -> {destination}")
    return processed


def main(argv=None):
    parser = argparse.ArgumentParser(description="Normalize observed mitoses to mitoses/mm²")
    sub = parser.add_subparsers(dest="command", required=True)
    single = sub.add_parser("single", help="Calculate one observation")
    single.add_argument("--mitotic-count", required=True, type=int)
    group = single.add_mutually_exclusive_group(required=True)
    group.add_argument("--field-diameter-mm", type=float)
    group.add_argument("--measured-area-mm2", type=float)
    single.add_argument("--fields-counted", type=int, default=10)
    batch = sub.add_parser("batch", help="Convert a CSV batch")
    batch.add_argument("-i", "--input", required=True)
    batch.add_argument("-o", "--output", default="results.csv")
    args = parser.parse_args(argv)
    try:
        if args.command == "single":
            result = calculate_metrics(args.mitotic_count, args.field_diameter_mm,
                                       args.fields_counted, args.measured_area_mm2)
            print(json.dumps(result, indent=2, allow_nan=False))
        else:
            process_batch(args.input, args.output)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
