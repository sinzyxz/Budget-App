from decimal import Decimal
from app.services import DEFAULT_PLANS, allocate, compare, suggest


def test_all_default_plans_sum_to_100():
    for name, (_, pct) in DEFAULT_PLANS.items():
        assert sum(pct.values()) == 100, name


def test_allocate_sum_is_exact_even_with_odd_amounts():
    for salary in ("30000", "12345.67", "0.01", "99999.99"):
        out = allocate(Decimal(salary), {"need": 50, "want": 30, "saving": 10, "invest": 10})
        assert sum(out.values()) == Decimal(salary)


def test_allocate_basic():
    out = allocate(Decimal("30000"), {"need": 50, "want": 30, "saving": 20, "invest": 0})
    assert out == {"need": Decimal(15000), "want": Decimal(9000), "saving": Decimal(6000), "invest": Decimal(0)}


def test_compare_flags_overspend():
    rows = compare({"need": Decimal(15000)}, {"need": Decimal(19000)})
    need = next(r for r in rows if r["group"] == "need")
    assert need["over"] and need["diff"] == Decimal(-4000)


def test_suggest_picks_closest_plan():
    plans = {n: pct for n, (_, pct) in DEFAULT_PLANS.items()}
    spent = {"need": Decimal(50), "want": Decimal(30), "saving": Decimal(10), "invest": Decimal(10)}
    assert suggest(spent, plans)["plan"] == "50/30/10/10"
    assert suggest({}, plans) is None
