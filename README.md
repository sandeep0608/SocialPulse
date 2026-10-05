<div align="center">

# 📊 Social Pulse

### A self-contained social-media analytics dashboard generator

**Turn a weekly CSV export into a beautiful, interactive, multi-page web dashboard — with one command.**
No server. No database. No build toolchain. Just one HTML file you can open, email, or host anywhere.

<br>

[!\[Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python\&logoColor=white)](https://www.python.org/)
[!\[pandas](https://img.shields.io/badge/built%20with-pandas-150458?logo=pandas\&logoColor=white)](https://pandas.pydata.org/)
[!\[Single file output](https://img.shields.io/badge/output-single%20HTML%20file-ff7a1a)](#)
[!\[No backend](https://img.shields.io/badge/backend-none-0a9a3f)](#)
[!\[License: MIT](https://img.shields.io/badge/License-MIT-2c93ff.svg)](LICENSE)

<br>

!\[Social Pulse — Overview](docs/screenshot-overview.png)

</div>

\---

## ✨ What it does

**Social Pulse** takes the messy weekly export from a social-media scheduler (VistaSocial, or native
exports from LinkedIn, Instagram, YouTube, TikTok, X/Twitter and Facebook) and a monthly newsletter
export (Kit / ConvertKit), and produces a single, polished `dashboard.html`: a ten-page analytics
report with trends, week-over-week and month-over-month comparisons, per-channel deep-dives, timing
heatmaps, a searchable post table, email performance, and a natural-language **"Ask the data"** box —
all computed in Python and rendered entirely client-side.

It replaced a manual, copy-paste-into-a-spreadsheet routine with a repeatable, **drop-the-CSV-and-rerun**
pipeline that produces something a manager is actually happy to open.

> 🧪 \*\*This repo ships with synthetic sample data\*\* for a fictional brand ("Nimbus") so you can clone it
> and see the full dashboard in seconds — nothing real or confidential is included. Point it at your own
> export to make it yours.

\---

## 🎬 See it in action

<table>
<tr>
<td width="50%">

**Light \& dark, out of the box**
A single theme toggle; every chart, table and heatmap is tuned for both.

!\[Dark mode](docs/screenshot-dark.png)

</td>
<td width="50%">

**"Ask the data" — in plain English**
A fully client-side query engine. Ask *"compare September vs August impressions"* and get the number
instantly. No API key, no server, nothing leaves the page.

!\[Ask the data](docs/screenshot-ask.png)

</td>
</tr>
<tr>
<td width="50%">

**Week-over-week comparison**
Every metric vs the prior period — in **% and absolute** terms — plus the biggest movers.

!\[Weekly comparison](docs/screenshot-weekly.png)

</td>
<td width="50%">

**Per-channel deep-dive**
A leaderboard, a reach-vs-volume head-to-head, paid-vs-organic, and a this-week readout for every channel.

!\[Channels](docs/screenshot-channels.png)

</td>
</tr>
</table>

👉 **Try the sample dashboard yourself:** open [`docs/dashboard.html`](docs/dashboard.html) in any browser
(download the file, or enable GitHub Pages and browse to it).

\---

## 🧭 The ten pages

|Page|What it answers|
|-|-|
|🔎 **Ask the data**|"What was *X* in *month/week* on *platform/channel*?" — typed in plain English, answered instantly|
|🏠 **Overview**|Headline KPIs, weekly trend charts, platform mix, week-scoped key insights + best-post spotlight|
|📅 **Weekly**|Week-over-week comparison (totals, per platform, per channel) + a week-by-week snapshot for anomaly checks|
|🗓️ **Monthly**|Month-over-month comparison, with a graceful note when the latest month is still partial|
|📊 **Platforms**|Impressions and engagement-rate breakdown across all six platforms|
|👥 **Channels**|Leaderboard by engagement rate, reach-vs-volume deep-dive, paid vs organic, per-channel weekly readout|
|#️⃣ **Hashtags**|Frequency and average engagement rate of the top tags|
|⏰ **Timing**|Engagement by daypart and weekday, plus a day × time heatmap|
|📋 **All posts**|Every post, newest first — searchable, filterable, and sortable on any column|
|✉️ **Email · Kit**|Monthly newsletter performance: open/click/unsub rates, best email, highlights, full email table|

\---

## 🚀 Quickstart

```bash
# 1. clone + install (just pandas)
git clone https://github.com/sandeep0608/social-pulse.git
cd social-pulse
python -m venv .venv \&\& source .venv/bin/activate     # optional but recommended
pip install -r requirements.txt

# 2. generate the sample data (synthetic, deterministic)
python make\_sample\_data.py

# 3. build the dashboard
python generate\_dashboard.py \\
    --posts data/sample\_posts.csv \\
    --email "data/sample\_broadcasts.csv:Nimbus Weekly"

# 4. open it
open output/dashboard.html        # macOS   (use `xdg-open` on Linux, `start` on Windows)
```

That's it — `output/dashboard.html` is a complete, standalone file. Email it, drop it on any static host,
or commit it to GitHub Pages.

### Using your own data

```bash
python generate\_dashboard.py --posts path/to/your\_export.csv
```

Add one `--email CSV:"Label"` per newsletter list. With two or more, the Email tab grows a property switcher:

```bash
python generate\_dashboard.py --posts posts.csv \\
    --email main\_list.csv:"Main"  --email academy\_list.csv:"Academy"
```

\---

## 🏗️ How it works

The design goal is **"the output has no dependencies."** All computation happens in Python at build time;
the result is a single HTML file whose interactivity (sorting, filtering, charts, theme, the Ask box) is
plain vanilla JavaScript over data embedded directly in the page.

```
 your\_export.csv ─┐
                  │   ┌─────────────────────────────────────────────┐
 broadcasts.csv ──┼──▶│  generate\_dashboard.py  (the one command)   │
                  │   │                                             │
                  │   │   src/social.py   → the "cube" of aggregates│
                  │   │   src/enrich.py   → week-scoped insights     │
                  │   │   src/email\_report.py → email performance    │
                  │   └───────────────────┬─────────────────────────┘
                  │                        │  embeds JSON into
                  │                        ▼
                  │             templates/dashboard.html
                  │            (self-contained HTML + CSS + JS,
                  │             with \_\_DATA\_\_ / \_\_EMAIL\_\_ slots)
                  │                        │
                  ▼                        ▼
            output/dashboard.html  ◀── one file, opens anywhere
```

Everything is derived from one consistent set of definitions, so the charts, the comparison tables and
the Ask box can never disagree:

```
engagement rate = engagement / impressions × 100
clicks          = clicks + url\_link\_clicks
weeks           = ISO weeks (Mon–Sun)
```

\---

## 📥 Input format

**Posts CSV** (VistaSocial / native export) — the columns used:

`date`, `time`, `network`, `profile`, `message`, `type`, `impressions`, `impressions\_organic`,
`impressions\_paid`, `reach`, `engagement`, `engagement\_organic`, `engagement\_paid`, `likes`, `dislikes`,
`comments`, `shares`, `retweets`, `quotes`, `clicks`, `url\_link\_clicks`, `plays`, `published\_link`.

**Broadcasts CSV** (Kit / ConvertKit export) — the columns used:

`subject`, `date`, `time`, `recipients`, `opened`, `open\_rate`, `clicked`, `click\_rate`,
`click\_to\_open\_rate`, `unsubscribed`, `unsub\_rate`, `url`.

Missing columns are tolerated (they read as zero / "—") and messy rows are skipped rather than crashing
the build. See [`make\_sample\_data.py`](make_sample_data.py) for a complete, generated example of both files.

\---

## ⚙️ Make it yours — one file to edit

Everything about *your* accounts lives in [**`src/config.py`**](src/config.py):

```python
CHANNEL\_MAP = {
    ("LinkedIn",  "Your Brand"):        "linkedin-yourbrand",
    ("Instagram", "Your Brand"):        "instagram-yourbrand",
    # ... one row per (network, profile) pair in your export
}
```

A "channel" is one brand property on one platform. When a new account comes online, add a row — unmapped
profiles show up labelled `<network>-unmapped` (a visible warning, not a crash) so you always notice them.

Branding (colors, fonts) lives in the CSS `:root` block at the top of
[`templates/dashboard.html`](templates/dashboard.html) — swap the brand blue `#2C93FF` and the DM Sans
font for your own and the whole dashboard re-themes.

\---

## 🗂️ Project structure

```
social-pulse/
├── generate\_dashboard.py     # the one command — CSV(s) → dashboard.html
├── make\_sample\_data.py       # generates the synthetic sample CSVs
├── src/
│   ├── config.py             # CHANNEL\_MAP + platform names  ← edit your accounts here
│   ├── social.py             # Posts CSV → aggregate "cube" (weekly/monthly/platform/channel/…)
│   ├── enrich.py             # adds week-scoped insights (spotlight, per-channel readout, key insights)
│   └── email\_report.py       # Kit CSV → monthly email performance
├── templates/
│   └── dashboard.html        # the self-contained HTML shell (\_\_DATA\_\_ / \_\_EMAIL\_\_ placeholders)
├── data/                     # sample CSVs (generated)
├── output/                   # generated dashboard.html
├── docs/                     # screenshots + a prebuilt sample dashboard to browse
├── requirements.txt
└── LICENSE
```

\---

## 🎨 Design notes

* **One file, zero dependencies at view time.** The dashboard embeds its data and runs on vanilla JS —
no framework, no fetch, no CDN required to read it (fonts load from Google Fonts when online, and fall
back to system fonts offline).
* **Accessible, colorblind-aware palette** that holds up in both light and dark themes, with a distinct
hue per platform.
* **Honest numbers.** Reach is only shown where a platform reports it; paid/organic splits are only shown
where available; the newest week is flagged as still-maturing so a fresh dip isn't misread as a decline.
* **Fast.** Thousands of posts render instantly because every aggregate is precomputed; the only runtime
work is sorting/filtering the post table.

\---

## 🧰 Tech stack

**Python** (pandas) for the data pipeline · **vanilla HTML / CSS / JavaScript** for the dashboard (no
framework) · **hand-rolled SVG** charts · **DM Sans** type.

\---

## 📜 License

[MIT](LICENSE) — free to use, adapt, and build on.

<div align="center">
<br>
<sub>Built as a portfolio project. Sample data is synthetic; any resemblance to real accounts is coincidental.</sub>
</div>

