#!/usr/bin/env python3
"""Render captured terminal output as a PNG that looks like a terminal window.

The rubric asks for screenshots of command output (pytest, docker compose, kubectl, trivy ...).
Capturing real terminal windows by hand gives inconsistent sizes and fonts, so instead I keep the raw
text in docs/screenshots/<name>.txt (greppable, diffable) and render the picture from it.

Usage:
    scripts/render-terminal.py INPUT.txt --title "pytest -v" [-o OUTPUT.png] [--width 1100] [--html-only]
    some-command | scripts/render-terminal.py - --title "kubectl get pods" -o docs/screenshots/pods.png

How it works:
    1. the text is HTML-escaped and wrapped in a small dark-theme page (title bar, traffic lights,
       monospace body) -> OUTPUT.html next to the PNG
    2. the page is screenshotted with Playwright's CLI:
           npx --yes playwright@1.56 screenshot --full-page file://OUTPUT.html OUTPUT.png
       (first run downloads the package; browsers may need `npx --yes playwright@1.56 install chromium`)
    3. if npx/Playwright is unavailable or fails, the HTML file is kept and the script exits 0 with a
       notice, so an evidence capture never fails just because of the renderer. Open the HTML in a
       browser and screenshot it by hand in that case.

ANSI colour codes are stripped before rendering; use NO_COLOR=1 / TERM=dumb when capturing if the
tool supports it (scripts/capture-evidence.sh does this).
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PLAYWRIGHT_SPEC = "playwright@1.56"
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07|\r")

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  :root {{ color-scheme: dark; }}
  html, body {{ margin: 0; background: #1b1f27; }}
  body {{ padding: 28px; width: {width}px; box-sizing: border-box; font-family: -apple-system, "Segoe UI", sans-serif; }}
  .window {{ background: #0f1117; border-radius: 10px; box-shadow: 0 18px 50px rgba(0,0,0,.55); overflow: hidden; border: 1px solid #2a2f3a; }}
  .bar {{ display: flex; align-items: center; height: 38px; background: #1c2029; border-bottom: 1px solid #2a2f3a; position: relative; }}
  .lights {{ display: flex; gap: 8px; padding-left: 14px; }}
  .lights span {{ width: 12px; height: 12px; border-radius: 50%; display: block; }}
  .lights .r {{ background: #ff5f57; }} .lights .y {{ background: #febc2e; }} .lights .g {{ background: #28c840; }}
  .title {{ position: absolute; left: 0; right: 0; text-align: center; color: #9aa3b2; font-size: 13px; pointer-events: none; }}
  pre {{ margin: 0; padding: 18px 20px 22px; color: #e6e9ef; font: 13px/1.45 "SF Mono", Menlo, Consolas, "DejaVu Sans Mono", monospace; white-space: pre-wrap; word-break: break-word; tab-size: 4; }}
  .prompt {{ color: #7ee787; font-weight: 600; }}
  .footer {{ color: #5c6475; font: 11px -apple-system, "Segoe UI", sans-serif; text-align: right; padding: 10px 28px 0; }}
</style>
</head>
<body>
<div class="window">
  <div class="bar">
    <div class="lights"><span class="r"></span><span class="y"></span><span class="g"></span></div>
    <div class="title">{title}</div>
  </div>
<pre>{body}</pre>
</div>
<div class="footer">{footer}</div>
</body>
</html>
"""


def read_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8", errors="replace")


def to_html_body(text: str) -> str:
    """Escape the text; lines starting with `$ ` are highlighted as prompts."""
    text = ANSI_RE.sub("", text).rstrip("\n")
    out = []
    for line in text.split("\n"):
        esc = html.escape(line)
        if line.startswith("$ "):
            esc = f'<span class="prompt">$</span> {html.escape(line[2:])}'
        out.append(esc)
    return "\n".join(out)


def write_html(text: str, title: str, width: int, footer: str, html_path: Path) -> None:
    html_path.write_text(
        HTML_TEMPLATE.format(
            title=html.escape(title), body=to_html_body(text), width=width, footer=html.escape(footer)
        ),
        encoding="utf-8",
    )


def screenshot(html_path: Path, png_path: Path, width: int) -> bool:
    """Render html_path to png_path with Playwright's CLI. Returns True on success."""
    npx = shutil.which("npx")
    if not npx:
        print("render-terminal: npx not found (install Node 22); keeping the HTML only.", file=sys.stderr)
        return False
    cmd = [
        npx, "--yes", PLAYWRIGHT_SPEC, "screenshot",
        "--full-page",
        "--browser", "chromium",
        # A short viewport: --full-page grows the capture to the content height but never shrinks
        # it, so a tall default viewport would leave dead space under short outputs.
        f"--viewport-size={width},120",
        html_path.resolve().as_uri(),
        str(png_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"render-terminal: playwright failed to start: {exc}", file=sys.stderr)
        return False
    if proc.returncode != 0 or not png_path.exists():
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-5:]
        print("render-terminal: playwright screenshot failed:\n  " + "\n  ".join(tail), file=sys.stderr)
        print(f"  hint: npx --yes {PLAYWRIGHT_SPEC} install chromium", file=sys.stderr)
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("input", help="captured terminal output (.txt) or '-' for stdin")
    parser.add_argument("--title", "-t", default=None, help="window title (default: input file name)")
    parser.add_argument("--output", "-o", default=None, help="PNG path (default: input name with .png)")
    parser.add_argument("--width", type=int, default=1100, help="page width in px (default 1100)")
    parser.add_argument("--footer", default="", help="small caption under the window (e.g. date / commit)")
    parser.add_argument("--html-only", action="store_true", help="only write the HTML, do not run Playwright")
    args = parser.parse_args(argv)

    text = read_input(args.input)
    if args.input == "-":
        png_path = Path(args.output or "terminal.png")
    else:
        png_path = Path(args.output or Path(args.input).with_suffix(".png"))
    title = args.title or (png_path.stem if args.input == "-" else Path(args.input).name)
    html_path = png_path.with_suffix(".html")
    png_path.parent.mkdir(parents=True, exist_ok=True)

    write_html(text, title, args.width, args.footer, html_path)
    print(f"html: {html_path}")

    if args.html_only or os.environ.get("RENDER_TERMINAL_HTML_ONLY") == "1":
        return 0
    if screenshot(html_path, png_path, args.width):
        print(f"png:  {png_path}")
        try:
            html_path.unlink()  # the PNG is the evidence; the HTML was only an intermediate step
        except OSError:
            pass
        return 0
    print(f"render-terminal: PNG not produced; open {html_path} in a browser and screenshot it.", file=sys.stderr)
    return 0  # never fail the capture because of the renderer


if __name__ == "__main__":
    sys.exit(main())
