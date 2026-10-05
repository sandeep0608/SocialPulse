#!/usr/bin/env python3
"""
generate_dashboard.py — build the Social Pulse dashboard as a single, shareable
HTML file.

One command turns a weekly Posts CSV (and, optionally, monthly Kit/ConvertKit
broadcast CSVs) into a self-contained `dashboard.html` — no server, no build
step, no internet needed to view the result.

Examples
--------
Social only:
    python generate_dashboard.py --posts data/sample_posts.csv

Social + one email list:
    python generate_dashboard.py --posts data/sample_posts.csv \\
        --email data/sample_broadcasts.csv:"Nimbus Weekly"

Social + two email lists (repeat --email; the Email tab gets a property switcher):
    python generate_dashboard.py --posts data/posts.csv \\
        --email data/list_a.csv:"Main" --email data/list_b.csv:"Academy"

Output goes to output/dashboard.html by default (override with --output).
"""
import argparse
import json
import sys
from pathlib import Path

from src import social, enrich, email_report

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "templates" / "dashboard.html"
OUTDIR = ROOT / "output"


def embed(obj) -> str:
    """Serialise a dict for safe inlining inside a <script> tag."""
    text = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    # stop a stray "</script>" inside post/email text from closing the tag early
    return text.replace("</", "<\\/")


def main():
    ap = argparse.ArgumentParser(
        description="Build the Social Pulse dashboard (single self-contained HTML file).",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--posts", required=True, help="VistaSocial / native Posts CSV")
    ap.add_argument("--email", action="append", default=[], metavar="CSV:PROPERTY",
                    help='Kit/ConvertKit broadcasts CSV + label, e.g. data/b.csv:"Nimbus Weekly". '
                         "Repeat for multiple lists.")
    ap.add_argument("--output", default=str(OUTDIR / "dashboard.html"),
                    help="Output HTML path (default: output/dashboard.html)")
    args = ap.parse_args()

    posts = Path(args.posts)
    if not posts.exists():
        sys.exit(f"Posts CSV not found: {posts}")

    print("[1/4] Building social cube …")
    cube = social.build(str(posts))
    print(f"      {cube['meta']['n_posts']:,} posts · {cube['meta']['n_channels']} channels · "
          f"{cube['meta']['n_platforms']} platforms · {len(cube['meta']['weeks'])} weeks")

    print("[2/4] Enriching week-scoped insights …")
    cube = enrich.enrich(cube, str(posts))

    email_data = email_report.empty()
    if args.email:
        print(f"[3/4] Building email data ({len(args.email)} list(s)) …")
        for spec in args.email:
            if ":" not in spec:
                sys.exit(f"--email expects CSV:PROPERTY, got {spec!r}")
            csv, prop = spec.rsplit(":", 1)
            csv_path = Path(csv)
            if not csv_path.exists():
                sys.exit(f"Email CSV not found: {csv_path}")
            email_report.add_property(email_data, str(csv_path), prop.strip().strip('"'))
    else:
        print('[3/4] No --email given; the Email tab will show "no data loaded".')

    print("[4/4] Rendering dashboard HTML …")
    tpl = TEMPLATE.read_text()
    tpl = tpl.replace("__DATA__", embed(cube)).replace("__EMAIL__", embed(email_data))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(tpl)
    kb = out.stat().st_size // 1024
    print(f"\n✅  Done → {out}  ({kb} KB)")
    print("Open it in any browser, or upload/publish it wherever you host static files.")


if __name__ == "__main__":
    main()
