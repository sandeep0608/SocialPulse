#!/usr/bin/env python3
"""
make_sample_data.py — generate realistic *synthetic* input data so the project
runs end-to-end with zero real accounts and nothing confidential.

It writes two CSVs that mirror the real exports the dashboard consumes:

  data/sample_posts.csv       a VistaSocial / native-style post export
  data/sample_broadcasts.csv  a Kit / ConvertKit broadcasts export

The data is for a fictional brand, "Nimbus", with two properties ("Nimbus" and
"Nimbus Learn") across six platforms. It is deterministic (seeded), shaped to
look like a real four-month window — weekday seasonality, a quiet summer dip,
and one genuinely viral week on Twitter/X — so every chart, comparison and
insight in the dashboard has something true to say.

    python make_sample_data.py           # writes into ./data
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 20260601
random.seed(SEED)

DATA = Path(__file__).resolve().parent / "data"
DATA.mkdir(exist_ok=True)

START = date(2026, 6, 1)
END = date(2026, 9, 27)

# channel definitions: (network, profile) -> behavioural profile
#   base_impr : typical impressions per post (lognormal-ish center)
#   rate      : typical engagement rate (%) center
#   reach     : does the platform report reach?
#   paidsplit : does it report an organic/paid split?
#   clicks    : does it report link clicks?
#   plays     : does it report video plays?
CHANNELS = {
    ("LinkedIn",  "Nimbus"):       dict(base=3200, rate=1.4, reach=True,  paidsplit=True,  clicks=False, plays=False, weight=11),
    ("LinkedIn",  "Nimbus Learn"): dict(base=900,  rate=4.0, reach=False, paidsplit=True,  clicks=True,  plays=False, weight=8),
    ("Instagram", "Nimbus"):       dict(base=1100, rate=1.0, reach=True,  paidsplit=True,  clicks=False, plays=False, weight=7),
    ("Instagram", "Nimbus Learn"): dict(base=320,  rate=2.6, reach=True,  paidsplit=True,  clicks=False, plays=False, weight=7),
    ("YouTube",   "Nimbus"):       dict(base=640,  rate=2.3, reach=False, paidsplit=False, clicks=False, plays=True,  weight=9),
    ("YouTube",   "Nimbus Learn"): dict(base=380,  rate=1.4, reach=False, paidsplit=False, clicks=False, plays=True,  weight=8),
    ("TikTok",    "Nimbus"):       dict(base=240,  rate=2.7, reach=True,  paidsplit=False, clicks=False, plays=True,  weight=7),
    ("Twitter/X", "Nimbus"):       dict(base=430,  rate=1.9, reach=False, paidsplit=False, clicks=True,  plays=False, weight=20),
    ("Twitter/X", "Nimbus Learn"): dict(base=110,  rate=1.8, reach=False, paidsplit=False, clicks=True,  plays=False, weight=8),
    ("Facebook",  "Nimbus"):       dict(base=300,  rate=0.7, reach=False, paidsplit=False, clicks=False, plays=False, weight=8),
    ("Facebook",  "Nimbus Learn"): dict(base=160,  rate=0.7, reach=False, paidsplit=False, clicks=False, plays=False, weight=8),
}

TYPE_BY_PLATFORM = {
    "LinkedIn":  ["Text", "Link", "Photo", "Video", "Document"],
    "Instagram": ["Reel", "Carousel", "Photo"],
    "YouTube":   ["Video", "Short"],
    "TikTok":    ["Video"],
    "Twitter/X": ["Text", "Link", "Photo", "Video"],
    "Facebook":  ["Link", "Photo", "Video", "Text"],
}

# generic, product-agnostic post templates (no real brands)
TOPICS = [
    "5 patterns for faster data pipelines",
    "How we cut our build times nearly in half",
    "A field guide to clean dashboards",
    "The one chart that changed our roadmap",
    "Why your API needs idempotency keys",
    "Shipping weekly: what six months taught us",
    "From messy CSV to a report in 60 seconds",
    "Reading the numbers: engagement vs reach",
    "New in Nimbus: scheduled exports are live",
    "A tiny trick for readable color palettes",
    "What a good incident review looks like",
    "Caching, explained with a coffee shop",
    "Our favorite open-source tools this quarter",
    "The quiet power of sensible defaults",
    "How to run a useful retro in 25 minutes",
    "Three metrics every content team should track",
    "Behind the scenes of our analytics stack",
    "We rebuilt our onboarding. Here's the data.",
    "Dark mode done right: a short checklist",
    "Turning weekly reviews into a habit",
    "The anatomy of a post that actually lands",
    "Automating the boring parts of reporting",
    "A practical take on week-over-week growth",
    "Small teams, big dashboards: our approach",
]
HASHTAG_POOL = [
    "#analytics", "#data", "#dashboards", "#datascience", "#reporting",
    "#dataviz", "#productivity", "#automation", "#opensource", "#engineering",
    "#marketing", "#socialmedia", "#growth", "#saas", "#devtools",
]


def viral_multiplier(d: date, network: str, profile: str) -> float:
    """One week in September goes viral on Twitter/X for the main brand."""
    viral_week = (date(2026, 9, 7), date(2026, 9, 13))
    if viral_week[0] <= d <= viral_week[1] and network == "Twitter/X" and profile == "Nimbus":
        # a couple of breakout posts; most normal
        return random.choice([1, 1, 1, 1, 60, 140])
    return 1.0


def season(d: date) -> float:
    """Weekday + summer-dip seasonality on posting volume."""
    wd = d.weekday()  # 0=Mon
    base = [1.0, 1.1, 1.0, 1.0, 0.95, 0.4, 0.45][wd]
    # quiet late-June / early-July dip, busier late August onward
    if date(2026, 6, 8) <= d <= date(2026, 7, 6):
        base *= 0.65
    if d >= date(2026, 8, 17):
        base *= 1.25
    return base


def gen_posts():
    rows = []
    pid = 1000
    d = START
    while d <= END:
        for (network, profile), cfg in CHANNELS.items():
            # expected posts for this channel today
            lam = cfg["weight"] / 7.0 * season(d)
            n = 0
            # Poisson-ish via thinning
            while random.random() < lam and n < 6:
                n += 1
                lam *= 0.55
            for _ in range(n):
                pid += 1
                vm = viral_multiplier(d, network, profile)
                impr = max(5, int(random.lognormvariate(0, 0.55) * cfg["base"] * vm))
                rate = max(0.1, random.gauss(cfg["rate"], cfg["rate"] * 0.4))
                if vm > 1:
                    rate = max(0.2, rate * 0.4)  # viral reach dilutes the rate
                eng = int(impr * rate / 100.0)
                # break engagement into components
                likes = int(eng * random.uniform(0.55, 0.78))
                comments = int(eng * random.uniform(0.04, 0.12))
                shares = int(eng * random.uniform(0.05, 0.15))
                retweets = int(eng * random.uniform(0.05, 0.2)) if network == "Twitter/X" else 0
                quotes = int(eng * random.uniform(0.0, 0.05)) if network == "Twitter/X" else 0
                dislikes = int(eng * random.uniform(0.0, 0.03)) if network == "YouTube" else 0
                eng = likes + comments + shares + retweets + quotes  # keep consistent

                reach = int(impr * random.uniform(0.45, 0.85)) if cfg["reach"] else 0
                if cfg["paidsplit"] and random.random() < 0.18:
                    paid = int(impr * random.uniform(0.4, 0.9))
                    organic = impr - paid
                    eng_paid = int(eng * random.uniform(0.3, 0.7))
                    eng_org = eng - eng_paid
                elif cfg["paidsplit"]:
                    organic, paid, eng_org, eng_paid = impr, 0, eng, 0
                else:
                    organic, paid, eng_org, eng_paid = 0, 0, 0, 0  # platform reports total only
                clicks = int(impr * random.uniform(0.002, 0.03)) if cfg["clicks"] else 0
                url_clicks = int(clicks * random.uniform(0.3, 0.8)) if clicks else 0
                plays = int(impr * random.uniform(0.3, 0.7)) if cfg["plays"] else 0

                topic = random.choice(TOPICS)
                tags = " ".join(random.sample(HASHTAG_POOL, random.randint(1, 3)))
                message = f"{topic} {tags}"
                ptype = random.choice(TYPE_BY_PLATFORM[network])
                hh = random.choices([6, 7, 8, 9, 10, 11, 13, 16, 20, 22],
                                    weights=[2, 5, 8, 9, 7, 4, 3, 2, 4, 3])[0]
                mm = random.randint(0, 59)
                rows.append({
                    "date": d.strftime("%B %-d, %Y"),
                    "time": f"{hh:02d}:{mm:02d}",
                    "network": network if network != "Twitter/X" else "Twitter",
                    "profile": profile,
                    "message": message,
                    "type": ptype,
                    "impressions": impr,
                    "impressions_organic": organic,
                    "impressions_paid": paid,
                    "reach": reach,
                    "engagement": eng,
                    "engagement_organic": eng_org,
                    "engagement_paid": eng_paid,
                    "likes": likes,
                    "dislikes": dislikes,
                    "comments": comments,
                    "shares": shares,
                    "retweets": retweets,
                    "quotes": quotes,
                    "clicks": clicks,
                    "url_link_clicks": url_clicks,
                    "plays": plays,
                    "published_link": f"https://nimbus.example/post/{pid}",
                })
        d += timedelta(days=1)
    return rows


SUBJECTS = [
    "This week in Nimbus: 5 ideas for cleaner reports",
    "The dashboard refresh you've been asking for",
    "How teams actually use weekly reviews",
    "New guide: from CSV to shareable report",
    "3 metrics worth your attention this month",
    "What changed in Nimbus this week",
    "A simpler way to track week-over-week growth",
    "Your monthly roundup is here",
    "Behind the build: our analytics stack",
    "Quick win: readable color palettes",
    "The small habit that improved our reporting",
    "Office hours + two new templates",
    "Ship log: scheduled exports, dark mode, and more",
    "Reading the numbers without the noise",
]


def gen_broadcasts():
    """Monthly-ish newsletter sends with realistic open/click/unsub rates."""
    rows = []
    subs = 18000
    d = START
    i = 0
    while d <= END:
        # ~2 sends a week on Tue/Thu
        if d.weekday() in (1, 3):
            subs += random.randint(40, 160)  # steady list growth
            recipients = int(subs * random.uniform(0.97, 1.0))
            open_rate = max(12, random.gauss(32, 5))
            opened = int(recipients * open_rate / 100)
            click_rate = max(0.1, random.gauss(1.4, 0.6))
            clicked = int(recipients * click_rate / 100)
            cto = round(clicked / opened * 100, 1) if opened else 0
            unsub_rate = max(0.02, random.gauss(0.18, 0.08))
            unsub = int(recipients * unsub_rate / 100)
            rows.append({
                "subject": SUBJECTS[i % len(SUBJECTS)],
                "date": d.strftime("%Y-%m-%d"),
                "time": f"{random.choice([8,9,10,14])}:00",
                "recipients": recipients,
                "opened": opened,
                "open_rate": round(open_rate, 1),
                "clicked": clicked,
                "click_rate": round(click_rate, 2),
                "click_to_open_rate": cto,
                "unsubscribed": unsub,
                "unsub_rate": round(unsub_rate, 2),
                "url": f"https://nimbus.example/newsletter/{d.strftime('%Y%m%d')}",
            })
            i += 1
        d += timedelta(days=1)
    return rows


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    posts = gen_posts()
    broadcasts = gen_broadcasts()
    write_csv(DATA / "sample_posts.csv", posts)
    write_csv(DATA / "sample_broadcasts.csv", broadcasts)
    print(f"wrote {len(posts):,} posts     -> {DATA/'sample_posts.csv'}")
    print(f"wrote {len(broadcasts):,} broadcasts -> {DATA/'sample_broadcasts.csv'}")


if __name__ == "__main__":
    main()
