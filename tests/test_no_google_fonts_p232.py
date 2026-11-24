"""P232: the web UI serves its own fonts; nothing loads from Google Fonts.

Fails if a Google Fonts host comes back in the web app's source, its HTML
or the nginx configs (which would also need the CSP loosened again)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")
WHERE = [ROOT / "apps" / "web" / "src", ROOT / "apps" / "web" / "index.html", ROOT / "infra"]
SUFFIXES = {".css", ".ts", ".tsx", ".js", ".jsx", ".html", ".conf"}


def _files():
    for base in WHERE:
        if base.is_file():
            yield base
        elif base.is_dir():
            for p in base.rglob("*"):
                if p.is_file() and p.suffix in SUFFIXES and "node_modules" not in p.parts:
                    yield p


def test_no_google_fonts_hosts():
    hits = [f"{p.relative_to(ROOT)}: {h}" for p in _files() for h in HOSTS
            if h in p.read_text(encoding="utf-8", errors="ignore")]
    assert not hits, "Google Fonts is back (P232: bundle fonts instead):\n" + "\n".join(hits)


def test_fonts_are_bundled():
    pkg = (ROOT / "apps" / "web" / "package.json").read_text(encoding="utf-8")
    main = (ROOT / "apps" / "web" / "src" / "main.tsx").read_text(encoding="utf-8")
    for family in ("instrument-sans", "inter", "manrope", "geist-mono"):
        assert f'"@fontsource-variable/{family}"' in pkg
        assert f'import "@fontsource-variable/{family}";' in main
