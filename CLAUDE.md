# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A GitHub profile card built as a single hand-crafted SVG (`maryhug-profile.svg`). All design, layout, and dark mode logic lives inside that one file. A GitHub Actions workflow (`refresh.yml`) touches the file daily to bust GitHub's aggressive SVG cache.

## Previewing Locally

A pre-configured launch target serves the repo on port 3000:

```
npx http-server . -p 3000 --cors
```

Then open `http://localhost:3000/preview.html` in the browser.

To test dark mode: Chrome DevTools → Rendering tab → **Emulate CSS media: prefers-color-scheme: dark**.

## SVG Architecture

The card is `800 × 924 px`. All layout uses absolute coordinates — no flexbox, no foreignObject.

### Section layout

Sections are stacked vertically:

| Section | y start (visual) | Card rect |
|---|---|---|
| Header (avatar, name, bio) | 0 | — (full-width background) |
| About Me | 172 | `x=24, w=362, h=216` |
| Now Playing (Spotify) | 400 | `x=24, w=362, h=64` — outside translate |
| Tech Stack | 172 | `x=414, w=362, h=182` |
| Tools | 370 | `x=414, w=362, h=104` |
| Weekly Activity | translate+94 → `y=396` → visual y=490 | `x=24, w=362, h=190` |
| Top Languages | translate+94 → `y=396` → visual y=490 | `x=414, w=362, h=190` |
| Let's Connect | translate applied to `y=602` | `x=24, w=752, h=100` |
| Footer | translate applied to `y=708` | full-width strip |

**Key pattern**: ROW 2 onwards (Weekly Activity, Top Languages, Let's Connect, Footer) are wrapped in `<g transform="translate(0,94)">` so they sit below the right column (Tools card ends y=474). When adding vertical space above this group, increase the translate value AND the SVG/clipPath/viewBox height by the same delta.

**The "Now Playing" Spotify card** lives outside the translate group at `y=400` (visual). It fits in the gap between About Me (ends y=388) and the translate group visual start (y=490).

**LET'S CONNECT buttons** are wrapped in `<a href>` elements for GitHub, LinkedIn, and Email links. SVG `<a>` uses `href` (not `xlink:href`) and `target="_blank"`.

### Color palette

| Token | Light | Dark |
|---|---|---|
| Rose accent | `#d6336c` | `#f472aa` |
| Body text | `#4a1030` | `#ffeaf4` |
| Muted text | `#9b5070` | `#c89ab6` |
| Card background | `white` | `#231018` |
| Pill background | `#fff0f6` | `#2d1222` |
| Borders/lines | `#f9c8de` | `#4a1a2e` |

### Dark mode

Dark mode uses CSS attribute selectors inside a `@media(prefers-color-scheme:dark)` block in the `<style>` tag (lines 3–15). This overrides SVG presentational attributes without touching the markup. The background switches from gradient `#bgG` to `#bgGdark` via `rect[fill="url(#bgG)"] { fill: url(#bgGdark); }`.

### Gradients defined in `<defs>`

- `bgG` / `bgGdark` — full-card background
- `barG` — vertical bar chart bars (rose gradient)
- `tsG`, `jsG`, `htmlG`, `cssG` — horizontal language bars
- `b1g`–`b5g`, `hG` — header name text and banner strip
- `#cs` filter — card drop shadow (rose, 9% opacity)

### Coordinate rules

- Inner content padding: `x=44` (left margin inside full-width cards), `x=434` inside right-column cards (x=414+20)
- Card border rects always come in pairs: a `fill="white"` rect with `filter="url(#cs)"` and a `fill="none" stroke="#f9c8de"` border rect at identical coordinates
- Text baselines: for `height=24` pills, text `y = rect_y + 16`; for `height=18` pills, text `y = rect_y + 12`

## GitHub Cache

GitHub caches SVGs for several hours. The `refresh.yml` workflow runs daily to inject `<!-- cache:YYYY-MM-DD -->` into the SVG, forcing GitHub to re-fetch it and pick up any fresh external API data (github-readme-stats, streak-stats).
