#!/usr/bin/env python3
"""
Daily GitHub stats + Spotify updater for maryhug-profile.svg.

Fetches live data from:
  - GitHub REST API                          → public repo count
  - github-contributions-api.jogruber.de    → yearly total, last 7 days, streak
  - Spotify Web API (optional)              → currently-playing / recently-played

Patches the SVG in-place using comment markers and coordinate-based regex.

Spotify env vars (set as GitHub Secrets):
  SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN
  If any are missing, the Spotify card keeps its last committed value.
"""

import os
import re
import base64
import json
import ssl
import urllib.request
import urllib.parse
from datetime import date, timedelta

# ── Config ─────────────────────────────────────────────────────────────────────
SVG_PATH   = "maryhug-profile.svg"
USERNAME   = "maryhug"
GITHUB_API  = f"https://api.github.com/users/{USERNAME}"
CONTRIB_API = f"https://github-contributions-api.jogruber.de/v4/{USERNAME}?y=last"

SPOTIFY_TOKEN_URL   = "https://accounts.spotify.com/api/token"
SPOTIFY_NOW_URL     = "https://api.spotify.com/v1/me/player/currently-playing"
SPOTIFY_RECENT_URL  = "https://api.spotify.com/v1/me/player/recently-played?limit=1"

# Bar chart layout (from SVG — do not change unless SVG layout changes)
BAR_X      = [52,  99,  145, 192, 238, 285, 331]   # rect x for Mon→Sun
BAR_CENTER = [67, 114,  160, 207, 253, 300, 346]   # text x-center for Mon→Sun
PH_COLORS  = ["#D8D0F4","#C8BEF0","#D0C8F4","#CAC0F0","#D4CCF4","#C8BEF0","#D8D0F4"]
C_COLORS   = ["#8B7ED8","#6B60C0","#9888E0","#7868C8","#9888E0","#6B60C0","#8B7ED8"]
BASELINE   = 510   # y of the horizontal base line
MAX_H      = 60    # max bar height in px (tallest bar = this)
PH_Y, PH_H = 504, 6   # 0-commit placeholder: y and height

MAX_TITLE_LEN  = 30   # chars before truncating song title with …
MAX_ARTIST_LEN = 32   # chars before truncating artist name with …


# ── Helpers ─────────────────────────────────────────────────────────────────────
def fetch_json(url: str, headers: dict = None) -> dict | None:
    """
    GET url, return parsed JSON or None on any error.
    Falls back to ssl.CERT_NONE on SSL failures (Windows Python 3.14 CA bug).
    """
    req_headers = {"User-Agent": "maryhug-profile-bot/1.0"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)

    for verify in (True, False):
        try:
            ctx = ssl.create_default_context()
            if not verify:
                ctx.check_hostname = False
                ctx.verify_mode    = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                if r.status == 204:    # No Content (Spotify: nothing playing)
                    return None
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                print(f"  HTTP {e.code} from {url} — check credentials")
                return None
            if verify:
                continue   # try without cert check
            return None
        except Exception:
            if verify:
                continue
            return None
    return None


def post_form(url: str, data: dict, headers: dict) -> dict | None:
    """POST url-encoded form data, return parsed JSON or None."""
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=encoded, headers=headers, method="POST")

    for verify in (True, False):
        try:
            ctx = ssl.create_default_context()
            if not verify:
                ctx.check_hostname = False
                ctx.verify_mode    = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                return json.loads(r.read())
        except Exception:
            if verify:
                continue
            return None
    return None


def xml_escape(text: str) -> str:
    """Escape characters that are special in SVG/XML text content."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 1] + "…"   # …


# ── Spotify ──────────────────────────────────────────────────────────────────────
def get_access_token(client_id: str, client_secret: str, refresh_token: str) -> str | None:
    """Exchange refresh_token for a short-lived access_token."""
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    result = post_form(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type":    "refresh_token",
            "refresh_token": refresh_token,
        },
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type":  "application/x-www-form-urlencoded",
        },
    )
    if result and "access_token" in result:
        return result["access_token"]
    print("  Could not get Spotify access token:", result)
    return None


def get_now_playing(access_token: str) -> tuple[str, str] | None:
    """
    Returns (title, artist) for the currently-playing or most-recently-played track.
    Returns None if Spotify creds are unavailable or API fails.
    """
    auth_header = {"Authorization": f"Bearer {access_token}"}

    # 1. Try currently-playing first
    data = fetch_json(SPOTIFY_NOW_URL, headers=auth_header)
    if data and data.get("is_playing") and data.get("item"):
        item   = data["item"]
        title  = item.get("name", "")
        artist = ", ".join(a["name"] for a in item.get("artists", []))
        return title, artist

    # 2. Fall back to recently-played
    data = fetch_json(SPOTIFY_RECENT_URL, headers=auth_header)
    if data and data.get("items"):
        item   = data["items"][0]["track"]
        title  = item.get("name", "")
        artist = ", ".join(a["name"] for a in item.get("artists", []))
        return title, artist

    return None


# ── Fetch GitHub data ────────────────────────────────────────────────────────────
print("Fetching GitHub profile …")
profile  = fetch_json(GITHUB_API)
repos    = profile["public_repos"] if profile else "—"

print("Fetching contribution data …")
contrib_data = fetch_json(CONTRIB_API)
total_year   = contrib_data["total"]["lastYear"] if contrib_data else 0
all_contribs = sorted(contrib_data.get("contributions", []), key=lambda c: c["date"])
contrib_map  = {c["date"]: c["count"] for c in all_contribs}


# ── Current week (Monday → Sunday) ─────────────────────────────────────────────
today       = date.today()
monday      = today - timedelta(days=today.weekday())
week_dates  = [(monday + timedelta(days=i)).isoformat() for i in range(7)]
week_counts = [contrib_map.get(d, 0) for d in week_dates]
max_count   = max(week_counts) if any(c > 0 for c in week_counts) else 1


# ── Current streak ──────────────────────────────────────────────────────────────
today_str  = today.isoformat()
allow_skip = contrib_map.get(today_str, 0) == 0

streak = 0
for d in sorted([k for k in contrib_map if k <= today_str], reverse=True):
    count = contrib_map[d]
    if count > 0:
        streak += 1
        allow_skip = False
    elif allow_skip and d == today_str:
        allow_skip = False
        continue
    else:
        break


# ── Spotify: fetch now-playing ───────────────────────────────────────────────────
spotify_client_id     = os.environ.get("SPOTIFY_CLIENT_ID", "")
spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
spotify_refresh_token = os.environ.get("SPOTIFY_REFRESH_TOKEN", "")

spotify_title  = None
spotify_artist = None

if all([spotify_client_id, spotify_client_secret, spotify_refresh_token]):
    print("Fetching Spotify now-playing …")
    access_token = get_access_token(spotify_client_id, spotify_client_secret, spotify_refresh_token)
    if access_token:
        result = get_now_playing(access_token)
        if result:
            spotify_title, spotify_artist = result
            print(f"  Now playing: {spotify_title} — {spotify_artist}")
        else:
            print("  No track data returned from Spotify.")
    else:
        print("  Skipping Spotify — could not get access token.")
else:
    print("Spotify env vars not set — skipping Spotify update.")


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

lines.append(
    f'<line x1="44" y1="{BASELINE}" x2="374" y2="{BASELINE}" '
    f'stroke="#f9c8de" stroke-width="1.5"/>'
)

bars_svg = "\n".join(lines)


# ── Patch SVG ─────────────────────────────────────────────────────────────────────
with open(SVG_PATH, "r", encoding="utf-8") as f:
    svg = f.read()

# 1. Bar chart block (between markers)
svg = re.sub(
    r"<!-- STATS_BAR_START -->.*?<!-- STATS_BAR_END -->",
    f"<!-- STATS_BAR_START -->\n{bars_svg}\n<!-- STATS_BAR_END -->",
    svg, flags=re.DOTALL
)

# 2. Public repos → x="310" y="592"
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

# 5. Spotify song title → x="80" y="430"  (only if we got data)
if spotify_title:
    safe_title = xml_escape(truncate(spotify_title, MAX_TITLE_LEN))
    svg = re.sub(
        r'(x="80" y="430"[^>]+>)[^<]+',
        lambda m: m.group(1) + safe_title,
        svg
    )

# 6. Spotify artist → x="80" y="444"
if spotify_artist:
    safe_artist = xml_escape(truncate(spotify_artist, MAX_ARTIST_LEN))
    svg = re.sub(
        r'(x="80" y="444"[^>]+>)[^<]+(?=<\/text>)',
        lambda m: m.group(1) + safe_artist,
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
if spotify_title:
    print(f"  Now playing         : {spotify_title} — {spotify_artist}")
