import json
from datetime import date
from pathlib import Path

import pytest

from datacleaner import InputError, process_file


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
TODAY = date(2026, 10, 6)


@pytest.mark.parametrize("suffix", ["csv", "xlsx"])
def test_portfolio_example_matches_expected_files(suffix):
    source = EXAMPLES / f"sample_customers.{suffix}"
    result = process_file(source.read_bytes(), source.name, today=TODAY)
    assert result.summary == json.loads((EXAMPLES / "expected_summary.json").read_text(encoding="utf-8"))
    assert result.clean_csv == (EXAMPLES / "expected_clean_customers.csv").read_bytes()
    assert result.errors_csv == (EXAMPLES / "expected_errors.csv").read_bytes()


def test_invalid_row_does_not_reserve_duplicate_email():
    source = (
        "name,email,phone,birth_date\n"
        ",same@example.com,,\n"
        "First Valid,same@example.com,,\n"
        "Second Valid,SAME@example.com,,\n"
    ).encode()
    result = process_file(source, "customers.csv", today=TODAY)
    assert result.summary == {"received": 3, "valid": 1, "invalid": 1, "duplicate": 1}
    assert b"First Valid,same@example.com" in result.clean_csv
    assert b"first valid occurrence on row 3" in result.errors_csv


def test_rejects_bad_header_and_wrong_row_width():
    with pytest.raises(InputError) as error:
        process_file(b"name,email,phone\nAna,a@example.com,11999999999\n", "bad.csv")
    assert error.value.code == "INVALID_HEADER"

    result = process_file(b"name,email,phone,birth_date\nAna,a@example.com\n", "bad.csv")
    assert result.summary == {"received": 1, "valid": 0, "invalid": 1, "duplicate": 0}
    assert b"INVALID_ROW" in result.errors_csv


def test_blank_rows_are_not_counted_and_dates_are_strict():
    source = (
        "name,email,phone,birth_date\n"
        "\n"
        "Ana,ana@example.com,,29/02/2024\n"
        "Bia,bia@example.com,,29/02/2023\n"
    ).encode()
    result = process_file(source, "customers.csv", today=TODAY)
    assert result.summary == {"received": 2, "valid": 1, "invalid": 1, "duplicate": 0}
    assert b"2024-02-29" in result.clean_csv
    assert b"4,birth_date,29/02/2023,INVALID_DATE" in result.errors_csv
