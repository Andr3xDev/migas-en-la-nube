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
        values = dict(attrs)
        self.violations += [
            f"inline handler {name} on <{tag}>" for name in names if name.startswith("on")
        ]
        if (values.get("href") or "").strip().lower().startswith("javascript:"):
            self.violations.append(f"javascript: href on <{tag}>")
        if tag == "script" and (values.get("src") or "").strip().startswith(("http", "//")):
            self.violations.append("external <script src>")


@pytest.mark.parametrize(
    "html",
    [
        "<script>alert(1)</script>",
        "<style>a{}</style>",
        '<p style="color:red">x</p>',
        '<button onclick="go()">x</button>',
        '<a href="javascript:go()">x</a>',
        '<script src="https://cdn.example.com/a.js"></script>',
        '<script src="//cdn.example.com/a.js"></script>',
    ],
)
def test_csp_finder_flags_violation(html: str) -> None:
    finder = CspViolationFinder()
    finder.feed(html)
    assert len(finder.violations) == 1


def test_web_files_are_discovered() -> None:
    assert HTML_FILES
    assert JS_FILES


@pytest.mark.parametrize("path", HTML_FILES, ids=lambda p: str(p.relative_to(WEB_DIR)))
def test_html_has_no_inline_script_or_style(path: Path) -> None:
    finder = CspViolationFinder()
    finder.feed(path.read_text(encoding="utf-8"))
    assert finder.violations == []


@pytest.mark.parametrize("path", JS_FILES, ids=lambda p: str(p.relative_to(WEB_DIR)))
def test_js_does_not_write_raw_html(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    assert [api for api in RAW_HTML_APIS if api in source] == []
