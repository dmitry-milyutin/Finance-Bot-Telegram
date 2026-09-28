from constants import TX_TYPE_INCOME, TX_TYPE_EXPENSE
from db import sum_by_type, sum_by_category, monthly_summary, sum_total_by_type
from utils import fmt_money

def build_period_report(user_id: int, title: str, start: str, end: str) -> str:
    sums = sum_by_type(user_id, start, end)
    inc = sums.get("income", 0)
    exp = sums.get("expense", 0)
    net = inc - exp

    lines = [
        f"📊 *{title}*",
        "",
        f"✅ Доход: *{fmt_money(inc)}*",
        f"➖ Расход: *{fmt_money(exp)}*",
        f"🧮 Итог: *{fmt_money(net)}*",
        "",
    ]

    inc_cat = sum_by_category(user_id, start, end, TX_TYPE_INCOME)
    exp_cat = sum_by_category(user_id, start, end, TX_TYPE_EXPENSE)

    if inc_cat:
        lines.append("Доходы по категориям:")
        for cat, s in inc_cat[:10]:
            lines.append(f"  • {cat}: {fmt_money(s)}")
        lines.append("")

    if exp_cat:
        lines.append("Расходы по категориям:")
        for cat, s in exp_cat[:10]:
            lines.append(f"  • {cat}: {fmt_money(s)}")

    return "\n".join(lines).strip()

def build_year_months_report(user_id: int, title: str, start: str, end: str) -> str:
    rows = monthly_summary(user_id, start, end)
    if not rows:
        return f"📊 *{title}*\n\nНет данных."

    total_income = sum(r["income"] for r in rows)
    total_expense = sum(r["expense"] for r in rows)

    lines = [
        f"📅 *{title} — по месяцам*",
        "",
        f"✅ Доход (год): *{fmt_money(total_income)}*",
        f"➖ Расход (год): *{fmt_money(total_expense)}*",
        f"🧮 Итог (год): *{fmt_money(total_income - total_expense)}*",
        "",
        "Месяцы:",
    ]

    for r in rows:
        ym = r["ym"]  # YYYY-MM
        net = r["income"] - r["expense"]
        lines.append(f"• {ym}: +{fmt_money(r['income'])} / -{fmt_money(r['expense'])} / = {fmt_money(net)}")

    return "\n".join(lines)


def build_balance_report(user_id: int) -> str:
    sums = sum_total_by_type(user_id)
    inc = sums.get("income", 0)
    exp = sums.get("expense", 0)
    bal = inc - exp

    return (
        "💰 *Текущий баланс*\n\n"
        f"✅ Всего доходов: *{fmt_money(inc)}*\n"
        f"➖ Всего расходов: *{fmt_money(exp)}*\n"
        f"🏦 Баланс: *{fmt_money(bal)}*"
    )