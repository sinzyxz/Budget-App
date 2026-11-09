# แบ่งเงินเดือน (Budget Split)

บันทึกรายรับรายจ่าย แล้วเทียบกับสูตรแบ่งเงิน 6 แบบ (50/30/20, 50/30/10/10, 70/20/10, 80/20, Pay Yourself First, ภาระเยอะ)
พร้อมแนะนำว่าพฤติกรรมจริงใกล้สูตรไหนที่สุด

**Stack:** Next.js (TypeScript) · FastAPI · SQLAlchemy · PostgreSQL · Docker · GitHub Actions

```
Next.js :3000  ->  FastAPI :8000  ->  PostgreSQL
```

## รัน
```bash
docker compose up --build
```
เว็บ http://localhost:3000 · API docs http://localhost:8000/docs

## รัน test
```bash
cd backend && pip install -r requirements.txt && pytest
```

## ใช้ Supabase แทน Postgres ในเครื่อง
ตั้ง `DATABASE_URL` ของ backend เป็น connection string ของ Supabase ในรูป `postgresql+psycopg://...`
แล้วลบ service `db` ออกจาก docker-compose

## การตัดสินใจออกแบบ
- เก็บเงินเป็น `NUMERIC(12,2)` และคำนวณด้วย `Decimal` ไม่ใช้ float
- `allocate()` แบ่งเป็นสตางค์ด้วย largest remainder ผลรวมทุกกลุ่มเท่ากับเงินเดือนเป๊ะ
- สูตรเป็นข้อมูลในตาราง `plans` / `plan_items` เพิ่มสูตรใหม่ได้โดยไม่แก้โค้ด
- logic คำนวณอยู่ใน `services.py` เป็น pure function ทดสอบง่าย

## TODO / ต่อยอด
- Alembic migration (ตอนนี้ใช้ `create_all` ตอนเริ่มระบบ)
- เก็บ token ใน httpOnly cookie, rate limit การ login
- สูตรของผู้ใช้เอง, เพิ่ม/แก้หมวดหมู่
- ใช้ LLM จัดหมวดหมู่จากข้อความ เช่น "กาแฟ 65"
- Deploy: Render/Fly.io + Neon/Supabase, เพิ่ม monitoring

> สูตรเป็นแนวทางทั่วไป ไม่ใช่คำแนะนำทางการเงินเฉพาะบุคคล
