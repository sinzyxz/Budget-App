"""Pure budget logic (no DB) so it is easy to unit test."""
from decimal import ROUND_HALF_UP, Decimal

GROUPS = ("need", "want", "saving", "invest")

DEFAULT_PLANS = {
    "50/30/20": ("จำเป็น 50 / อยากได้ 30 / ออม 20 — สูตรมาตรฐาน",
                 {"need": 50, "want": 30, "saving": 20, "invest": 0}),
    "50/30/10/10": ("จำเป็น 50 / อยากได้ 30 / ออม 10 / ลงทุน 10",
                    {"need": 50, "want": 30, "saving": 10, "invest": 10}),
    "70/20/10": ("ใช้จ่าย 70 (จำเป็น 45 + อยากได้ 25) / ออม 20 / ลงทุน 10",
                 {"need": 45, "want": 25, "saving": 20, "invest": 10}),
    "80/20": ("ใช้จ่าย 80 (จำเป็น 55 + อยากได้ 25) / ออม 20 — เริ่มง่ายที่สุด",
              {"need": 55, "want": 25, "saving": 20, "invest": 0}),
    "Pay Yourself First": ("ออมและลงทุน 40 ก่อน แล้วค่อยใช้ที่เหลือ",
                           {"need": 40, "want": 20, "saving": 30, "invest": 10}),
    "ภาระเยอะ 60/10/20/10": ("จำเป็น 60 (ผ่อน/ค่าครองชีพสูง) / อยากได้ 10 / ออม 20 / ลงทุน 10",
                             {"need": 60, "want": 10, "saving": 20, "invest": 10}),
}


def allocate(base: Decimal, percents: dict[str, int]) -> dict[str, Decimal]:
    """Split base by percents in satang; leftover cents go to largest remainders so the sum is exact."""
    cents = int((Decimal(base) * 100).to_integral_value(ROUND_HALF_UP))
    floors = {g: cents * p // 100 for g, p in percents.items()}
    rema = {g: cents * p % 100 for g, p in percents.items()}
    left = cents - sum(floors.values())
    for g in sorted(rema, key=rema.get, reverse=True)[: max(left, 0)]:
        floors[g] += 1
    return {g: Decimal(v) / 100 for g, v in floors.items()}


def compare(allowed: dict[str, Decimal], spent: dict[str, Decimal]) -> list[dict]:
    rows = []
    for g in GROUPS:
        a, s = allowed.get(g, Decimal(0)), spent.get(g, Decimal(0))
        rows.append({"group": g, "allowed": a, "spent": s, "diff": a - s, "over": s > a})
    return rows


def suggest(spent: dict[str, Decimal], plans: dict[str, dict[str, int]]) -> dict | None:
    """Pick the plan whose shares are closest (L1 distance) to the real spending shares."""
    total = sum(spent.values(), Decimal(0))
    if total <= 0:
        return None
    shares = {g: float(spent.get(g, 0) / total * 100) for g in GROUPS}
    best = min(plans, key=lambda n: sum(abs(shares[g] - plans[n].get(g, 0)) for g in GROUPS))
    return {"plan": best, "distance": round(sum(abs(shares[g] - plans[best].get(g, 0)) for g in GROUPS), 1),
            "shares": {g: round(v, 1) for g, v in shares.items()}}
