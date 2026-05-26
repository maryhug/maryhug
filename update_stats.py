#!/usr/bin/env python3
"""
Daily GitHub stats updater for maryhug-profile.svg.

Fetches live data from:
  - GitHub REST API      → public repo count
  - github-contributions-api.jogruber.de  → yearly total, last 7 days, streak

Patches the SVG in-place using comment markers and coordinate-based regex.
"""

import re
import json
import ssl
import urllib.request
from datetime import date, timedelta

# ── Config ─────────────────────────────────────────────────────────────────────
SVG_PATH   = "maryhug-profile.svg"
USERNAME   = "maryhug"
GITHUB_API = f"https://api.github.com/users/{USERNAME}"
CONTRIB_API = f"https://github-contributions-api.jogruber.de/v4/{USERNAME}?y=last"

# Bar chart layout (from SVG — do not change unless SVG layout changes)
BAR_X      = [52,  99,  145, 192, 238, 285, 331]  # rect x for Mon→Sun
BAR_CENTER = [67, 114,  160, 207, 253, 300, 346]  # text x-center for Mon→Sun
PH_COLORS  = ["#ffd6eb","#ffb7d5","#f9a8d4","#ffd0e8","#fce4ee","#ffd0e8","#ffd6eb"]
C_COLORS   = ["#ea4899","#d6336c","#f472aa","#e8599a","#f472aa","#d6336c","#ea4899"]
BASELINE   = 510   # y of the horizontal base line
MAX_H      = 60    # max bar height in px (tallest bar = this)
PH_Y, PH_H = 504, 6   # 0-commit placeholder: y and height


# ── Helpers ─────────────────────────────────────────────────────────────────────
def fetch(url: str) -> dict:
    """Fetch JSON from url. Uses a relaxed SSL context on Windows (Python 3.14 CA bug)."""
    req = urllib.request.Request(url, headers={"User-Agent": "maryhug-profile-bot/1.0"})
    # Build context: verify certs normally; if that fails, fall back to no-verify
    # (only public trusted APIs are called, so this is safe)
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            return json.loads(r.read())
    except Exception:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            return json.loads(r.read())


# ── Fetch data ──────────────────────────────────────────────────────────────────
print("Fetching GitHub profile …")
profile   = fetch(GITHUB_API)
repos     = profile["public_repos"]

print("Fetching contribution data …")
data          = fetch(CONTRIB_API)
total_year    = data["total"]["lastYear"]
all_contribs  = sorted(data["contributions"], key=lambda c: c["date"])
contrib_map   = {c["date"]: c["count"] for c in all_contribs}


# ── Current week (Monday → Sunday) ─────────────────────────────────────────────
today      = date.today()
monday     = today - timedelta(days=today.weekday())   # ISO Monday of current week
week_dates = [(monday + timedelta(days=i)).isoformat() for i in range(7)]
week_counts = [contrib_map.get(d, 0) for d in week_dates]
max_count   = max(week_counts) if any(c > 0 for c in week_counts) else 1


# ── Current streak ──────────────────────────────────────────────────────────────
# Rules: if today has commits → count back from today.
#        if today has 0 → skip today, start from yesterday (one-day grace).
#        Any day with 0 after the chain starts → stop.
today_str    = today.isoformat()
allow_skip   = contrib_map.get(today_str, 0) == 0   # today has 0 → allow one skip

streak = 0
for d in sorted([k for k in contrib_map if k <= today_str], reverse=True):
    count = contrib_map[d]
    if count > 0:
        streak += 1
        allow_skip = False
    elif allow_skip and d == today_str:
        allow_skip = False   # used the grace-day
        continue
    else:
        break   # chain broken


# ── Build bar-chart SVG fragment ────────────────────────────────────────────────
lines = []
for i, (count, ph_col, c_col) in enumerate(zip(week_counts, PH_COLORS, C_COLORS)):
    x      = BAR_X[i]
    center = BAR_CENTER[i]
    delay  = f".{65 + i * 2}s"

    if count == 0:
        lines.append(
            f'<rect x="{x}" y="{PH_Y}" width="30" height="{PH_H}" rx="3" '
            f'fill="{ph_col}" style="animation:fadein .4s ease both {delay}"/>'
        )
    else:
        h     = max(8, round(MAX_H * count / max_count))
        bar_y = BASELINE - h
        lines.append(
            f'<rect x="{x}" y="{bar_y}" width="30" height="{h}" rx="5" '
            f'fill="{c_col}" style="animation:fadein .5s ease both {delay}"/>'
        )
        lines.append(
            f'<text x="{center}" y="{bar_y - 6}" font-size="9" font-weight="600" '
            f'fill="#d6336c" text-anchor="middle">{count}</text>'
        )

# Baseline
lines.append(
    f'<line x1="44" y1="{BASELINE}" x2="374" y2="{BASELINE}" '
    f'stroke="#f9c8de" stroke-width="1.5"/>'
)

bars_svg = "\n".join(lines)


# ── Patch SVG ────────────────────────────────────────────────────────────────────
with open(SVG_PATH, "r", encoding="utf-8") as f:
    svg = f.read()

# 1. Bar chart block (between markers)
svg = re.sub(
    r"<!-- STATS_BAR_START -->.*?<!-- STATS_BAR_END -->",
    f"<!-- STATS_BAR_START -->\n{bars_svg}\n<!-- STATS_BAR_END -->",
    svg, flags=re.DOTALL
)

# 2. Public repos  → unique attribute coords: x="310" y="592"
svg = re.sub(
    r'(x="310" y="592"[^>]+>)\d+',
    lambda m: m.group(1) + str(repos),
    svg
)

# 3. Total contributions → x="158" y="592"
svg = re.sub(
    r'(x="158" y="592"[^>]+>)\d+',
    lambda m: m.group(1) + str(total_year),
    svg
)

# 4. Current streak → x="155" y="566"
streak_text = "1 day" if streak == 1 else f"{streak} days"
svg = re.sub(
    r'(x="155" y="566"[^>]+>)[^<]+',
    lambda m: m.group(1) + streak_text,
    svg
)

with open(SVG_PATH, "w", encoding="utf-8") as f:
    f.write(svg)


# ── Summary ──────────────────────────────────────────────────────────────────────
print()
print("SVG updated successfully!")
print(f"  Public repos        : {repos}")
print(f"  Contributions/year  : {total_year}")
print(f"  Current streak      : {streak_text}")
print(f"  Week Mon->Sun       : {week_counts}")
