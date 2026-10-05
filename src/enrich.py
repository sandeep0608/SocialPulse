"""
enrich.py — add the *narrative* layer to the social cube: the week-scoped key
insights, the best-post spotlight, the top-rate leaderboard and a per-channel
readout, each with a plain-English "why" that reads the numbers for the viewer.

Everything here is scoped to the **latest ISO week** in the data, because that
is the week a weekly report is actually about. The "why" strings are transparent
heuristics over the post's own metrics (format, paid push, share ratio, topic) —
no model, no guesswork hidden from the reader.
"""
from __future__ import annotations

from datetime import timedelta

import pandas as pd

from .social import load


def _week_bounds(dt):
    monday = dt - timedelta(days=dt.weekday())
    return monday, monday + timedelta(days=6)


def _why(row, overall_rate) -> str:
    """A transparent, metric-driven reason a post performed as it did."""
    bits = []
    t = str(row["type"]).lower()
    if t in ("video", "reel", "short"):
        bits.append("a video-first format, which this audience rewards")
    elif t in ("carousel", "document"):
        bits.append("a carousel/document — high dwell-time formats")
    elif t == "link":
        bits.append("a link post built to drive clicks")
    rate = row["engagement"] / row["impressions"] * 100 if row["impressions"] else 0
    if rate >= overall_rate * 1.6:
        bits.append(f"engagement ran well above the account average ({rate:.1f}% vs {overall_rate:.1f}%)")
    if row.get("impressions_paid", 0) > 0:
        bits.append("a paid push extended its reach")
    shares = row.get("shares", 0) + row.get("retweets", 0) + row.get("quotes", 0)
    if row["engagement"] and shares / max(row["engagement"], 1) > 0.18:
        bits.append("a high share ratio suggests it resonated enough to pass along")
    tag = str(row["message"]).lower()
    if any(k in tag for k in ["new in", "launch", "live", "introducing"]):
        bits.append("an announcement hook drove curiosity")
    if not bits:
        bits.append("steady fundamentals — on-topic subject, clean format")
    return "; ".join(bits[:3]) + "."


def _diagnostic(name, week_rate, win_rate, posts, overall_rate) -> str:
    if posts == 0:
        return "No posts this week — nothing published on this channel in the window."
    gap = week_rate - overall_rate
    if posts >= 8 and week_rate < overall_rate * 0.6:
        return (f"High volume ({posts} posts) at a thin {week_rate:.1f}% rate — a cadence-vs-quality "
                "question worth a look.")
    if week_rate >= overall_rate * 1.4:
        return f"Punching above its weight — {week_rate:.1f}% beats the {overall_rate:.1f}% account average this week."
    if gap >= 0:
        return f"Holding steady, a touch above the {overall_rate:.1f}% account average."
    return f"Slightly below the {overall_rate:.1f}% account average — room to tighten the hook or format."


def enrich(cube: dict, posts_csv: str) -> dict:
    df = load(posts_csv)
    overall_rate = cube["overall"]["rate"]

    latest_week = cube["meta"]["latest_week"]
    prev_week = cube["meta"]["prev_week"]
    wk = df[df.week == latest_week].copy()
    pw = df[df.week == prev_week].copy()

    if len(wk):
        lo, hi = _week_bounds(wk["dt"].min())
        wnum = latest_week.split("-W")[1]
        wlabel = lo.strftime("%b %-d")
        cube["insight_scope"] = {
            "label": f"W{wnum} · {wlabel}",
            "range": f"{lo.strftime('%b %-d')}–{hi.strftime('%b %-d')}",
        }
    else:
        cube["insight_scope"] = {"label": latest_week, "range": ""}

    wk["rate"] = wk["engagement"] / wk["impressions"].replace(0, pd.NA) * 100

    # ---- spotlight: best post of the week by engagement ----
    if len(wk):
        s = wk.sort_values("engagement", ascending=False).iloc[0]
        cube["spotlight"] = {
            "plat": s["platform"], "chan": s["channel"], "type": s["type"],
            "date": s["dt"].strftime("%b %-d"), "txt": str(s["message"])[:220],
            "impr": int(s["impressions"]), "paid": int(s["impressions_paid"]),
            "eng": int(s["engagement"]),
            "er": round(s["engagement"] / s["impressions"] * 100, 1) if s["impressions"] else 0,
            "likes": int(s["likes"]), "comments": int(s["comments"]), "shares": int(s["shares"]),
            "why": _why(s, overall_rate),
            "note": "Newest-week engagement is still maturing." if latest_week == cube["meta"]["weeks"][-1] else "",
        }
    else:
        cube["spotlight"] = {"plat": "", "chan": "", "type": "", "date": "", "txt": "No posts this week.",
                             "impr": 0, "paid": 0, "eng": 0, "er": 0, "likes": 0, "comments": 0,
                             "shares": 0, "why": "", "note": ""}

    # ---- top rate leaderboard (week, min impressions floor) ----
    cand = wk[wk["impressions"] >= 50].sort_values("rate", ascending=False)
    top_rate = []
    for _, p in cand.head(5).iterrows():
        top_rate.append({
            "er": round(float(p["rate"]), 1), "txt": str(p["message"])[:200],
            "plat": p["platform"], "chan": p["channel"], "type": p["type"],
            "impr": int(p["impressions"]), "paid": int(p["impressions_paid"]),
            "eng": int(p["engagement"]), "why": _why(p, overall_rate),
        })
    cube["top_rate"] = top_rate

    # ---- per-channel readout (this week) ----
    channel_insights = []
    for c in cube["meta"]["channels"]:
        g = wk[wk.channel == c]
        im = int(g["impressions"].sum())
        en = int(g["engagement"].sum())
        ck = int(g["clicks_total"].sum())
        rate = round(en / im * 100, 1) if im else 0
        ctr = round(ck / im * 100, 1) if im else 0
        paid = int(g["impressions_paid"].sum())
        best = None
        if len(g):
            b = g.sort_values("engagement", ascending=False).iloc[0]
            best = {
                "er": round(b["engagement"] / b["impressions"] * 100, 1) if b["impressions"] else 0,
                "impr": int(b["impressions"]), "paid": int(b["impressions_paid"]),
                "txt": str(b["message"])[:160], "eng": int(b["engagement"]),
                "likes": int(b["likes"]), "comments": int(b["comments"]), "shares": int(b["shares"]),
                "type": b["type"], "date": b["dt"].strftime("%b %-d"), "why": _why(b, overall_rate),
            }
        channel_insights.append({
            "name": c, "platform": cube["meta"]["chan_platform"][c],
            "posts": int(len(g)), "impressions": im, "engagement": en,
            "rate": rate, "ctr": ctr, "paid": paid, "best": best,
            "diagnostic": _diagnostic(c, rate, rate, len(g), overall_rate),
        })
    cube["channel_insights"] = channel_insights

    # ---- derived key insights (week-scoped) ----
    ins = []
    wk_ch = [ci for ci in channel_insights if ci["posts"] > 0]
    if wk_ch:
        strong = max(wk_ch, key=lambda c: c["rate"])
        big = max(wk_ch, key=lambda c: c["impressions"])
        wk_impr = sum(c["impressions"] for c in wk_ch) or 1
        share = round(big["impressions"] / wk_impr * 100)
        ins.append({"k": "win", "t": f"<b>{strong['name']} led on engagement this week</b> — "
                    f"{strong['rate']:.1f}% across {strong['posts']} post(s). This is where the audience "
                    "responded most strongly."})
        ins.append({"k": "", "t": f"<b>One channel carried reach:</b> {big['name']} generated {share}% of "
                    f"the week's impressions ({big['impressions']:,}) at a {big['rate']:.1f}% rate — the "
                    "volume engine, distinct from the highest-efficiency channel."})
    # rate direction vs prior week
    def _r(g):
        im = g["impressions"].sum()
        return g["engagement"].sum() / im * 100 if im else 0
    now_r, prev_r = _r(wk), _r(pw)
    if len(pw):
        up = now_r >= prev_r
        ins.append({"k": "win" if up else "risk",
                    "t": f"<b>Engagement rate {'rose' if up else 'slipped'} to {now_r:.1f}%</b> this week "
                    f"(from {prev_r:.1f}% last week){'' if up else ' — worth watching if it continues.'}"})
    weak = [c for c in wk_ch if c["posts"] >= 3]
    if weak:
        w = min(weak, key=lambda c: c["rate"])
        ins.append({"k": "risk", "t": f"<b>{w['name']} is the week's weak link:</b> {w['posts']} posts at "
                    f"just {w['rate']:.1f}% — high effort, low return. A candidate to rethink or repurpose."})
    # timing edge (from full-window timing, still useful context)
    bestday = max((d for d in cube["dow"] if d["posts"] >= 10), key=lambda d: d["rate"], default=None)
    bestdp = max((d for d in cube["daypart"] if d["posts"] >= 10), key=lambda d: d["rate"], default=None)
    if bestday and bestdp:
        ins.append({"k": "", "t": f"<b>Timing edge:</b> {bestday['t']} and the {bestdp['t']} window carry the "
                    f"strongest engagement rates ({bestday['rate']:.1f}% / {bestdp['rate']:.1f}%). Worth "
                    "concentrating priority posts there."})
    cube["insights2"] = ins
    return cube
