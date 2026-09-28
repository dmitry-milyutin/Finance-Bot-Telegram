import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import TZ_NAME, CURRENCY

TZ = ZoneInfo(TZ_NAME)

_AMOUNT_RE = re.compile(r"^\s*([+-]?\d+(?:[.,]\d{1,2})?)\s*$")

def now_local() -> datetime:
    return datetime.now(TZ)

def dt_to_db_str(dt: datetime) -> str:
    # SQLite-friendly, сравнимо строками
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def parse_amount_to_tyiyn(text: str) -> int | None:
    """
    Принимает: "1500", "1500.5", "1500,50"
    Возвращает сумму в тыйынах (1/100 KGS) целым int.
    """
    s = text.replace(" ", "").strip()
    m = _AMOUNT_RE.match(s)
    if not m:
        return None
    val = m.group(1).replace(",", ".")
    try:
        f = float(val)
    except ValueError:
        return None
    f = abs(f)
    return int(round(f * 100))

def fmt_money(tyiyn: int) -> str:
    sign = "-" if tyiyn < 0 else ""
    t = abs(tyiyn)
    whole = t // 100
    frac = t % 100
    if frac == 0:
        return f"{sign}{whole} {CURRENCY}"
    return f"{sign}{whole}.{frac:02d} {CURRENCY}"

def period_range(cmd: str) -> tuple[str, str, str]:
    """
    Возвращает (title, start_db_str, end_db_str) в локальном времени.
    end — НЕвключительно.
    """
    now = now_local()
    if cmd == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        title = f"Сегодня ({start.strftime('%d.%m.%Y')})"
    elif cmd == "week":
        # неделя с понедельника
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        title = f"Неделя ({start.strftime('%d.%m')}–{(end - timedelta(seconds=1)).strftime('%d.%m')})"
    elif cmd == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # следующий месяц
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        title = f"Месяц ({start.strftime('%m.%Y')})"
    elif cmd == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1)
        title = f"Год ({start.strftime('%Y')})"
    else:
        raise ValueError("Unknown period command")

    return title, dt_to_db_str(start), dt_to_db_str(end)