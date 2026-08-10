#!/usr/bin/env python3
"""
InferenceIndexer.ai - Backfill SIT-Adjusted values for historical price_snapshots.

Recomputes reasoning_multiplier and sit_adjusted_price for all existing rows,
then recalculates sit_score and sit_index_values using the adjusted formula.

Usage:
  python3 backfill_sit_adjusted.py          # Run the backfill
  python3 backfill_sit_adjusted.py --dry-run # Show what would change without writing
"""

import os
import sys
import json
from datetime import date

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed")
    sys.exit(1)

# Import constants from pipeline
sys.path.insert(0, os.path.dirname(__file__))
from pipeline import (
    REASONING_MULTIPLIERS, NON_REASONING_MULTIPLIER,
    get_reasoning_multiplier, calculate_sit_adjusted_price,
    _median, BASE_DATE, BASE_VALUE
)

def get_db_connection():
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        env_path = os.path.expanduser("~/.hermes/.env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("SUPABASE_DB_URL="):
                        db_url = line.split("=", 1)[1]
                        break
    if not db_url:
        print("ERROR: SUPABASE_DB_URL not found")
        sys.exit(1)
    return psycopg2.connect(db_url, connect_timeout=10)


def backfill_snapshots(conn, dry_run=False):
    """Recompute reasoning_multiplier and sit_adjusted_price for all price_snapshots."""
    cur = conn.cursor()
    
    # Get all models with their AA scores and reasoning flags
    cur.execute("SELECT id, tier, aa_index_score, is_reasoning FROM models WHERE is_active = true")
    model_info = {}
    for row in cur.fetchall():
        model_info[row[0]] = {
            "tier": row[1],
            "aa_score": row[2],
            "is_reasoning": row[3] or False,
        }
    print(f"  Loaded {len(model_info)} models from DB")
    
    # Get all price snapshots that need updating
    cur.execute("""
        SELECT id, model_id, blended_price_per_m 
        FROM price_snapshots 
        ORDER BY fetched_at ASC
    """)
    snapshots = cur.fetchall()
    print(f"  Found {len(snapshots)} price snapshots to update")
    
    if dry_run:
        # Show sample of what would change
        updated = 0
        skipped = 0
        for snap_id, model_id, blended in snapshots[:20]:
            info = model_info.get(model_id)
            if not info:
                skipped += 1
                continue
            rm = get_reasoning_multiplier(info["tier"], info["is_reasoning"])
            adj = calculate_sit_adjusted_price(blended, rm, info["aa_score"])
            if updated < 5:
                print(f"    {model_id[:40]:40s} | blended=${blended:.4f} | rm={rm:.1f} | adjusted={adj}")
            updated += 1
        print(f"  ... would update {updated} of first 20 (showing 5)")
        print(f"  ... {skipped} skipped (model not found)")
        return 0, 0
    
    updated = 0
    skipped = 0
    for snap_id, model_id, blended in snapshots:
        info = model_info.get(model_id)
        if not info:
            skipped += 1
            continue
        
        rm = get_reasoning_multiplier(info["tier"], info["is_reasoning"])
        adj = calculate_sit_adjusted_price(blended, rm, info["aa_score"])
        
        cur.execute("""
            UPDATE price_snapshots 
            SET reasoning_multiplier = %s, sit_adjusted_price = %s
            WHERE id = %s
        """, (rm, adj, snap_id))
        updated += 1
        
        if updated % 1000 == 0:
            conn.commit()
            print(f"    ... updated {updated}/{len(snapshots)}")
    
    conn.commit()
    print(f"  Updated {updated} snapshots, skipped {skipped}")
    return updated, skipped


def recalculate_sit_scores(conn, dry_run=False):
    """Recalculate sit_score for all snapshots using adjusted prices.
    
    For each snapshot date, compute tier medians using sit_adjusted_price,
    then set sit_score = adjusted_price / tier_median.
    """
    cur = conn.cursor()
    
    # Get all distinct dates
    cur.execute("SELECT DISTINCT fetched_at::date FROM price_snapshots ORDER BY 1")
    dates = [row[0] for row in cur.fetchall()]
    print(f"  Found {len(dates)} dates to recalculate")
    
    if dry_run:
        print(f"  Would recalculate SIT scores for {len(dates)} dates")
        return
    
    # Get all models with their tiers
    cur.execute("SELECT id, tier FROM models WHERE is_active = true")
    model_tiers = {row[0]: row[1] for row in cur.fetchall()}
    
    for snap_date in dates:
        # Get all snapshots for this date
        cur.execute("""
            SELECT id, model_id, blended_price_per_m, sit_adjusted_price
            FROM price_snapshots
            WHERE fetched_at::date = %s
        """, (snap_date,))
        rows = cur.fetchall()
        
        # Compute tier medians using ONLY adjusted prices (models with AA scores only)
        tier_prices = {}
        for snap_id, model_id, blended, adjusted in rows:
            tier = model_tiers.get(model_id)
            if not tier:
                continue
            if tier not in tier_prices:
                tier_prices[tier] = []
            if adjusted and adjusted > 0:
                tier_prices[tier].append(adjusted)
        
        tier_medians = {}
        for tier, prices in tier_prices.items():
            if prices:
                tier_medians[tier] = _median(prices)
        
        # Update each snapshot's sit_score
        for snap_id, model_id, blended, adjusted in rows:
            tier = model_tiers.get(model_id)
            tier_median = tier_medians.get(tier)
            
            if tier_median and tier_median > 0 and adjusted and adjusted > 0:
                ratio = adjusted / tier_median
                new_score = max(round(ratio * 100), 1)
                cur.execute("""
                    UPDATE price_snapshots SET sit_score = %s WHERE id = %s
                """, (new_score, snap_id))
            else:
                # No AA score = no SIT score
                cur.execute("""
                    UPDATE price_snapshots SET sit_score = NULL WHERE id = %s
                """, (snap_id,))
    
    conn.commit()
    print(f"  Recalculated SIT scores for {len(dates)} dates")


def recalculate_sit_index_values(conn, dry_run=False):
    """Recalculate sit_index_values using adjusted prices.

    For each date, compute median adjusted price per tier and update
    sit_price and sit_index_points.

    !! WARNING (2026-08-10): This recomputes sit_price via equal-weighted
       per-tier median over ALL snapshot models. This does NOT match the live
       pipeline's composite methodology (usage-weighted top-50, quality-gated)
       or the tier median_tier method. Running it blindly overwrites the
       correct sit_index_values history with a different, inconsistent basis,
       producing false %-change readings on the homepage (e.g. a spurious
       153% jump). DO NOT run step 3 unless you specifically intend to rewrite
       the index history. See data_integrity_check.py check #5.
    """
    cur = conn.cursor()
    
    # Get all distinct dates
    cur.execute("SELECT DISTINCT fetched_at::date FROM price_snapshots ORDER BY 1")
    dates = [row[0] for row in cur.fetchall()]
    print(f"  Found {len(dates)} dates for index recalculation")
    
    if dry_run:
        print(f"  Would recalculate {len(dates)} dates of SIT index values")
        return
    
    # Get all models with their tiers
    cur.execute("SELECT id, tier FROM models WHERE is_active = true")
    model_tiers = {row[0]: row[1] for row in cur.fetchall()}
    
    for snap_date in dates:
        # Get all snapshots for this date
        cur.execute("""
            SELECT model_id, blended_price_per_m, sit_adjusted_price
            FROM price_snapshots
            WHERE fetched_at::date = %s
        """, (snap_date,))
        rows = cur.fetchall()
        
        # Compute per-tier medians using blended prices (spot price)
        tier_data = {}
        all_prices = []
        
        for model_id, blended, adjusted in rows:
            tier = model_tiers.get(model_id)
            if not blended or blended <= 0:
                continue
            
            if tier and tier not in tier_data:
                tier_data[tier] = {"prices": [], "providers": set()}
            if tier:
                tier_data[tier]["prices"].append(blended)
            
            all_prices.append(blended)
        
        # Get providers from models
        cur.execute("SELECT DISTINCT provider FROM models WHERE is_active = true")
        all_providers = {row[0] for row in cur.fetchall()}
        
        # Compute and upsert index values
        for tier_name in ["frontier", "standard", "budget", "micro"]:
            td = tier_data.get(tier_name)
            if td and td["prices"]:
                median_price = _median(td["prices"])
                model_count = len(td["prices"])
                provider_count = len(set(
                    model_tiers.get(mid, "unknown") for mid, _, _ in rows
                    if model_tiers.get(mid) == tier_name
                ))
                
                # Get base price for index points
                cur.execute("""
                    SELECT sit_price FROM sit_index_values
                    WHERE tier = %s AND date = %s
                    ORDER BY date ASC LIMIT 1
                """, (tier_name, BASE_DATE))
                base_row = cur.fetchone()
                
                if base_row:
                    base_price = base_row[0]
                    index_points = round((median_price / base_price) * BASE_VALUE, 2) if base_price > 0 else BASE_VALUE
                elif snap_date <= BASE_DATE:
                    index_points = BASE_VALUE
                else:
                    index_points = BASE_VALUE
                
                cur.execute("""
                    INSERT INTO sit_index_values
                        (date, tier, sit_price, sit_index_points, model_count, provider_count, calculation_method)
                    VALUES (%s, %s, %s, %s, %s, %s, 'equal_weight_adjusted')
                    ON CONFLICT (date, tier) DO UPDATE SET
                        sit_price = EXCLUDED.sit_price,
                        sit_index_points = EXCLUDED.sit_index_points,
                        model_count = EXCLUDED.model_count,
                        provider_count = EXCLUDED.provider_count,
                        calculation_method = 'equal_weight_adjusted',
                        calculated_at = NOW()
                """, (snap_date, tier_name, median_price, index_points, model_count, provider_count))
        
        # Composite
        if all_prices:
            composite_median = _median(all_prices)
            cur.execute("""
                SELECT sit_price FROM sit_index_values
                WHERE tier = 'composite' AND date = %s
                ORDER BY date ASC LIMIT 1
            """, (BASE_DATE,))
            base_row = cur.fetchone()
            
            if base_row:
                base_price = base_row[0]
                index_points = round((composite_median / base_price) * BASE_VALUE, 2) if base_price > 0 else BASE_VALUE
            elif snap_date <= BASE_DATE:
                index_points = BASE_VALUE
            else:
                index_points = BASE_VALUE
            
            cur.execute("""
                INSERT INTO sit_index_values
                    (date, tier, sit_price, sit_index_points, model_count, provider_count, calculation_method)
                VALUES (%s, 'composite', %s, %s, %s, %s, 'equal_weight_adjusted')
                ON CONFLICT (date, tier) DO UPDATE SET
                    sit_price = EXCLUDED.sit_price,
                    sit_index_points = EXCLUDED.sit_index_points,
                    model_count = EXCLUDED.model_count,
                    provider_count = EXCLUDED.provider_count,
                    calculation_method = 'equal_weight_adjusted',
                    calculated_at = NOW()
            """, (snap_date, composite_median, index_points, len(all_prices), len(all_providers)))
    
    conn.commit()
    print(f"  Recalculated SIT index values for {len(dates)} dates")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Backfill SIT-Adjusted values")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    args = parser.parse_args()
    
    print("=" * 60)
    print("SIT-ADJUSTED BACKFILL")
    print("=" * 60)
    
    if args.dry_run:
        print("DRY RUN: No changes will be written\n")
    
    conn = get_db_connection()
    try:
        print("\n1. Backfilling reasoning_multiplier and sit_adjusted_price...")
        updated, skipped = backfill_snapshots(conn, dry_run=args.dry_run)
        
        print("\n2. Recalculating SIT scores...")
        recalculate_sit_scores(conn, dry_run=args.dry_run)
        
        print("\n3. Recalculating SIT index values...")
        recalculate_sit_index_values(conn, dry_run=args.dry_run)
        
        if not args.dry_run:
            print("\n✓ Backfill complete!")
        else:
            print("\n✓ Dry run complete (no changes written)")
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Backfill error: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
