"""Regression coverage for concise, consistent admissions pages."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "frontend" / "templates"
SCRIPTS = ROOT / "frontend" / "static" / "js"


def test_admissions_steps_never_skip_a_number():
    html = (TEMPLATES / "administrator" / "admissions.html").read_text(
        encoding="utf-8"
    )
    numbers = re.findall(r'class="admissions-step-number">(\d+)</span>', html)
    assert numbers == ["1", "2", "3", "4"]
    assert html.count('id="official-transcript-form"') == 1
    assert html.count('id="create-student-record-form"') == 1
    assert "Official Transcript" in html
    assert 'id="process-intent"' in html


def test_no_requirement_numbers_appear_in_frontend_source():
    # Requirement IDs belong in internal documentation and tests.
    sources = list(TEMPLATES.rglob("*.html")) + list(SCRIPTS.rglob("*.js"))
    failures = []
    for file in sources:
        if re.search(r"\bSRS\s*\d+\.", file.read_text(encoding="utf-8")):
            failures.append(file.relative_to(ROOT).as_posix())
    assert not failures, failures


def test_advisor_loading_state_has_a_real_error_target():
    html = (TEMPLATES / "advisor" / "graduate_college.html").read_text(
        encoding="utf-8"
    )
    script = (SCRIPTS / "pages" / "reviews" / "graduate-college.js").read_text(
        encoding="utf-8"
    )
    assert 'id="gc-selection-error"' in html
    assert '$("gc-selection-error")' in script
    assert 'emptySelection.querySelector("p")' not in script
