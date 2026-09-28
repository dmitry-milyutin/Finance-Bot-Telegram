import sqlite3
from typing import Any

from config import DB_PATH
from constants import (
    TX_STATUS_PENDING_TYPE,
    TX_STATUS_PENDING_CATEGORY,
    TX_STATUS_DONE,
    TX_STATUS_CANCELED,
)

def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db() -> None:
    con = _connect()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL,
        message_id INTEGER NOT NULL,
        amount_tyiyn INTEGER NOT NULL,
        tx_type TEXT,
        category TEXT,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_user_created ON transactions(user_id, created_at);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_status ON transactions(user_id, status);")

    con.commit()
    con.close()

def cancel_pending(user_id: int) -> None:
    con = _connect()
    con.execute(
        "UPDATE transactions SET status=? WHERE user_id=? AND status IN (?,?)",
        (TX_STATUS_CANCELED, user_id, TX_STATUS_PENDING_TYPE, TX_STATUS_PENDING_CATEGORY),
    )
    con.commit()
    con.close()

def create_tx(user_id: int, chat_id: int, message_id: int, amount_tyiyn: int, created_at: str) -> int:
    con = _connect()
    cur = con.cursor()
    cur.execute(
        """INSERT INTO transactions(user_id, chat_id, message_id, amount_tyiyn, created_at, status)
           VALUES(?,?,?,?,?,?)""",
        (user_id, chat_id, message_id, amount_tyiyn, created_at, TX_STATUS_PENDING_TYPE),
    )
    con.commit()
    tx_id = cur.lastrowid
    con.close()
    return int(tx_id)

def get_tx(tx_id: int, user_id: int) -> dict[str, Any] | None:
    con = _connect()
    row = con.execute("SELECT * FROM transactions WHERE id=? AND user_id=?", (tx_id, user_id)).fetchone()
    con.close()
    return dict(row) if row else None

def set_type(tx_id: int, user_id: int, tx_type: str) -> None:
    con = _connect()
    con.execute(
        "UPDATE transactions SET tx_type=?, status=? WHERE id=? AND user_id=?",
        (tx_type, TX_STATUS_PENDING_CATEGORY, tx_id, user_id),
    )
    con.commit()
    con.close()

def set_category_done(tx_id: int, user_id: int, category: str) -> None:
    con = _connect()
    con.execute(
        "UPDATE transactions SET category=?, status=? WHERE id=? AND user_id=?",
        (category, TX_STATUS_DONE, tx_id, user_id),
    )
    con.commit()
    con.close()

def cancel_tx(tx_id: int, user_id: int) -> None:
    con = _connect()
    con.execute(
        "UPDATE transactions SET status=? WHERE id=? AND user_id=?",
        (TX_STATUS_CANCELED, tx_id, user_id),
    )
    con.commit()
    con.close()

def fetch_period(user_id: int, start: str, end: str) -> list[sqlite3.Row]:
    con = _connect()
    rows = con.execute(
        """SELECT * FROM transactions
           WHERE user_id=? AND status=? AND created_at>=? AND created_at<? 
           ORDER BY created_at DESC, id DESC""",
        (user_id, TX_STATUS_DONE, start, end),
    ).fetchall()
    con.close()
    return rows

def sum_by_type(user_id: int, start: str, end: str) -> dict[str, int]:
    con = _connect()
    rows = con.execute(
        """SELECT tx_type, COALESCE(SUM(amount_tyiyn),0) AS s
           FROM transactions
           WHERE user_id=? AND status=? AND created_at>=? AND created_at<?
           GROUP BY tx_type""",
        (user_id, TX_STATUS_DONE, start, end),
    ).fetchall()
    con.close()
    out = {"income": 0, "expense": 0}
    for r in rows:
        if r["tx_type"] in out:
            out[r["tx_type"]] = int(r["s"])
    return out

def sum_by_category(user_id: int, start: str, end: str, tx_type: str) -> list[tuple[str, int]]:
    con = _connect()
    rows = con.execute(
        """SELECT category, COALESCE(SUM(amount_tyiyn),0) AS s
           FROM transactions
           WHERE user_id=? AND status=? AND tx_type=? AND created_at>=? AND created_at<?
           GROUP BY category
           ORDER BY s DESC""",
        (user_id, TX_STATUS_DONE, tx_type, start, end),
    ).fetchall()
    con.close()
    return [(str(r["category"]), int(r["s"])) for r in rows]

def monthly_summary(user_id: int, year_start: str, year_end: str) -> list[dict[str, Any]]:
    """
    Отчёт по месяцам текущего года: используем created_at (локальная строка).
    """
    con = _connect()
    rows = con.execute(
        """
        SELECT substr(created_at,1,7) AS ym,
               SUM(CASE WHEN tx_type='income' THEN amount_tyiyn ELSE 0 END) AS income_sum,
               SUM(CASE WHEN tx_type='expense' THEN amount_tyiyn ELSE 0 END) AS expense_sum
        FROM transactions
        WHERE user_id=? AND status=? AND created_at>=? AND created_at<?
        GROUP BY ym
        ORDER BY ym ASC
        """,
        (user_id, TX_STATUS_DONE, year_start, year_end),
    ).fetchall()
    con.close()
    return [
        {"ym": r["ym"], "income": int(r["income_sum"] or 0), "expense": int(r["expense_sum"] or 0)}
        for r in rows
    ]



def sum_total_by_type(user_id: int) -> dict[str, int]:
    """
    Суммы за всё время (только DONE).
    Возвращает {"income": ..., "expense": ...}
    """
    con = _connect()
    rows = con.execute(
        """SELECT tx_type, COALESCE(SUM(amount_tyiyn),0) AS s
           FROM transactions
           WHERE user_id=? AND status=?
           GROUP BY tx_type""",
        (user_id, TX_STATUS_DONE),
    ).fetchall()
    con.close()

    out = {"income": 0, "expense": 0}
    for r in rows:
        if r["tx_type"] in out:
            out[r["tx_type"]] = int(r["s"])
    return out