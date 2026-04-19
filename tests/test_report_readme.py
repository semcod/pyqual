from __future__ import annotations

from pyqual.report import BADGE_END, BADGE_START, _read_costs_data, _replace_badges_in_text


def test_read_costs_data_missing_file() -> None:
    data = _read_costs_data(None)
    assert data == {} or isinstance(data, dict)


def test_update_readme_badges_noop_markers() -> None:
    text = f"before\n{BADGE_START}\nold\n{BADGE_END}\nafter"
    updated = _replace_badges_in_text(text, "new badges")
    assert BADGE_START in updated
    assert BADGE_END in updated
    assert "new badges" in updated
