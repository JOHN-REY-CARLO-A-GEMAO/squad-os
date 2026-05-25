import pytest
from dashboard import format_project_label, format_log_timestamp

def test_format_project_label():
    # Standard format
    assert format_project_label("20241027_123456_my_project") == "12:34:56 - My Project"
    # Long slug
    assert format_project_label("20241027_123456_my_long_project_name") == "12:34:56 - My Long Project Name"
    # Non-standard format
    assert format_project_label("old_project_style") == "Old Project Style"
    assert format_project_label("simple") == "Simple"

def test_format_log_timestamp():
    # ISO format
    assert format_log_timestamp("2024-10-27T12:34:56.789Z") == "12:34:56"
    assert format_log_timestamp("2024-10-27T15:00:00") == "15:00:00"
    # Invalid format
    assert format_log_timestamp("not-a-date") == "not-a-date"
    # None/Empty
    assert format_log_timestamp(None) == ""
    assert format_log_timestamp("") == ""
