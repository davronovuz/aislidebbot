#!/usr/bin/env python3
"""
One-time migration: SQLite (data/user.db) → PostgreSQL.

Run inside the migrate container:
    docker compose --profile migrate run migrate

Or directly:
    python scripts/migrate_sqlite_to_pg.py

Idempotent: uses INSERT ... ON CONFLICT DO NOTHING for all rows.
"""
import sqlite3
import os
import sys
import logging
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

SQLITE_PATH = os.getenv("SQLITE_PATH", "data/user.db")
PG_URL = os.getenv("DATABASE_URL_SYNC", "postgresql://aislide:aislide@postgres:5432/aislide")


def sqlite_conn():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def pg_conn():
    return psycopg2.connect(PG_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def ts(val) -> str | None:
    """Convert SQLite datetime string to ISO timestamp with timezone."""
    if not val:
        return None
    try:
        dt = datetime.fromisoformat(str(val))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return None


def migrate_users(sl, pg):
    log.info("Migrating users...")
    rows = sl.execute("SELECT * FROM Users").fetchall()
    count = 0
    with pg.cursor() as cur:
        for r in rows:
            cur.execute("""
                INSERT INTO users (telegram_id, username, balance, free_presentations,
                    total_spent, total_deposited, is_active, is_blocked, last_active, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (telegram_id) DO NOTHING
            """, (
                r["telegram_id"], r["username"],
                float(r["balance"] or 0), int(r["free_presentations"] or 1),
                float(r["total_spent"] or 0), float(r["total_deposited"] or 0),
                bool(r["is_active"]), bool(r["is_blocked"]),
                ts(r["last_active"]), ts(r["created_at"]) or datetime.now(timezone.utc).isoformat(),
            ))
            count += 1
    pg.commit()
    log.info(f"  → {count} users")


def migrate_transactions(sl, pg):
    log.info("Migrating transactions...")
    rows = sl.execute("""
        SELECT t.*, u.telegram_id
        FROM Transactions t
        JOIN Users u ON u.id = t.user_id
    """).fetchall()
    count = 0
    with pg.cursor() as cur:
        for r in rows:
            cur.execute("SELECT id FROM users WHERE telegram_id=%s", (r["telegram_id"],))
            user_row = cur.fetchone()
            if not user_row:
                continue
            user_id = user_row["id"]
            cur.execute("""
                INSERT INTO transactions (user_id, transaction_type, amount, balance_before,
                    balance_after, description, receipt_file_id, status, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                user_id, r["transaction_type"], float(r["amount"]),
                float(r.get("balance_before") or 0), float(r.get("balance_after") or 0),
                r["description"], r["receipt_file_id"], r["status"],
                ts(r["created_at"]) or datetime.now(timezone.utc).isoformat(),
            ))
            count += 1
    pg.commit()
    log.info(f"  → {count} transactions")


def migrate_pricing(sl, pg):
    log.info("Migrating pricing...")
    try:
        rows = sl.execute("SELECT * FROM Pricing").fetchall()
    except Exception:
        log.info("  → no Pricing table in SQLite, skipping")
        return
    count = 0
    with pg.cursor() as cur:
        for r in rows:
            cur.execute("""
                INSERT INTO pricing (service_type, price, currency, description, is_active)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (service_type) DO UPDATE SET price=EXCLUDED.price
            """, (
                r["service_type"], float(r["price"]),
                r.get("currency", "so'm"), r.get("description", ""),
                bool(r.get("is_active", True)),
            ))
            count += 1
    pg.commit()
    log.info(f"  → {count} pricing rows")


def migrate_tasks(sl, pg):
    log.info("Migrating presentation_tasks (completed only)...")
    try:
        rows = sl.execute("""
            SELECT pt.*, u.telegram_id
            FROM PresentationTasks pt
            JOIN Users u ON u.id = pt.user_id
            WHERE pt.status = 'completed'
        """).fetchall()
    except Exception:
        log.info("  → no PresentationTasks table in SQLite, skipping")
        return
    count = 0
    with pg.cursor() as cur:
        for r in rows:
            cur.execute("SELECT id FROM users WHERE telegram_id=%s", (r["telegram_id"],))
            user_row = cur.fetchone()
            if not user_row:
                continue
            user_id = user_row["id"]
            cur.execute("""
                INSERT INTO presentation_tasks
                    (task_uuid, user_id, telegram_id, presentation_type, slide_count,
                     answers, status, progress, amount_charged, result_file_id, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (task_uuid) DO NOTHING
            """, (
                r["task_uuid"], user_id, r["telegram_id"],
                r.get("presentation_type", "presentation"), int(r.get("slide_count") or 10),
                r.get("answers"), "completed", 100,
                float(r.get("amount_charged") or 0), r.get("result_file_id"),
                ts(r["created_at"]) or datetime.now(timezone.utc).isoformat(),
            ))
            count += 1
    pg.commit()
    log.info(f"  → {count} tasks migrated")


def migrate_marketplace(sl, pg):
    log.info("Migrating marketplace (Templates + ReadyWorks)...")

    # Templates
    try:
        rows = sl.execute("SELECT * FROM Templates").fetchall()
        count = 0
        with pg.cursor() as cur:
            for r in rows:
                cur.execute("""
                    INSERT INTO templates
                        (name, category, slide_count, price, colors, file_id,
                         preview_file_id, preview_url, is_premium, is_active, downloads, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    r["name"], r.get("category", "general"), int(r.get("slide_count") or 10),
                    float(r.get("price") or 0), r.get("colors", ""),
                    r["file_id"], r.get("preview_file_id"), r.get("preview_url"),
                    bool(r.get("is_premium")), bool(r.get("is_active", True)),
                    int(r.get("downloads") or 0),
                    ts(r.get("created_at")) or datetime.now(timezone.utc).isoformat(),
                ))
                count += 1
        pg.commit()
        log.info(f"  → {count} templates")
    except Exception as e:
        log.info(f"  → Templates: {e}")

    # ReadyWorks
    try:
        rows = sl.execute("SELECT * FROM ReadyWorks").fetchall()
        count = 0
        with pg.cursor() as cur:
            for r in rows:
                cur.execute("""
                    INSERT INTO ready_works
                        (title, subject, work_type, page_count, price, language,
                         description, file_id, preview_file_id, preview_available,
                         is_active, downloads, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    r["title"], r.get("subject", ""), r.get("work_type", "mustaqil_ish"),
                    int(r.get("page_count") or 10), float(r.get("price") or 0),
                    r.get("language", "uz"), r.get("description", ""),
                    r["file_id"], r.get("preview_file_id"),
                    bool(r.get("preview_available")), bool(r.get("is_active", True)),
                    int(r.get("downloads") or 0),
                    ts(r.get("created_at")) or datetime.now(timezone.utc).isoformat(),
                ))
                count += 1
        pg.commit()
        log.info(f"  → {count} ready works")
    except Exception as e:
        log.info(f"  → ReadyWorks: {e}")


def migrate_subscriptions(sl, pg):
    log.info("Migrating subscriptions...")
    try:
        plans = sl.execute("SELECT * FROM SubscriptionPlans").fetchall()
        with pg.cursor() as cur:
            for p in plans:
                cur.execute("""
                    INSERT INTO subscription_plans
                        (plan_name, display_name, price, duration_days,
                         max_presentations, max_courseworks, max_slides, description, is_active)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (plan_name) DO NOTHING
                """, (
                    p["plan_name"], p.get("display_name", p["plan_name"]),
                    float(p.get("price") or 0), int(p.get("duration_days") or 30),
                    int(p.get("max_presentations") or 0), int(p.get("max_courseworks") or 0),
                    int(p.get("max_slides") or 20), p.get("description", ""),
                    bool(p.get("is_active", True)),
                ))
        pg.commit()

        subs = sl.execute("""
            SELECT us.*, u.telegram_id
            FROM UserSubscriptions us
            JOIN Users u ON u.id = us.user_id
            WHERE us.is_active = 1
        """).fetchall()
        with pg.cursor() as cur:
            for s in subs:
                cur.execute("SELECT id FROM users WHERE telegram_id=%s", (s["telegram_id"],))
                user_row = cur.fetchone()
                if not user_row:
                    continue
                cur.execute("SELECT id FROM subscription_plans WHERE plan_name=%s", (s["plan_name"],))
                plan_row = cur.fetchone()
                if not plan_row:
                    continue
                cur.execute("""
                    INSERT INTO user_subscriptions
                        (user_id, plan_id, plan_name, max_presentations, presentations_used,
                         max_courseworks, courseworks_used, max_slides, expires_at, is_active)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (user_id) DO NOTHING
                """, (
                    user_row["id"], plan_row["id"], s["plan_name"],
                    int(s.get("max_presentations") or 0), int(s.get("presentations_used") or 0),
                    int(s.get("max_courseworks") or 0), int(s.get("courseworks_used") or 0),
                    int(s.get("max_slides") or 20), ts(s.get("expires_at")), True,
                ))
        pg.commit()
        log.info(f"  → {len(plans)} plans, {len(subs)} active subscriptions")
    except Exception as e:
        log.info(f"  → Subscriptions: {e}")


def main():
    if not os.path.exists(SQLITE_PATH):
        log.warning(f"SQLite file not found at {SQLITE_PATH} — skipping migration")
        return

    log.info(f"Starting migration: {SQLITE_PATH} → PostgreSQL")
    sl = sqlite_conn()
    pg = pg_conn()

    try:
        migrate_users(sl, pg)
        migrate_transactions(sl, pg)
        migrate_pricing(sl, pg)
        migrate_tasks(sl, pg)
        migrate_marketplace(sl, pg)
        migrate_subscriptions(sl, pg)
        log.info("✅ Migration complete!")
    except Exception as e:
        log.error(f"❌ Migration failed: {e}", exc_info=True)
        pg.rollback()
        sys.exit(1)
    finally:
        sl.close()
        pg.close()


if __name__ == "__main__":
    main()
