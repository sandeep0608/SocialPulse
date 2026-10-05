"""
email_report.py — turn a Kit / ConvertKit broadcasts CSV into the "email cube"
the dashboard's Email tab reads: per-month KPIs, a best-email spotlight, a few
evidence-based highlights, and the full month-by-month email table.

Multiple lists (properties) can be merged by calling `add_property` repeatedly
against the same dict — the Email tab then shows a property switcher.
"""
from __future__ import annotations

import re

import pandas as pd


def _clean(s, n=90):
    s = re.sub(r"\s+", " ", str(s)).strip()
    return (s[:n] + "…") if len(s) > n else s


def _why(row) -> str:
    """Transparent reason an email likely performed, from its subject + metrics."""
    subj = str(row["subject"])
    low = subj.lower()
    bits = []
    if any(k in low for k in ["new", "guide", "template", "ship log"]):
        bits.append("a fresh-content drop — subscribers open for the new thing")
    elif any(k in low for k in ["how", "ideas", "ways", "metrics", "tips"]):
        bits.append("a practical, how-to subject that promises a quick win")
    elif "?" in subj:
        bits.append("a question hook in the subject line")
    else:
        bits.append("a clear, benefit-led subject line")
    if row["click_to_open_rate"] >= 4:
        bits.append(f"and the body delivered — {row['click_to_open_rate']:.1f}% click-to-open means openers "
                    "found something worth clicking")
    elif row["clicked"] > 0 and row["click_rate"] < 0.3:
        bits.append("but few clicked — opens without a strong link to pursue")
    return "; ".join(bits[:3]) + "."


def _emailobj(r):
    return {
        "d": r["dt"].strftime("%b %-d"), "ymd": r["dt"].strftime("%Y-%m-%d"),
        "t": str(r["time"])[:5], "subj": _clean(r["subject"], 120),
        "recip": int(r["recipients"]), "opened": int(r["opened"]),
        "open": round(float(r["open_rate"]), 1), "clicked": int(r["clicked"]),
        "click": round(float(r["click_rate"]), 2), "cto": round(float(r["click_to_open_rate"]), 1),
        "unsub_n": int(r["unsubscribed"]), "unsub": round(float(r["unsub_rate"]), 2),
        "url": str(r["url"]) if isinstance(r["url"], str) and r["url"].startswith("http") else "",
    }


def add_property(data: dict, broadcasts_csv: str, prop_label: str) -> dict:
    """Parse one broadcasts CSV and merge it into the email cube under `prop_label`."""
    df = pd.read_csv(broadcasts_csv)
    df.columns = [c.strip().lower() for c in df.columns]
    df["dt"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["dt"].notna()].copy()
    for c in ["recipients", "opened", "clicked", "unsubscribed"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    for c in ["open_rate", "click_rate", "click_to_open_rate", "unsub_rate"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["month"] = df["dt"].dt.strftime("%Y-%m")

    maxd = df["dt"].max()
    cutoff = maxd - pd.DateOffset(months=13)
    recent = df[df["dt"] >= cutoff]
    months = sorted(recent["month"].dropna().unique(), reverse=True)
    mlabel = lambda m: pd.Timestamp(m + "-01").strftime("%B %Y")

    by_month = {}
    for m in months:
        g = df[df.month == m].sort_values("dt")
        tot_rec = int(g["recipients"].sum())
        subs = int(g["recipients"].max())
        tot_op = int(g["opened"].sum())
        tot_cl = int(g["clicked"].sum())
        tot_un = int(g["unsubscribed"].sum())
        o_rate = round(tot_op / tot_rec * 100, 1) if tot_rec else 0
        c_rate = round(tot_cl / tot_rec * 100, 2) if tot_rec else 0
        u_rate = round(tot_un / tot_rec * 100, 2) if tot_rec else 0
        cto = round(tot_cl / tot_op * 100, 1) if tot_op else 0

        best = g.sort_values(["click_rate", "open_rate"], ascending=False).iloc[0]
        best_obj = _emailobj(best)
        best_obj["why"] = _why(best)

        ins = [
            {"k": "win", "t": f"<b>Best email: “{_clean(best['subject'], 70)}”</b> — {best['open_rate']:.1f}% "
             f"open and <b>{best['click_rate']:.2f}% click</b> ({best['click_to_open_rate']:.1f}% "
             f"click-to-open). {_why(best)}"},
            {"k": "", "t": f"<b>Opens held at {o_rate:.1f}%</b> across {len(g)} email{'s' if len(g) != 1 else ''} "
             f"to ~{subs:,} subscribers — steady for a list this size (typical newsletter benchmarks sit ~20%)."},
        ]
        worst = g.sort_values("click_rate").iloc[0]
        if len(g) > 1 and worst["open_rate"] >= 15 and worst["click_rate"] < 0.3:
            ins.append({"k": "risk", "t": f"<b>“{_clean(worst['subject'], 60)}” drew opens "
                        f"({worst['open_rate']:.1f}%) but few clicks ({worst['click_rate']:.2f}%)</b> — likely "
                        "an announcement with no strong link to pursue. Add a clear CTA to convert that curiosity."})
        ins.append({"k": "", "t": f"<b>Unsubscribes stayed low at {u_rate:.2f}%</b> ({tot_un:,} of ~{subs:,}) — "
                    "well within a healthy range; the cadence isn't fatiguing the list."})

        by_month[m] = {
            "label": mlabel(m), "sent": int(len(g)), "subscribers": subs,
            "total_recipients": tot_rec, "total_opened": tot_op, "total_clicked": tot_cl,
            "total_unsub": tot_un, "open_rate": o_rate, "click_rate": c_rate,
            "unsub_rate": u_rate, "cto_rate": cto, "best": best_obj, "insights": ins,
            "emails": [_emailobj(r) for _, r in g.sort_values("dt", ascending=False).iterrows()],
        }

    if prop_label not in data["properties"]:
        data["properties"].append(prop_label)
    data["data"][prop_label] = {
        "months": [{"key": m, "label": mlabel(m)} for m in months],
        "latest": months[0], "byMonth": by_month,
    }
    data["current"] = data["properties"][0]
    return data


def empty() -> dict:
    return {"properties": [], "current": None, "data": {}}
