"""
social.py — turn a VistaSocial / native Posts CSV into the "social cube": the
nested dictionary of pre-computed aggregates the dashboard reads.

Everything the dashboard shows is derived here with one consistent set of
definitions, so the charts, the comparison tables and the "Ask the data" box can
never disagree with each other:

    engagement rate = engagement / impressions * 100
    clicks          = clicks + url_link_clicks
    weeks           = ISO weeks (Mon-Sun)

The output is intentionally plain JSON-able data (dicts, lists, numbers) so it
can be embedded straight into the HTML template.
"""
from __future__ import annotations

import re
from datetime import timedelta

import pandas as pd

from .config import normalise_platform, channel_for, PLATFORMS

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
HASHTAG_RX = re.compile(r"#\w+")


def _num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)


def _agg(df: pd.DataFrame) -> dict:
    """Aggregate a slice of posts into the standard metric bundle."""
    impr = int(df["impressions"].sum())
    eng = int(df["engagement"].sum())
    reach = int(df["reach"].sum())
    clicks = int(df["clicks_total"].sum())
    return {
        "posts": int(len(df)),
        "impressions": impr,
        "reach": reach,
        "engagement": eng,
        "clicks": clicks,
        "rate": round(eng / impr * 100, 2) if impr else 0.0,
        "ctr": round(clicks / impr * 100, 2) if impr else 0.0,
    }


def _iso_week(dt) -> str:
    y, w, _ = dt.isocalendar()
    return f"{y}-W{int(w):02d}"


def _week_monday(dt):
    return dt - timedelta(days=dt.weekday())


DAYPARTS = [
    ("12am–4am", 0, 4), ("4am–8am", 4, 8), ("8am–12pm", 8, 12),
    ("12pm–4pm", 12, 16), ("4pm–8pm", 16, 20), ("8pm–12am", 20, 24),
]
DAYPART_SHORT = ["12–4a", "4–8a", "8–12p", "12–4p", "4–8p", "8–12a"]
DOW = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DOW_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def load(posts_csv: str) -> pd.DataFrame:
    """Read + normalise the posts export into a tidy dataframe."""
    df = pd.read_csv(posts_csv)
    df.columns = [c.strip().lower() for c in df.columns]

    df["dt"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["dt"].notna()].copy()

    df["platform"] = df["network"].map(normalise_platform)
    df["channel"] = [channel_for(p, pr) for p, pr in zip(df["platform"], df["profile"])]

    for col in ["impressions", "impressions_organic", "impressions_paid", "reach",
                "engagement", "engagement_organic", "engagement_paid", "likes",
                "dislikes", "comments", "shares", "retweets", "quotes",
                "clicks", "url_link_clicks", "plays"]:
        df[col] = _num(df[col]) if col in df.columns else 0

    df["clicks_total"] = df["clicks"] + df["url_link_clicks"]
    df["week"] = df["dt"].apply(_iso_week)
    df["month"] = df["dt"].dt.strftime("%Y-%m")
    df["hour"] = pd.to_datetime(df["time"], errors="coerce", format="mixed").dt.hour.fillna(9).astype(int)
    df["dow"] = df["dt"].dt.weekday
    df = df.sort_values("dt").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# cube
# ---------------------------------------------------------------------------
def build(posts_csv: str) -> dict:
    df = load(posts_csv)

    platforms_present = [p for p in PLATFORMS if p in set(df["platform"])]
    channels_present = sorted(df["channel"].unique())
    chan_platform = {c: df[df.channel == c]["platform"].iloc[0] for c in channels_present}

    weeks = sorted(df["week"].unique())
    months = sorted(df["month"].unique())

    # ---- weekly / monthly ----
    weekly = []
    for wk in weeks:
        g = df[df.week == wk]
        monday = _week_monday(g["dt"].min())
        a = _agg(g)
        a.update(week=wk, label=monday.strftime("%b %-d"))
        weekly.append(a)

    monthly = []
    for m in months:
        g = df[df.month == m]
        a = _agg(g)
        a.update(month=m, label=pd.Timestamp(m + "-01").strftime("%B %Y"))
        monthly.append(a)

    # ---- platform / channel full-window ----
    platforms_full = []
    for p in platforms_present:
        a = _agg(df[df.platform == p])
        a["name"] = p
        platforms_full.append(a)

    channels_full = []
    for c in channels_present:
        a = _agg(df[df.channel == c])
        a["name"] = c
        a["platform"] = chan_platform[c]
        channels_full.append(a)

    # ---- hashtags ----
    tag_rows = []
    for msg, rate in zip(df["message"].fillna(""), df["engagement"] / df["impressions"].replace(0, pd.NA) * 100):
        for t in HASHTAG_RX.findall(str(msg).lower()):
            tag_rows.append((t, rate))
    tdf = pd.DataFrame(tag_rows, columns=["t", "r"]) if tag_rows else pd.DataFrame(columns=["t", "r"])
    hashtags = []
    if len(tdf):
        grp = tdf.groupby("t").agg(u=("t", "size"), r=("r", "mean")).reset_index()
        grp = grp.sort_values("u", ascending=False)
        for _, row in grp.head(15).iterrows():
            hashtags.append({"t": row["t"], "u": int(row["u"]), "r": round(float(row["r"] or 0), 2)})
    n_hashtags = int(tdf["t"].nunique()) if len(tdf) else 0

    # ---- timing ----
    def _rate(g):
        im = g["impressions"].sum()
        return round(g["engagement"].sum() / im * 100, 2) if im else 0.0

    daypart = []
    for label, lo, hi in DAYPARTS:
        g = df[(df.hour >= lo) & (df.hour < hi)]
        daypart.append({"t": label, "posts": int(len(g)), "rate": _rate(g)})

    dow = []
    for i, name in enumerate(DOW):
        g = df[df.dow == i]
        dow.append({"t": name, "posts": int(len(g)), "rate": _rate(g)})

    heat_data = []
    for i in range(7):
        row = []
        for _, lo, hi in DAYPARTS:
            g = df[(df.dow == i) & (df.hour >= lo) & (df.hour < hi)]
            row.append(_rate(g) if len(g) else None)
        heat_data.append(row)
    heat = {"rows": DOW_SHORT, "cols": DAYPART_SHORT, "data": heat_data}

    # ---- paid vs organic (platforms that report a split) ----
    split = df[(df["impressions_organic"] + df["impressions_paid"]) > 0]
    paid_df = split[split["impressions_paid"] > 0]
    org_df = split[split["impressions_paid"] == 0]

    def _paidblock(g):
        im = int(g["impressions"].sum())
        return {
            "posts": int(len(g)),
            "impr_per_post": int(im / len(g)) if len(g) else 0,
            "rate": round(g["engagement"].sum() / im * 100, 2) if im else 0.0,
            "reach": int(g["reach"].sum()),
        }
    paid = {"Paid": _paidblock(paid_df), "Organic": _paidblock(org_df)}

    # ---- week-over-week / month-over-month comparison cubes ----
    def _compare(dim_col, now_key, prev_key, key_field):
        def slice_agg(mask):
            return _agg(df[mask])
        totals = {"now": slice_agg(df[key_field] == now_key),
                  "prev": slice_agg(df[key_field] == prev_key)}
        plats = []
        for p in platforms_present:
            plats.append({"name": p,
                          "now": slice_agg((df.platform == p) & (df[key_field] == now_key)),
                          "prev": slice_agg((df.platform == p) & (df[key_field] == prev_key))})
        chans = []
        for c in channels_present:
            chans.append({"name": c, "platform": chan_platform[c],
                          "now": slice_agg((df.channel == c) & (df[key_field] == now_key)),
                          "prev": slice_agg((df.channel == c) & (df[key_field] == prev_key))})
        return totals, plats, chans

    wow = {}
    if len(weeks) >= 2:
        now_w, prev_w = weeks[-1], weeks[-2]
        t, pl, ch = _compare("week", now_w, prev_w, "week")
        nl = next(w["label"] for w in weekly if w["week"] == now_w)
        pll = next(w["label"] for w in weekly if w["week"] == prev_w)
        wow = {"now": now_w, "prev": prev_w, "now_label": nl, "prev_label": pll,
               "totals": t, "platforms": pl, "channels": ch}

    # month-over-month; if the latest month is barely started, compare the last
    # two *complete* months instead (and say so).
    mom = {}
    if len(months) >= 2:
        now_m, prev_m = months[-1], months[-2]
        last_day = df[df.month == now_m]["dt"].max()
        days_elapsed = last_day.day
        import calendar
        in_month = calendar.monthrange(last_day.year, last_day.month)[1]
        partial = days_elapsed < in_month
        note = ""
        if partial and days_elapsed / in_month < 0.5 and len(months) >= 3:
            now_m, prev_m = months[-2], months[-1 - 2]
            partial = False
        t, pl, ch = _compare("month", now_m, prev_m, "month")
        nl = pd.Timestamp(now_m + "-01").strftime("%B %Y")
        pll = pd.Timestamp(prev_m + "-01").strftime("%B %Y")
        if partial:
            note = (f"{nl} is partial (through {last_day.strftime('%b %-d')}); totals run "
                    f"below a full {pll}, though rates stay comparable.")
        mom = {"now": now_m, "prev": prev_m, "now_label": nl, "prev_label": pll,
               "partial": partial, "note": note, "totals": t, "platforms": pl, "channels": ch}

    # ---- posts table (all posts, newest first) ----
    def _name(msg):
        s = re.sub(r"\s+", " ", str(msg or "")).strip()
        if not s or s.lower() == "nan":
            return "(no text — media only)"
        return s[:140]

    posts_table = []
    for _, r in df.sort_values("dt", ascending=False).iterrows():
        im = int(r["impressions"])
        en = int(r["engagement"])
        posts_table.append({
            "d": r["dt"].strftime("%b %-d"),
            "ymd": r["dt"].strftime("%Y-%m-%d"),
            "t": str(r["time"])[:5],
            "nm": _name(r["message"]),
            "ln": str(r["published_link"]) if isinstance(r["published_link"], str) and str(r["published_link"]).startswith("http") else "",
            "pr": str(r["profile"]),
            "pl": r["platform"],
            "im": im,
            "io": int(r["impressions_organic"]),
            "ip": int(r["impressions_paid"]),
            "er": round(en / im * 100, 1) if im else 0,
            "li": int(r["likes"]),
            "di": int(r["dislikes"]),
            "co": int(r["comments"]),
            "sh": int(r["shares"]),
            "rt": int(r["retweets"]),
            "qu": int(r["quotes"]),
            "en": en,
            "eo": int(r["engagement_organic"]),
            "ep": int(r["engagement_paid"]),
            "ck": int(r["clicks_total"]),
            "pv": int(r["plays"]),
        })

    # channel lookup for the "Ask the data" box: "Platform|Profile" -> channel key
    chan_lookup = {}
    for p, pr, c in zip(df["platform"], df["profile"], df["channel"]):
        chan_lookup[f"{p}|{pr}"] = c

    meta = {
        "date_min": df["dt"].min().strftime("%b %-d, %Y"),
        "date_max": df["dt"].max().strftime("%b %-d, %Y"),
        "n_posts": int(len(df)),
        "n_channels": len(channels_present),
        "n_platforms": len(platforms_present),
        "weeks": weeks,
        "latest_week": weeks[-1],
        "prev_week": weeks[-2] if len(weeks) >= 2 else weeks[-1],
        "months": months,
        "latest_month": months[-1],
        "prev_month": months[-2] if len(months) >= 2 else months[-1],
        "latest_month_label": monthly[-1]["label"],
        "prev_month_label": monthly[-2]["label"] if len(monthly) >= 2 else monthly[-1]["label"],
        "month_partial": bool(mom.get("partial", False)),
        "platforms": platforms_present,
        "channels": channels_present,
        "chan_platform": chan_platform,
        "chan_lookup": chan_lookup,
    }

    return {
        "meta": meta,
        "overall": _agg(df),
        "weekly": weekly,
        "monthly": monthly,
        "platforms_full": platforms_full,
        "channels_full": channels_full,
        "hashtags": hashtags,
        "n_hashtags": n_hashtags,
        "daypart": daypart,
        "dow": dow,
        "heat": heat,
        "paid": paid,
        "wow": wow,
        "mom": mom,
        "posts_table": posts_table,
    }
