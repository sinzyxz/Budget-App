from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import services
from .db import Base, SessionLocal, engine, get_db
from .models import Category, Plan, PlanItem, Transaction, User
from .security import check_pw, current_user, hash_pw, make_token

DEFAULT_CATEGORIES = [
    ("ค่าที่พัก", "need"), ("ค่าอาหาร", "need"), ("ค่ารถ/เดินทาง", "need"),
    ("ค่าโทรศัพท์/เน็ต", "need"), ("ค่าน้ำ/ไฟ", "need"),
    ("ท่องเที่ยว/บันเทิง", "want"), ("ช้อปปิ้ง", "want"), ("กาแฟ/ของกิน", "want"),
    ("เงินออม", "saving"), ("ลงทุน", "invest"),
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(func.count()).select_from(Plan)):
            for name, (desc, pct) in services.DEFAULT_PLANS.items():
                db.add(Plan(name=name, description=desc,
                            items=[PlanItem(group_name=g, percent=p) for g, p in pct.items()]))
            db.commit()
    yield


app = FastAPI(title="Budget Split API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"],
                   allow_methods=["*"], allow_headers=["*"])


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=72)


class BudgetIn(BaseModel):
    salary: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    plan_id: int


class TxIn(BaseModel):
    type: Literal["income", "expense"]
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    occurred_on: date
    category_id: int | None = None
    note: str = Field("", max_length=200)


def month_range(month: str) -> tuple[date, date]:
    try:
        y, m = map(int, month.split("-"))
        start = date(y, m, 1)
    except ValueError:
        raise HTTPException(422, "month ต้องอยู่ในรูป YYYY-MM")
    return start, date(y + (m == 12), m % 12 + 1, 1)


def tx_out(t: Transaction) -> dict:
    return {"id": t.id, "type": t.type, "amount": float(t.amount), "occurred_on": t.occurred_on,
            "note": t.note, "category": t.category.name if t.category else None,
            "group": t.category.group_name if t.category else None}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register", status_code=201)
def register(body: Credentials, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "อีเมลนี้ถูกใช้แล้ว")
    first_plan = db.scalar(select(Plan).order_by(Plan.id))
    user = User(email=email, password_hash=hash_pw(body.password), plan_id=first_plan.id)
    db.add(user)
    db.flush()
    db.add_all(Category(user_id=user.id, name=n, group_name=g) for n, g in DEFAULT_CATEGORIES)
    db.commit()
    return {"token": make_token(user.id)}


@app.post("/auth/login")
def login(body: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if not user or not check_pw(body.password, user.password_hash):
        raise HTTPException(401, "อีเมลหรือรหัสผ่านไม่ถูกต้อง")
    return {"token": make_token(user.id)}


@app.get("/me")
def me(user: User = Depends(current_user)):
    return {"email": user.email, "salary": float(user.salary), "plan_id": user.plan_id}


@app.put("/me/budget")
def set_budget(body: BudgetIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not db.get(Plan, body.plan_id):
        raise HTTPException(404, "ไม่พบสูตร")
    user.salary, user.plan_id = body.salary, body.plan_id
    db.commit()
    return {"salary": float(user.salary), "plan_id": user.plan_id}


@app.get("/plans")
def plans(db: Session = Depends(get_db)):
    rows = db.scalars(select(Plan).order_by(Plan.id)).all()
    return [{"id": p.id, "name": p.name, "description": p.description,
             "items": [{"group_name": i.group_name, "percent": i.percent} for i in p.items]} for p in rows]


@app.get("/categories")
def categories(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Category).where(Category.user_id == user.id).order_by(Category.id)).all()
    return [{"id": c.id, "name": c.name, "group": c.group_name} for c in rows]


@app.post("/transactions", status_code=201)
def add_tx(body: TxIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.type == "expense":
        cat = db.get(Category, body.category_id) if body.category_id else None
        if not cat or cat.user_id != user.id:
            raise HTTPException(422, "รายจ่ายต้องเลือกหมวดหมู่ของคุณ")
    t = Transaction(user_id=user.id, type=body.type, amount=body.amount, occurred_on=body.occurred_on,
                    category_id=body.category_id if body.type == "expense" else None, note=body.note)
    db.add(t)
    db.commit()
    db.refresh(t)
    return tx_out(t)


@app.get("/transactions")
def list_tx(month: str = Query(..., pattern=r"^\d{4}-\d{2}$"), user: User = Depends(current_user),
            db: Session = Depends(get_db)):
    start, end = month_range(month)
    q = (select(Transaction).where(Transaction.user_id == user.id, Transaction.occurred_on >= start,
                                   Transaction.occurred_on < end)
         .order_by(Transaction.occurred_on.desc(), Transaction.id.desc()))
    return [tx_out(t) for t in db.scalars(q).unique()]


@app.delete("/transactions/{tx_id}", status_code=204)
def delete_tx(tx_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.get(Transaction, tx_id)
    if not t or t.user_id != user.id:
        raise HTTPException(404, "ไม่พบรายการ")
    db.delete(t)
    db.commit()


@app.get("/budget/report")
def report(month: str = Query(..., pattern=r"^\d{4}-\d{2}$"), user: User = Depends(current_user),
           db: Session = Depends(get_db)):
    start, end = month_range(month)
    base_q = select(Transaction).where(Transaction.user_id == user.id, Transaction.occurred_on >= start,
                                       Transaction.occurred_on < end)
    txs = db.scalars(base_q).unique().all()
    income = sum((t.amount for t in txs if t.type == "income"), Decimal(0))
    spent = {g: Decimal(0) for g in services.GROUPS}
    for t in txs:
        if t.type == "expense" and t.category:
            spent[t.category.group_name] += t.amount
    base = user.salary if user.salary > 0 else income
    plan = db.get(Plan, user.plan_id) if user.plan_id else None
    rows, plan_name = [], None
    if plan:
        plan_name = plan.name
        allowed = services.allocate(base, {i.group_name: i.percent for i in plan.items})
        rows = services.compare(allowed, spent)
    all_plans = {p.name: {i.group_name: i.percent for i in p.items} for p in db.scalars(select(Plan)).all()}
    return {
        "base": float(base), "income": float(income), "plan": plan_name,
        "total_spent": float(sum(spent.values(), Decimal(0))),
        "rows": [{**r, "allowed": float(r["allowed"]), "spent": float(r["spent"]), "diff": float(r["diff"])}
                 for r in rows],
        "suggestion": services.suggest(spent, all_plans),
    }
