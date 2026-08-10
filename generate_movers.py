#!/usr/bin/env python3
"""
Daily movers graphic generator for InferenceIndexer.

Fetches the live SIT-Composite and the top 24h price drops/rises from the
InferenceIndexer API, renders a branded graphic (dark cream + gold), and emits
ready-to-post text for X and LinkedIn.

OUTPUTS (written to --outdir, default ./daily-movers/):
  movers_<YYYY-MM-DD>.png   - the graphic
  post_x.txt                - post text (caption only; attach movers_*.png)
  post_linkedin.txt         - LinkedIn text + image reference
  latest.jpg/.png           - copy named for easy reuse

Usage:
  python3 generate_movers.py [--outdir DIR]

Exit codes: 0 ok, 1 failure.
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timezone

# ---------------------------------------------------------------- config ----
API_BASE = "https://api.inferenceindexer.ai"
SSR_SECRET = os.environ.get("INFERENCEINDEXER_SSR_SECRET", "inferenceindexer-ssr-2026")

# Brand
GOLD = (196, 160, 56)        # #C4A038
CREAM = (245, 243, 235)      # #F5F3EB
DARK = (20, 18, 16)          # #141210
BG = (26, 24, 22)            # #1A1816
MUTED = (140, 138, 132)      # #8C8A84
GREEN = (34, 197, 94)        # #22C55E drops
RED = (239, 68, 68)          # #EF4444 rises
DIVIDER = (60, 57, 52)       # #3C3934

N_DROPS = 5
N_RISES = 5


def fetch_json(path):
    req = urllib.request.Request(
        API_BASE + path,
        headers={"X-SSR-Secret": SSR_SECRET, "User-Agent": "inferenceindexer-daily-movers/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


# ---------------------------------------------------------------- data -------
def human_model(m):
    """Use the API's human-readable name field; strip the leading provider: prefix."""
    raw = m.get("name") or m.get("model_id") or m.get("id") or ""
    # e.g. "OpenAI: GPT-5.6 Luna" -> "GPT-5.6 Luna"
    if ":" in raw:
        return raw.split(":", 1)[1].strip()
    return raw.lstrip("~").strip()


def get_data():
    models = fetch_json("/v1/models?limit=400")["models"]
    comp = fetch_json("/v1/sit/composite/latest")["composite"]

    def c24(m):
        return m.get("change_24h") or 0

    movers = [m for m in models if c24(m) != 0]
    drops = sorted(movers, key=c24)[:N_DROPS]
    rises = sorted(movers, key=lambda m: -c24(m))[:N_RISES]

    def row(m):
        return {
            "label": human_model(m),
            "chg": c24(m),
        }

    return {
        "as_of": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        "composite_price": comp.get("price_per_m"),
        "composite_chg24": comp.get("change_24h"),
        "models": comp.get("models"),
        "providers": comp.get("providers"),
        "drops": [row(m) for m in drops],
        "rises": [row(m) for m in rises],
    }


# ---------------------------------------------------------------- graphic ----
def draw_graphic(data, out_path):
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1600, 1000
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    def font(sz, bold=False):
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
        candidates = [
            os.path.join(base, "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for c in candidates:
            if os.path.exists(c):
                return ImageFont.truetype(c, sz)
        return ImageFont.load_default()

    F = 12  # margin
    # Header
    d.text((40, 36), "INFERENCEINDEXER.AI", font=font(26, True), fill=GOLD)
    d.text((40, 78), "Independent AI Inference Price Index", font=font(18), fill=MUTED)
    d.text((40, 106), data["as_of"], font=font(18), fill=MUTED)

    # Composite headline (right side)
    cprice = data["composite_price"]
    cchg = data["composite_chg24"]
    chg_col = GREEN if (cchg or 0) < 0 else RED
    d.text((W - 40, 36), f"${cprice:.2f} / M", font=font(56, True), fill=CREAM, anchor="ra")
    d.text(
        (W - 40, 108),
        f"{cchg:+.1f}% 24h   ·   {data['models']} models / {data['providers']} providers",
        font=font(18),
        fill=chg_col,
        anchor="ra",
    )

    # Main divider
    yy = 165
    d.line([(40, yy), (W - 40, yy)], fill=DIVIDER, width=2)

    # Two columns: DROPS (left) and RISES (right)
    col_w = (W - 40 * 2 - 40) // 2
    x0 = 40
    x1 = 40 + col_w + 40

    def draw_col(x, title, rows, col, is_drop):
        d.text((x, 200), title, font=font(24, True), fill=col)
        yy2 = 250
        for i, r in enumerate(rows):
            arrow = "▼" if is_drop else "▲"
            badge_w = 150  # fixed width for the % badge so names never overlap
            row_h = 54
            # % badge (left) - fixed width, color fills only up to scaled width
            bar_w = int(badge_w * min(abs(r["chg"]) / 315.0, 1.0))
            d.rounded_rectangle([x, yy2, x + badge_w, yy2 + row_h], radius=8, fill=(46, 42, 38))
            if bar_w > 6:
                d.rounded_rectangle([x, yy2, x + bar_w, yy2 + row_h], radius=8, fill=col)
            d.text(
                (x + 14, yy2 + (row_h - 28) // 2),
                f"{arrow} {r['chg']:+.0f}%",
                font=font(22, True),
                fill=CREAM,
            )
            # model name to the RIGHT of the badge (fixed offset, never under it)
            d.text((x + badge_w + 22, yy2 + 8), r["label"], font=font(20, True), fill=CREAM)
            yy2 += row_h + 12
        return yy2

    yy_d = draw_col(x0, "↓ BIGGEST PRICE DROPS (24H)", data["drops"], GREEN, True)
    yy_r = draw_col(x1, "↑ BIGGEST PRICE INCREASES (24H)", data["rises"], RED, False)

    # Footer
    footer_y = min(yy_d, yy_r) + 30
    d.line([(40, footer_y), (W - 40, footer_y)], fill=DIVIDER, width=2)
    d.text(
        (40, footer_y + 18),
        "Prices are USD per million tokens · Independent price reporting · Updated hourly",
        font=font(15),
        fill=MUTED,
    )
    d.text((W - 40, footer_y + 18), "inferenceindexer.ai · @inferenceindex", font=font(15), fill=MUTED, anchor="ra")

    img.save(out_path)
    return out_path


# ---------------------------------------------------------------- text -------
def make_x_text(data):
    lines = []
    # Composite line
    cchg = data["composite_chg24"] or 0
    arrow = "↓" if cchg < 0 else "↑" if cchg > 0 else "→"
    lines.append(f"SIT-Composite ${data['composite_price']:.2f}/M ({arrow} {abs(cchg):.1f}% 24h).")
    lines.append("")
    lines.append("Biggest price drops (24h):")
    for r in data["drops"]:
        lines.append(f"  ▼ {r['label']} {r['chg']:+.0f}%")
    lines.append("")
    lines.append("Biggest price increases (24h):")
    for r in data["rises"]:
        lines.append(f"  ▲ {r['label']} {r['chg']:+.0f}%")
    lines.append("")
    lines.append("Live at inferenceindexer.ai")
    lines.append("#AInference #LLM #pricing")
    return "\n".join(lines)


def make_linkedin_text(data):
    cchg = data["composite_chg24"] or 0
    arrow = "↓" if cchg < 0 else "↑" if cchg > 0 else "→"
    lines = []
    lines.append(
        f"Inference prices keep moving. The SIT-Composite is ${data['composite_price']:.2f} per million tokens today "
        f"({arrow} {abs(cchg):.1f}% over 24h), tracking {data['models']} top models across {data['providers']} providers."
    )
    lines.append("")
    lines.append("Biggest price drops (24h):")
    for r in data["drops"]:
        lines.append(f"  • {r['label']}: {r['chg']:+.0f}%")
    lines.append("")
    lines.append("Biggest price increases (24h):")
    for r in data["rises"]:
        lines.append(f"  • {r['label']}: {r['chg']:+.0f}%")
    lines.append("")
    lines.append(
        "The gap between frontier and budget inference is what most teams under-optimise. "
        "We publish live, independent per-model pricing so you can see where the market actually is."
    )
    lines.append("")
    lines.append("See the full index: inferenceindexer.ai")
    return "\n".join(lines)


# ---------------------------------------------------------------- main -------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily-movers"))
    ap.add_argument("--post-x", action="store_true", help="also post to X via xurl (requires authenticated xurl)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    data = get_data()

    today = date.today().isoformat()
    png_path = os.path.join(args.outdir, f"movers_{today}.png")
    draw_graphic(data, png_path)

    # Reuse copy named for easy upload
    latest = os.path.join(args.outdir, "latest.png")
    img_copy(png_path, latest)

    x_text = make_x_text(data)
    li_text = make_linkedin_text(data)
    write(os.path.join(args.outdir, "post_x.txt"), x_text + "\n")
    write(os.path.join(args.outdir, "post_linkedin.txt"), li_text + "\n")

    # Print for the agent/report
    print(f"OUT_IMAGE={png_path}")
    print("===== X POST =====")
    print(x_text)
    print("===== LINKEDIN =====")
    print(li_text)

    if args.post_x:
        post_to_x(png_path, x_text)


def write(path, text):
    with open(path, "w") as f:
        f.write(text)


def img_copy(src, dst):
    import shutil

    shutil.copy(src, dst)


def post_to_x(img_path, text):
    """Post image + text to X via xurl if available and authenticated."""
    import subprocess

    # Attach image
    out = subprocess.run(["xurl", "media", "upload", img_path], capture_output=True, text=True)
    if out.returncode != 0 or "media_id" not in out.stdout:
        print("xurl media upload failed:", out.stderr or out.stdout, file=sys.stderr)
        sys.exit(2)
    media_id = json.loads(out.stdout).get("media_id")
    res = subprocess.run(["xurl", "post", text, "--media-id", str(media_id)], capture_output=True, text=True)
    print("xurl post result:", res.stdout, res.stderr, file=sys.stderr)


if __name__ == "__main__":
    main()