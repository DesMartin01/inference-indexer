#!/usr/bin/env python3
"""
Generate SIT Monthly Report data from the InferenceIndexer database.

Outputs a populated markdown file with all placeholder values filled in.
Narrative sections are left for Des to write.

Usage:
    .venv/bin/python generate_monthly_report.py --month 2026-08
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

import psycopg2


def get_db_connection():
    """Get DB connection from env file."""
    env_path = os.path.expanduser("~/.hermes/.env")
    db_url = None
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("SUPABASE_DB_URL="):
                db_url = line.split("=", 1)[1].strip().strip('"')
                break
    if not db_url:
        print("ERROR: SUPABASE_DB_URL not found in ~/.hermes/.env")
        sys.exit(1)
    return psycopg2.connect(db_url, connect_timeout=10)


def fmt_price(n):
    """Format price for display."""
    if n is None:
        return "N/A"
    if n < 0.01:
        return f"${n:.4f}"
    return f"${n:.2f}"


def fmt_pct(n):
    """Format percentage with sign."""
    if n is None:
        return "N/A"
    if n >= 0:
        return f"+{n:.1f}%"
    return f"{n:.1f}%"


def get_tier_data(conn, report_date):
    """Get latest and previous month tier data."""
    cur = conn.cursor()

    # Get latest SIT values for all tiers
    cur.execute(
        """
        SELECT tier, sit_price, model_count, provider_count, date
        FROM sit_index_values
        WHERE date = (SELECT MAX(date) FROM sit_index_values)
        ORDER BY CASE WHEN tier = 'composite' THEN 0 ELSE 1 END, tier
    """
    )
    latest = {row[0]: {"price": row[1], "models": row[2], "providers": row[3], "date": row[4]} for row in cur.fetchall()}

    # Get previous month's values (approximately 30 days ago)
    cur.execute(
        """
        SELECT tier, sit_price, model_count, provider_count
        FROM sit_index_values
        WHERE date < (SELECT MAX(date) FROM sit_index_values) - INTERVAL '25 days'
        AND date IN (
            SELECT MAX(date) FROM sit_index_values WHERE date < (SELECT MAX(date) FROM sit_index_values) - INTERVAL '25 days'
        )
        ORDER BY tier
    """
    )
    prev = {row[0]: {"price": row[1], "models": row[2], "providers": row[3]} for row in cur.fetchall()}

    # Get 30-day composite history for trend chart
    cur.execute(
        """
        SELECT date, sit_price
        FROM sit_index_values
        WHERE tier = 'composite'
        ORDER BY date ASC
        LIMIT 30
    """
    )
    history = [(row[0], row[1]) for row in cur.fetchall()]

    # Get tier medians by SIT score
    cur.execute(
        """
        SELECT m.tier,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY lp.sit_score) as median_sit
        FROM latest_prices lp
        JOIN models m ON lp.model_id = m.id
        WHERE lp.sit_score IS NOT NULL
        GROUP BY m.tier
    """
    )
    tier_sit_medians = {row[0]: round(row[1]) if row[1] else None for row in cur.fetchall()}

    cur.close()
    return latest, prev, history, tier_sit_medians


def get_movers(conn):
    """Get biggest price movers over 30 days."""
    cur = conn.cursor()

    # Get current blended prices
    cur.execute(
        """
        SELECT m.id, m.name, m.provider, m.tier, lp.blended_price_per_m, lp.sit_score
        FROM latest_prices lp
        JOIN models m ON lp.model_id = m.id
        WHERE lp.blended_price_per_m > 0
    """
    )
    current = {row[0]: {"name": row[1], "provider": row[2], "tier": row[3], "price": row[4], "sit": row[5]} for row in cur.fetchall()}

    # Get oldest price snapshot in the last 30 days for each model
    cur.execute(
        """
        SELECT ps.model_id, ps.blended_price_per_m
        FROM price_snapshots ps
        WHERE ps.id = (
            SELECT ps2.id FROM price_snapshots ps2
            WHERE ps2.model_id = ps.model_id
            AND ps2.fetched_at >= CURRENT_DATE - INTERVAL '35 days'
            ORDER BY ps2.fetched_at ASC
            LIMIT 1
        )
    """
    )
    old_prices = {row[0]: row[1] for row in cur.fetchall()}

    # Calculate changes
    changes = []
    for model_id, old_price in old_prices.items():
        if model_id in current and old_price and old_price > 0:
            curr = current[model_id]
            change_pct = ((curr["price"] - old_price) / old_price) * 100
            changes.append(
                {
                    "model_id": model_id,
                    "name": curr["name"],
                    "provider": curr["provider"],
                    "tier": curr["tier"],
                    "price": curr["price"],
                    "change_pct": change_pct,
                    "sit": curr["sit"],
                }
            )

    risers = sorted(changes, key=lambda x: x["change_pct"], reverse=True)[:5]
    fallers = sorted(changes, key=lambda x: x["change_pct"])[:5]

    cur.close()
    return risers, fallers


def get_value_leaders(conn):
    """Get best value (lowest SIT) and premium plays (highest SIT) per tier."""
    cur = conn.cursor()

    cur.execute(
        """
        SELECT m.name, m.provider, m.tier, lp.blended_price_per_m,
               lp.sit_score, lp.sit_adjusted_price
        FROM latest_prices lp
        JOIN models m ON lp.model_id = m.id
        WHERE lp.sit_score IS NOT NULL
        ORDER BY m.tier, lp.sit_score ASC
    """
    )

    by_tier = defaultdict(list)
    for row in cur.fetchall():
        by_tier[row[2]].append(
            {
                "name": row[0],
                "provider": row[1],
                "tier": row[2],
                "blended": row[3],
                "sit": int(row[4]),
                "adjusted": row[5],
            }
        )

    cheapest = {}
    most_expensive = {}
    for tier, models in by_tier.items():
        cheapest[tier] = models[0]
        most_expensive[tier] = models[-1]

    cur.close()
    return cheapest, most_expensive


def get_market_structure(conn):
    """Get price spread and provider landscape."""
    cur = conn.cursor()

    # Frontier spread
    cur.execute(
        """
        SELECT m.name, lp.blended_price_per_m
        FROM latest_prices lp
        JOIN models m ON lp.model_id = m.id
        WHERE m.tier = 'frontier' AND lp.blended_price_per_m > 0
        ORDER BY lp.blended_price_per_m ASC
        LIMIT 1
    """
    )
    cheapest_frontier = cur.fetchone()

    cur.execute(
        """
        SELECT m.name, lp.blended_price_per_m
        FROM latest_prices lp
        JOIN models m ON lp.model_id = m.id
        WHERE m.tier = 'frontier' AND lp.blended_price_per_m > 0
        ORDER BY lp.blended_price_per_m DESC
        LIMIT 1
    """
    )
    most_expensive_frontier = cur.fetchone()

    spread_ratio = most_expensive_frontier[1] / cheapest_frontier[1] if cheapest_frontier and most_expensive_frontier else None

    # Top providers by model count
    cur.execute(
        """
        SELECT m.provider, COUNT(*) as model_count,
               AVG(lp.blended_price_per_m) as avg_price,
               STRING_AGG(DISTINCT m.tier, ', ') as tiers
        FROM models m
        JOIN latest_prices lp ON m.id = lp.model_id
        WHERE m.is_active = true AND lp.blended_price_per_m > 0
        GROUP BY m.provider
        ORDER BY model_count DESC
        LIMIT 5
    """
    )
    top_providers = cur.fetchall()

    # New models this month
    cur.execute(
        """
        SELECT m.name, m.provider, m.tier, lp.blended_price_per_m, lp.sit_score
        FROM models m
        JOIN latest_prices lp ON m.id = lp.model_id
        WHERE m.created_at >= CURRENT_DATE - INTERVAL '30 days'
        AND lp.blended_price_per_m > 0
        ORDER BY m.created_at DESC
        LIMIT 5
    """
    )
    new_models = cur.fetchall()

    cur.close()
    return {
        "cheapest_frontier": cheapest_frontier,
        "most_expensive_frontier": most_expensive_frontier,
        "spread_ratio": spread_ratio,
        "top_providers": top_providers,
        "new_models": new_models,
    }


def get_summary_stats(conn):
    """Get overall summary statistics."""
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM models WHERE is_active = true")
    total_models = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT provider) FROM models WHERE is_active = true")
    total_providers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM models WHERE aa_index_score IS NOT NULL AND is_active = true")
    models_with_aa = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM models WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'")
    new_models_count = cur.fetchone()[0]

    cur.close()
    return {
        "total_models": total_models,
        "total_providers": total_providers,
        "models_with_aa": models_with_aa,
        "new_models_count": new_models_count,
    }


def generate_report(month):
    """Generate the populated report."""
    conn = get_db_connection()

    latest, prev, history, tier_sit_medians = get_tier_data(conn, None)
    risers, fallers = get_movers(conn)
    cheapest, most_expensive = get_value_leaders(conn)
    market = get_market_structure(conn)
    stats = get_summary_stats(conn)

    conn.close()

    # Build the report
    now = datetime.now()
    month_name = now.strftime("%B %Y")

    report = f"""# SIT Monthly Report: {month_name}

> Source: InferenceIndexer.ai / SIT | Published: {now.strftime("%Y-%m-%d")} | Data close: {latest.get("composite", {}).get("date", "N/A")}

---

## 1. Executive Summary

The Standard Inference Token (SIT) composite closed at **{fmt_price(latest.get("composite", {}).get("price"))}/M** on {latest.get("composite", {}).get("date", "N/A")}.

**Key numbers at a glance:**

| Metric | This Month | Last Month | Change |
|--------|-----------|------------|--------|
| SIT-Composite | {fmt_price(latest.get("composite", {}).get("price"))}/M | {fmt_price(prev.get("composite", {}).get("price"))}/M | {fmt_pct(((latest.get("composite", {}).get("price", 0) - prev.get("composite", {}).get("price", 0)) / prev.get("composite", {}).get("price", 1)) * 100) if prev.get("composite") else "N/A"} |
| SIT-Frontier | {fmt_price(latest.get("frontier", {}).get("price"))}/M | {fmt_price(prev.get("frontier", {}).get("price"))}/M | {fmt_pct(((latest.get("frontier", {}).get("price", 0) - prev.get("frontier", {}).get("price", 0)) / prev.get("frontier", {}).get("price", 1)) * 100) if prev.get("frontier") else "N/A"} |
| SIT-Standard | {fmt_price(latest.get("standard", {}).get("price"))}/M | {fmt_price(prev.get("standard", {}).get("price"))}/M | {fmt_pct(((latest.get("standard", {}).get("price", 0) - prev.get("standard", {}).get("price", 0)) / prev.get("standard", {}).get("price", 1)) * 100) if prev.get("standard") else "N/A"} |
| SIT-Budget | {fmt_price(latest.get("budget", {}).get("price"))}/M | {fmt_price(prev.get("budget", {}).get("price"))}/M | {fmt_pct(((latest.get("budget", {}).get("price", 0) - prev.get("budget", {}).get("price", 0)) / prev.get("budget", {}).get("price", 1)) * 100) if prev.get("budget") else "N/A"} |
| SIT-Micro | {fmt_price(latest.get("micro", {}).get("price"))}/M | {fmt_price(prev.get("micro", {}).get("price"))}/M | {fmt_pct(((latest.get("micro", {}).get("price", 0) - prev.get("micro", {}).get("price", 0)) / prev.get("micro", {}).get("price", 1)) * 100) if prev.get("micro") else "N/A"} |
| Models tracked | {stats["total_models"]} | - | +{stats["new_models_count"]} |
| Providers | {stats["total_providers"]} | - | - |
| Models with AA scores | {stats["models_with_aa"]} | - | - |

**Three things to know:**

1. [WRITE: Biggest tier move and why]
2. [WRITE: Notable model launch or price cut]
3. [WRITE: Quality-adjusted value shift]

---

## 2. Index Performance & Tier Analysis

**SIT-Composite: {fmt_price(latest.get("composite", {}).get("price"))}/M** ({fmt_pct(((latest.get("composite", {}).get("price", 0) - prev.get("composite", {}).get("price", 0)) / prev.get("composite", {}).get("price", 1)) * 100) if prev.get("composite") else "N/A"} MoM)

[WRITE: 2-3 sentence narrative on what drove the composite this month]

**Tier breakdown:**

| Tier | Price/M | MoM Change | Models | Median SIT Score |
|------|---------|-----------|--------|-----------------|
| Frontier | {fmt_price(latest.get("frontier", {}).get("price"))} | {fmt_pct(((latest.get("frontier", {}).get("price", 0) - prev.get("frontier", {}).get("price", 0)) / prev.get("frontier", {}).get("price", 1)) * 100) if prev.get("frontier") else "N/A"} | {latest.get("frontier", {}).get("models", "N/A")} | {tier_sit_medians.get("frontier", "N/A")} |
| Standard | {fmt_price(latest.get("standard", {}).get("price"))} | {fmt_pct(((latest.get("standard", {}).get("price", 0) - prev.get("standard", {}).get("price", 0)) / prev.get("standard", {}).get("price", 1)) * 100) if prev.get("standard") else "N/A"} | {latest.get("standard", {}).get("models", "N/A")} | {tier_sit_medians.get("standard", "N/A")} |
| Budget | {fmt_price(latest.get("budget", {}).get("price"))} | {fmt_pct(((latest.get("budget", {}).get("price", 0) - prev.get("budget", {}).get("price", 0)) / prev.get("budget", {}).get("price", 1)) * 100) if prev.get("budget") else "N/A"} | {latest.get("budget", {}).get("models", "N/A")} | {tier_sit_medians.get("budget", "N/A")} |
| Micro | {fmt_price(latest.get("micro", {}).get("price"))} | {fmt_pct(((latest.get("micro", {}).get("price", 0) - prev.get("micro", {}).get("price", 0)) / prev.get("micro", {}).get("price", 1)) * 100) if prev.get("micro") else "N/A"} | {latest.get("micro", {}).get("models", "N/A")} | {tier_sit_medians.get("micro", "N/A")} |

[WRITE: One paragraph per tier explaining what moved and why]

---

## 3. Biggest Movers

**Top 5 price increases (30-day, blended $/M):**

| Rank | Model | Provider | Tier | Price/M | Change | SIT Score |
|------|-------|----------|------|---------|--------|-----------|
"""

    for i, m in enumerate(risers, 1):
        report += f"| {i} | {m['name']} | {m['provider']} | {m['tier'].capitalize()} | {fmt_price(m['price'])} | {fmt_pct(m['change_pct'])} | {int(m['sit']) if m['sit'] else 'N/A'} |\n"

    report += """
**Top 5 price decreases (30-day, blended $/M):**

| Rank | Model | Provider | Tier | Price/M | Change | SIT Score |
|------|-------|----------|------|---------|--------|-----------|
"""

    for i, m in enumerate(fallers, 1):
        report += f"| {i} | {m['name']} | {m['provider']} | {m['tier'].capitalize()} | {fmt_price(m['price'])} | {fmt_pct(m['change_pct'])} | {int(m['sit']) if m['sit'] else 'N/A'} |\n"

    report += """
[WRITE: Why did these models move? New launches undercutting incumbents? Promotions? Supply constraints?]

---

## 4. Quality-Adjusted Value Leaders

SIT Score adjusts raw price for reasoning capability and intelligence (AA Index). Score of 100 = tier median. Below 100 = cheaper per unit of intelligence.

**Best value by tier (lowest SIT Score):**

| Tier | Model | Provider | Blended $/M | SIT-Adjusted $/M | SIT Score | vs Median |
|------|-------|----------|-------------|------------------|-----------|-----------|
"""

    for tier in ["frontier", "standard", "budget", "micro"]:
        if tier in cheapest:
            m = cheapest[tier]
            below = 100 - m["sit"] if m["sit"] < 100 else 0
            report += f"| {tier.capitalize()} | {m['name']} | {m['provider']} | {fmt_price(m['blended'])} | {fmt_price(m['adjusted'])} | {m['sit']} | {below}% below |\n"

    report += """
**Premium plays (highest SIT Score):**

| Tier | Model | Provider | Blended $/M | SIT-Adjusted $/M | SIT Score | vs Median |
|------|-------|----------|-------------|------------------|-----------|-----------|
"""

    for tier in ["frontier", "standard", "budget", "micro"]:
        if tier in most_expensive:
            m = most_expensive[tier]
            above = m["sit"] - 100 if m["sit"] > 100 else 0
            report += f"| {tier.capitalize()} | {m['name']} | {m['provider']} | {fmt_price(m['blended'])} | {fmt_price(m['adjusted'])} | {m['sit']} | {above}% above |\n"

    pct_with_aa = round((stats["models_with_aa"] / stats["total_models"]) * 100) if stats["total_models"] > 0 else 0
    report += f"""
**Coverage note:** {stats["models_with_aa"]} of {stats["total_models"]} models ({pct_with_aa}%) have AA Intelligence Index scores and SIT Scores. Models without AA scores are excluded from quality-adjusted analysis but remain in the spot-price index.

[WRITE: What's the value story? Is the gap widening or narrowing? Any new entrant disrupting rankings?]

---

## 5. Price Spread & Market Structure

"""

    spread = market["spread_ratio"]
    cheapest_f = market["cheapest_frontier"]
    most_exp_f = market["most_expensive_frontier"]

    report += f"""**The frontier spread:** {spread:.0f}x

The gap between the cheapest and most expensive frontier model is **{spread:.0f}x** ({cheapest_f[0]} at {fmt_price(cheapest_f[1])}/M vs {most_exp_f[0]} at {fmt_price(most_exp_f[1])}/M).

[WRITE: What does this spread mean? Widening = premium models commanding more. Narrowing = commoditization.]

**Top providers by model count:**

| Provider | Models | Avg Blended $/M | Tiers |
|----------|--------|-----------------|-------|
"""

    for p in market["top_providers"]:
        report += f"| {p[0]} | {p[1]} | {fmt_price(p[2])} | {p[3]} |\n"

    report += """
**New entrants this month:**

| Model | Provider | Tier | Price/M | SIT Score |
|-------|----------|------|---------|-----------|
"""

    for m in market["new_models"]:
        report += f"| {m[0]} | {m[1]} | {m[2].capitalize()} | {fmt_price(m[3])} | {int(m[4]) if m[4] else 'N/A'} |\n"

    report += f"""
[WRITE: Context for new entrants. Why do they matter?]

---

## 6. Methodology & Forward Look

**Methodology summary:**

- **SIT-Composite:** Median blended price per million tokens across all tracked models
- **SIT Score:** Quality-adjusted metric. Formula: `(Blended Price x Reasoning Multiplier) / AA Intelligence Index Score`, scaled to 100 = tier median
- **Reasoning multipliers:** Frontier 4x, Standard 3x, Budget 2.5x, Micro 2x. Non-reasoning: 1.0x
- **Data source:** OpenRouter API ({stats["total_models"]} models, {stats["total_providers"]} providers)
- **Blended price:** 70% input / 30% output weighted
- **Update frequency:** Daily. This report reflects the close on {latest.get("composite", {}).get("date", "N/A")}
- **Full methodology:** inferenceindexer.ai/methodology

**Forward look:**

[WRITE: 3-5 bullets on what to watch next month]

**Citation:**

When citing this report: "InferenceIndexer SIT Monthly Report, {month_name}. Source: inferenceindexer.ai"

**Archive:** inferenceindexer.ai/reports
**Data access:** inferenceindexer.ai/api
"""

    return report


def main():
    parser = argparse.ArgumentParser(description="Generate SIT Monthly Report")
    parser.add_argument("--month", required=True, help="Month in YYYY-MM format")
    parser.add_argument("--output", default=None, help="Output file path")
    args = parser.parse_args()

    report = generate_report(args.month)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        output_dir = os.path.expanduser("~/obsidian-vault/10-Projects/inference-futures-exchange/reports")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"sit-monthly-{args.month}.md")
        with open(output_path, "w") as f:
            f.write(report)
        print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
