"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, getToken, setToken } from "@/lib/api";

type Plan = { id: number; name: string; description: string };
type Cat = { id: number; name: string; group: string };
type Tx = { id: number; type: "income" | "expense"; amount: number; occurred_on: string; note: string; category: string | null };
type Row = { group: string; allowed: number; spent: number; diff: number; over: boolean };
type Report = {
  base: number; income: number; plan: string | null; total_spent: number; rows: Row[];
  suggestion: { plan: string; distance: number; shares: Record<string, number> } | null;
};

const LABEL: Record<string, string> = { need: "จำเป็น", want: "อยากได้", saving: "ออม", invest: "ลงทุน" };
const baht = (n: number) => n.toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const today = () => new Date().toISOString().slice(0, 10);

function Auth({ onDone }: { onDone: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      const r = await api<{ token: string }>(`/auth/${mode}`, { method: "POST", body: JSON.stringify({ email, password }) });
      setToken(r.token);
      onDone();
    } catch (x) { setErr((x as Error).message); }
  }

  return (
    <main className="auth">
      <h1>แบ่งเงินเดือน</h1>
      <p className="muted">ใส่เงินเดือน บันทึกรายจ่าย แล้วดูว่าใช้เกินสูตรที่เลือกตรงไหน</p>
      <form className="panel" onSubmit={submit}>
        <label htmlFor="email">อีเมล</label>
        <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label htmlFor="pw">รหัสผ่าน (อย่างน้อย 8 ตัว)</label>
        <input id="pw" type="password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required />
        {err && <p className="err" role="alert">{err}</p>}
        <button type="submit">{mode === "login" ? "เข้าสู่ระบบ" : "สมัครสมาชิก"}</button>
        <div className="seg">
          <button type="button" className={mode === "login" ? "on" : ""} onClick={() => setMode("login")}>มีบัญชีแล้ว</button>
          <button type="button" className={mode === "register" ? "on" : ""} onClick={() => setMode("register")}>สมัครใหม่</button>
        </div>
      </form>
    </main>
  );
}

function Dashboard({ onLogout }: { onLogout: () => void }) {
  const [month, setMonth] = useState(today().slice(0, 7));
  const [plans, setPlans] = useState<Plan[]>([]);
  const [cats, setCats] = useState<Cat[]>([]);
  const [txs, setTxs] = useState<Tx[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [salary, setSalary] = useState("");
  const [planId, setPlanId] = useState(0);
  const [form, setForm] = useState({ type: "expense", amount: "", category_id: "", occurred_on: today(), note: "" });
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try {
      const [t, r] = await Promise.all([
        api<Tx[]>(`/transactions?month=${month}`),
        api<Report>(`/budget/report?month=${month}`),
      ]);
      setTxs(t); setReport(r);
    } catch (x) { setErr((x as Error).message); }
  }, [month]);

  useEffect(() => {
    (async () => {
      try {
        const [p, c, me] = await Promise.all([
          api<Plan[]>("/plans"), api<Cat[]>("/categories"),
          api<{ salary: number; plan_id: number }>("/me"),
        ]);
        setPlans(p); setCats(c); setSalary(String(me.salary || "")); setPlanId(me.plan_id);
        setForm((f) => ({ ...f, category_id: String(c[0]?.id ?? "") }));
      } catch { onLogout(); }
    })();
  }, [onLogout]);

  useEffect(() => { load(); }, [load]);

  async function saveBudget(e: FormEvent) {
    e.preventDefault(); setErr("");
    try {
      await api("/me/budget", { method: "PUT", body: JSON.stringify({ salary: Number(salary || 0), plan_id: planId }) });
      load();
    } catch (x) { setErr((x as Error).message); }
  }

  async function addTx(e: FormEvent) {
    e.preventDefault(); setErr("");
    try {
      await api("/transactions", {
        method: "POST",
        body: JSON.stringify({
          type: form.type, amount: Number(form.amount), occurred_on: form.occurred_on, note: form.note,
          category_id: form.type === "expense" ? Number(form.category_id) : null,
        }),
      });
      setForm((f) => ({ ...f, amount: "", note: "" }));
      load();
    } catch (x) { setErr((x as Error).message); }
  }

  async function remove(id: number) {
    await api(`/transactions/${id}`, { method: "DELETE" });
    load();
  }

  const chosen = plans.find((p) => p.id === planId);

  return (
    <main>
      <div className="top">
        <h1>แบ่งเงินเดือน</h1>
        <div className="row" style={{ alignItems: "center" }}>
          <input aria-label="เดือน" type="month" value={month} onChange={(e) => setMonth(e.target.value)} style={{ width: 160 }} />
          <button className="ghost" onClick={onLogout}>ออกจากระบบ</button>
        </div>
      </div>
      {err && <p className="err" role="alert">{err}</p>}
      <div className="grid">
        <div>
          <form className="panel" onSubmit={saveBudget}>
            <h2>เงินเดือนและสูตร</h2>
            <label htmlFor="salary">เงินเดือน (บาท)</label>
            <input id="salary" type="number" min="0" step="0.01" value={salary} onChange={(e) => setSalary(e.target.value)} />
            <label htmlFor="plan">สูตรแบ่งเงิน</label>
            <select id="plan" value={planId} onChange={(e) => setPlanId(Number(e.target.value))}>
              {plans.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            {chosen && <p className="muted">{chosen.description}</p>}
            <button type="submit">บันทึกสูตร</button>
          </form>

          <form className="panel" onSubmit={addTx}>
            <h2>เพิ่มรายการ</h2>
            <label htmlFor="type">ประเภท</label>
            <select id="type" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
              <option value="expense">รายจ่าย</option><option value="income">รายรับ</option>
            </select>
            <label htmlFor="amount">จำนวนเงิน</label>
            <input id="amount" type="number" min="0.01" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required />
            {form.type === "expense" && (<>
              <label htmlFor="cat">หมวดหมู่</label>
              <select id="cat" value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })}>
                {cats.map((c) => <option key={c.id} value={c.id}>{c.name} ({LABEL[c.group]})</option>)}
              </select>
            </>)}
            <label htmlFor="date">วันที่</label>
            <input id="date" type="date" value={form.occurred_on} onChange={(e) => setForm({ ...form, occurred_on: e.target.value })} required />
            <label htmlFor="note">บันทึก</label>
            <input id="note" value={form.note} maxLength={200} onChange={(e) => setForm({ ...form, note: e.target.value })} />
            <button type="submit">เพิ่มรายการ</button>
          </form>
        </div>

        <div>
          <section className="panel">
            <h2>เทียบกับสูตร {report?.plan ?? ""}</h2>
            {report && report.base > 0 ? (<>
              <p className="muted">ฐานคำนวณ {baht(report.base)} บาท · ใช้ไปแล้ว {baht(report.total_spent)} บาท</p>
              {report.rows.map((r) => (
                <div key={r.group}>
                  <div className="row">
                    <strong>{LABEL[r.group]}</strong>
                    <span className={r.over ? "bad" : ""}>
                      {baht(r.spent)} / {baht(r.allowed)}{r.over ? ` (เกิน ${baht(-r.diff)})` : ""}
                    </span>
                  </div>
                  <div className={`bar ${r.over ? "over" : ""}`}>
                    <span style={{ width: `${r.allowed > 0 ? Math.min(100, (r.spent / r.allowed) * 100) : r.spent > 0 ? 100 : 0}%` }} />
                  </div>
                </div>
              ))}
            </>) : <p className="muted">ใส่เงินเดือนทางซ้าย หรือบันทึกรายรับของเดือนนี้ เพื่อให้ระบบคำนวณงบแต่ละกลุ่ม</p>}
            {report?.suggestion && (
              <p>พฤติกรรมเดือนนี้ใกล้สูตร <strong>{report.suggestion.plan}</strong> ที่สุด
                {report.suggestion.plan !== report.plan && " ลองเปลี่ยนสูตรดูได้"}</p>
            )}
            <p className="muted">สูตรเป็นแนวทางทั่วไป ไม่ใช่คำแนะนำทางการเงินเฉพาะบุคคล</p>
          </section>

          <section className="panel">
            <h2>รายการเดือนนี้</h2>
            {txs.length === 0 ? <p className="muted">ยังไม่มีรายการ เพิ่มรายการแรกจากฟอร์มทางซ้าย</p> : (
              <table>
                <thead><tr><th>วันที่</th><th>หมวด</th><th>บันทึก</th><th className="num">จำนวน</th><th /></tr></thead>
                <tbody>{txs.map((t) => (
                  <tr key={t.id}>
                    <td>{t.occurred_on}</td><td>{t.category ?? "รายรับ"}</td><td>{t.note}</td>
                    <td className="num">{t.type === "income" ? "+" : "−"}{baht(t.amount)}</td>
                    <td><button className="del" aria-label="ลบรายการ" onClick={() => remove(t.id)}>ลบ</button></td>
                  </tr>
                ))}</tbody>
              </table>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}

export default function Home() {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);
  useEffect(() => { setAuthed(!!getToken()); setReady(true); }, []);
  const logout = useCallback(() => { setToken(null); setAuthed(false); }, []);
  if (!ready) return null;
  return authed ? <Dashboard onLogout={logout} /> : <Auth onDone={() => setAuthed(true)} />;
}
