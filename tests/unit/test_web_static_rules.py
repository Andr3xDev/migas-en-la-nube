from html.parser import HTMLParser
from pathlib import Path

import pytest

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
HTML_FILES = sorted(WEB_DIR.rglob("*.html"))
JS_FILES = sorted(WEB_DIR.rglob("*.js"))
RAW_HTML_APIS = ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write")


class CspViolationFinder(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.violations: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        names = {name for name, _ in attrs}
        if tag == "script" and "src" not in names:
            self.violations.append("inline <script>")
        if tag == "style":
            self.violations.append("<style> tag")
        if "style" in names:
            self.violations.append(f"style attribute on <{tag}>")


def test_web_files_are_discovered() -> None:
    assert HTML_FILES
    assert JS_FILES


@pytest.mark.parametrize("path", HTML_FILES, ids=lambda p: str(p.relative_to(WEB_DIR)))
def test_html_has_no_inline_script_or_style(path: Path) -> None:
    finder = CspViolationFinder()
    finder.feed(path.read_text(encoding="utf-8"))
    assert finder.violations == []


@pytest.mark.parametrize("path", HTML_FILES, ids=lambda p: str(p.relative_to(WEB_DIR)))
def test_html_loads_auth_boot_before_stylesheet(path: Path) -> None:
    html = path.read_text(encoding="utf-8")
    head = html.split("</head>")[0]
    boot = head.find('<script src="/js/auth-boot.js"></script>')
    stylesheet = head.find('rel="stylesheet"')
    assert 0 <= boot < stylesheet


@pytest.mark.parametrize("path", JS_FILES, ids=lambda p: str(p.relative_to(WEB_DIR)))
def test_js_does_not_write_raw_html(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    assert [api for api in RAW_HTML_APIS if api in source] == []
