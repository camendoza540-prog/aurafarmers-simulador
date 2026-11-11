import { useMemo, useState } from "react";
import { CalendarClock, ChevronDown, FastForward, HandCoins, Landmark, PiggyBank, RefreshCw, Sprout, Wallet } from "lucide-react";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import usePolling from "../hooks/usePolling";
import { Empty, ErrorBox, Loader } from "../components/Feedback";
import Modal from "../components/Modal";
import SavingsCalculator from "../components/SavingsCalculator";
import { dateLong, money, number, pct } from "../utils/format";

const INFLATION = 0.05;
const addDays = (d) => {
  const x = new Date();
  x.setDate(x.getDate() + d);
  return x.toISOString().slice(0, 10);
};

export default function Savings() {
  const toast = useToast();
  const { user, refreshUser } = useAuth();
  const products = usePolling("/savings/products/");
  const { data, error, loading, reload } = usePolling("/savings/accounts/", 15000);
  const [depositing, setDepositing] = useState(null);
  const [showCalc, setShowCalc] = useState(false);

  const act = async (fn, okMsg) => {
    try {
      const res = await fn();
      toast(okMsg || res.data?.detail || "Listo.");
      reload(true);
      refreshUser();
    } catch (e) {
      toast(errorMessage(e), "error");
    }
  };

  const active = data?.accounts.filter((a) => a.status === "active") || [];
  const closed = data?.accounts.filter((a) => a.status === "closed") || [];

  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Ahorro y CDT</h1>
          <p>Haz crecer tu dinero con una tasa fija y sin sustos del mercado. Aquí ves cuánto recibirás y cuándo, antes de decidir.</p>
        </div>
      </div>

      <section className="cdt-how">
        <div className="how-step"><span className="how-ico"><Wallet size={20} /></span><div><strong>1. Depositas</strong><p>Eliges cuánto y por cuánto tiempo. El dinero sale de tu efectivo disponible.</p></div></div>
        <div className="how-step"><span className="how-ico"><Sprout size={20} /></span><div><strong>2. Crece con tasa fija</strong><p>La tasa está pactada desde el inicio: no sube ni baja con el mercado.</p></div></div>
        <div className="how-step"><span className="how-ico"><HandCoins size={20} /></span><div><strong>3. Recibes capital + intereses</strong><p>En un CDT, al vencimiento. En la cuenta de ahorro, cuando quieras.</p></div></div>
      </section>

      {products.data && <CdtSimulator products={products.data} cash={Number(user?.profile?.cash_balance || 0)} onOpened={() => { reload(true); refreshUser(); }} />}

      <section className="panel">
        <div className="panel-head">
          <h2>Mis CDT y cuentas</h2>
          {data && active.length > 0 && (
            <div className="row" style={{ gap: 20, fontSize: 14 }}>
              <span className="muted">Saldo total <strong style={{ color: "var(--ink)" }}>{money(data.summary.value)}</strong></span>
              <span className="muted">Intereses ganados <strong className="gain">{money(data.summary.interest)}</strong></span>
            </div>
          )}
        </div>
        {error && !data && <ErrorBox error={error} onRetry={reload} />}
        {loading && !data ? <Loader /> : active.length === 0 ? (
          <Empty title="Todavía no tienes CDT ni cuentas de ahorro">Usa el simulador de arriba: eliges monto y plazo, y ves exactamente cuánto recibirás.</Empty>
        ) : (
          <div className="cdt-grid">
            {active.map((a) => (
              <AccountCard key={a.id} a={a}
                onAdvance={(d, label) => act(() => api.post(`/savings/accounts/${a.id}/advance/`, { days: d }), `Simulaste ${label} en «${a.name}».`)}
                onWithdraw={() => act(() => api.post(`/savings/accounts/${a.id}/withdraw/`))}
                onRenew={() => act(() => api.post(`/savings/accounts/${a.id}/renew/`))}
                onDeposit={() => setDepositing(a)} />
            ))}
          </div>
        )}
        {closed.length > 0 && (
          <details style={{ marginTop: 16 }}>
            <summary className="muted" style={{ cursor: "pointer", fontSize: 14 }}>Cuentas cerradas ({closed.length})</summary>
            {closed.map((a) => (
              <div key={a.id} className="row between" style={{ padding: "8px 0", borderBottom: "1px solid var(--line-soft)", fontSize: 14 }}>
                <span>{a.name} <span className="muted">· {a.product_label}</span></span>
                <span>{money(a.principal)} → <strong>{money(a.final_value)}</strong> <span className="gain">(+{money(Number(a.final_value) - Number(a.principal))})</span></span>
              </div>
            ))}
          </details>
        )}
      </section>

      <section className="panel">
        <button className="row between btn-reset" style={{ width: "100%" }} onClick={() => setShowCalc(!showCalc)} aria-expanded={showCalc}>
          <div style={{ textAlign: "left" }}>
            <h2>Calculadora avanzada de interés compuesto</h2>
            <p className="muted" style={{ margin: "4px 0 0", fontSize: 14 }}>Con aportes mensuales, tasa nominal o efectiva e inflación.</p>
          </div>
          <ChevronDown size={20} style={{ transform: showCalc ? "rotate(180deg)" : "none", transition: "transform .2s" }} />
        </button>
        {showCalc && <div style={{ marginTop: 18 }}><SavingsCalculator /></div>}
      </section>

      <section className="panel glossary-mini">
        <h2 style={{ marginBottom: 10 }}>Palabras clave</h2>
        <dl>
          <div><dt>Tasa E.A. (efectiva anual)</dt><dd>Cuánto crece tu dinero en un año, ya incluyendo los intereses sobre intereses. Es la forma en que los bancos colombianos anuncian sus tasas.</dd></div>
          <div><dt>CDT</dt><dd>Certificado de Depósito a Término: prestas tu dinero al banco por un plazo fijo y él te paga una tasa mayor que la de una cuenta de ahorro.</dd></div>
          <div><dt>Vencimiento</dt><dd>El día en que termina el plazo del CDT. Antes de esa fecha no puedes retirarlo.</dd></div>
          <div><dt>Renovar</dt><dd>Al vencer, volver a abrir el CDT con el capital más los intereses para seguir ganando interés compuesto.</dd></div>
        </dl>
      </section>

      {depositing && <DepositModal account={depositing} onClose={() => setDepositing(null)} onDone={() => { reload(true); refreshUser(); }} />}
    </div>
  );
}

function CdtSimulator({ products, cash, onOpened }) {
  const toast = useToast();
  const [code, setCode] = useState("CDT180");
  const [amount, setAmount] = useState(5000);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const p = products.find((x) => x.code === code) || products[0];
  const rate = p.rate_ea / 100;
  const days = p.term_days || 365;
  const result = amount * (1 + rate) ** (days / 365);
  const interest = result - amount;
  const savingsRate = (products.find((x) => x.code === "AHORRO")?.rate_ea || 0) / 100;
  const vsSavings = amount * (1 + savingsRate) ** (days / 365);
  const realValue = result / (1 + INFLATION) ** (days / 365);
  const monthly = ((1 + rate) ** (1 / 12) - 1) * 100;
  const max = Math.max(1000, Math.floor(cash));
  const tooMuch = amount > cash;
  const tooLittle = amount < Number(p.min_amount);

  const bars = useMemo(() => {
    const items = [
      { label: p.term_days ? `CDT a ${p.term_days} días` : "Cuenta de ahorro", value: result, color: "var(--pine)" },
      ...(p.code !== "AHORRO" ? [{ label: "Cuenta de ahorro", value: vsSavings, color: "var(--sage)" }] : []),
      { label: "Dejarlo quieto (poder de compra con 5 % de inflación)", value: amount / (1 + INFLATION) ** (days / 365), color: "var(--loss)" },
    ];
    const top = Math.max(...items.map((i) => i.value));
    const bottom = Math.min(...items.map((i) => i.value)) * 0.97;
    return items.map((i) => ({ ...i, w: ((i.value - bottom) / (top - bottom || 1)) * 85 + 15 }));
  }, [p, result, vsSavings, amount, days]);

  const open = async () => {
    setBusy(true);
    try {
      await api.post("/savings/accounts/", { product: p.code, amount, name: name || undefined });
      toast(`${p.name} abierto por ${money(amount)}.`);
      setName("");
      onOpened();
    } catch (e) {
      toast(errorMessage(e), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel cdt-sim">
      <div className="cdt-sim-form">
        <h2>Simula tu CDT</h2>
        <p className="muted" style={{ fontSize: 14, marginTop: 4 }}>Mueve el monto y elige el plazo. El resultado se actualiza al instante.</p>
        <div className="field">
          <div className="row between"><label htmlFor="cdt-amt">¿Cuánto quieres invertir?</label><span className="muted" style={{ fontSize: 12.5 }}>Disponible {money(cash, true)}</span></div>
          <div className="input-group"><span className="prefix">US$</span>
            <input id="cdt-amt" className={`input ${tooMuch ? "invalid" : ""}`} type="number" min="0" step="100" value={amount} onChange={(e) => setAmount(Math.max(0, Number(e.target.value)))} />
          </div>
          <input type="range" min="100" max={max} step="100" value={Math.min(amount, max)} onChange={(e) => setAmount(Number(e.target.value))} aria-label="Monto" />
        </div>
        <span style={{ fontSize: 13, fontWeight: 600, color: "var(--ink-2)" }}>¿Por cuánto tiempo?</span>
        <div className="term-cards">
          {products.map((x) => (
            <button key={x.code} className={`term-card ${code === x.code ? "on" : ""}`} onClick={() => setCode(x.code)}>
              <span className="term-name">{x.term_days ? `${x.term_days} días` : "Sin plazo"}</span>
              <span className="term-rate">{pct(x.rate_ea, false, 1)} E.A.</span>
              <span className="term-kind">{x.term_days ? "CDT" : "Cuenta de ahorro"}</span>
            </button>
          ))}
        </div>
        <div className="field" style={{ marginTop: 14 }}>
          <label htmlFor="cdt-name">Ponle un nombre (opcional)</label>
          <input id="cdt-name" className="input" maxLength={60} value={name} onChange={(e) => setName(e.target.value)} placeholder="Ej.: Matrícula del próximo semestre" />
        </div>
      </div>

      <div className="cdt-sim-result">
        <div className="muted" style={{ fontSize: 14 }}>
          {p.term_days
            ? <>Hoy inviertes <strong style={{ color: "var(--ink)" }}>{money(amount)}</strong> y el <strong style={{ color: "var(--ink)" }}>{dateLong(addDays(days))}</strong> recibes</>
            : <>Si depositas {money(amount)}, en un año tu cuenta tendría</>}
        </div>
        <div className="cdt-big">{money(result)}</div>
        <div className="gain" style={{ fontWeight: 600 }}>+{money(interest)} de intereses</div>

        <div className="cdt-timeline">
          <div className="tl-dot"><span>Hoy</span><strong>{money(amount, true)}</strong></div>
          <div className="tl-line"><span /></div>
          <div className="tl-dot end"><span>{p.term_days ? "Vencimiento" : "En 1 año"}</span><strong>{money(result, true)}</strong></div>
        </div>

        <dl className="cdt-facts">
          <div><dt>Tasa</dt><dd>{pct(p.rate_ea, false, 2)} E.A. ≈ {number(monthly, 3)} % mensual</dd></div>
          <div><dt>Plazo</dt><dd>{p.term_days ? `${p.term_days} días · no se puede retirar antes` : "Sin plazo · retiras cuando quieras"}</dd></div>
          <div><dt>Valor real</dt><dd>{money(realValue)} en dinero de hoy, descontando 5 % de inflación</dd></div>
        </dl>

        <h3 style={{ fontSize: 14, margin: "16px 0 8px" }}>¿Qué tendrías al final con cada opción?</h3>
        <div className="compare-bars">
          {bars.map((b) => (
            <div key={b.label} className="cbar">
              <span className="cbar-label">{b.label}</span>
              <div className="cbar-track"><span style={{ width: `${b.w}%`, background: b.color }} /></div>
              <strong>{money(b.value, true)}</strong>
            </div>
          ))}
        </div>

        {tooMuch && <p className="loss" style={{ fontSize: 13.5 }}>No tienes suficiente efectivo disponible.</p>}
        {tooLittle && !tooMuch && <p className="loss" style={{ fontSize: 13.5 }}>El monto mínimo para {p.name.toLowerCase()} es {money(p.min_amount, true)}.</p>}
        <button className="btn btn-primary btn-block" style={{ marginTop: 12 }} disabled={busy || tooMuch || tooLittle} onClick={open}>
          <Landmark size={16} /> {busy ? "Abriendo…" : `Abrir ${p.term_days ? `CDT a ${p.term_days} días` : "cuenta de ahorro"}`}
        </button>
      </div>
    </section>
  );
}

function AccountCard({ a, onAdvance, onWithdraw, onRenew, onDeposit }) {
  const c = a.current;
  const isCdt = !!a.term_days;
  return (
    <article className={`cdt-card ${c.matured ? "matured" : ""}`}>
      <header className="row between" style={{ alignItems: "flex-start" }}>
        <div>
          <div className="row" style={{ gap: 8 }}>
            {isCdt ? <CalendarClock size={18} color="var(--wheat)" /> : <PiggyBank size={18} color="var(--pine)" />}
            <h3>{a.name}</h3>
          </div>
          <div className="muted" style={{ fontSize: 12.5 }}>{a.product_label} · {pct(a.rate_ea * 100, false, 1)} E.A.</div>
        </div>
        {isCdt && <span className={`tag ${c.matured ? "tag-alcista" : "tag-etf"}`}>{c.matured ? "Listo para cobrar" : `Faltan ${number(c.days_to_maturity, 0)} días`}</span>}
      </header>

      <div className="cdt-card-values">
        <div><span>Invertiste</span><strong>{money(a.principal)}</strong></div>
        <div><span>Hoy vale</span><strong>{money(c.value)}</strong></div>
        <div><span>Ganado</span><strong className="gain">+{money(c.interest)}</strong></div>
      </div>

      {isCdt ? (
        <>
          <div className="furrow" style={{ height: 10, margin: "14px 0 6px" }}>
            <span style={{ width: `${c.progress_pct}%`, background: c.matured ? "var(--gain)" : "var(--wheat)" }} />
          </div>
          <div className="row between muted" style={{ fontSize: 12.5 }}>
            <span>Día {number(Math.min(c.days_elapsed, a.term_days), 0)} de {a.term_days}</span>
            <span>Vence {c.maturity_date ? dateLong(c.maturity_date) : "—"}</span>
          </div>
          <p className="cdt-note">
            {c.matured
              ? <>Tu CDT terminó. Puedes <strong>cobrarlo</strong> (el dinero vuelve a tu efectivo) o <strong>renovarlo</strong> con capital + intereses.</>
              : <>Al vencimiento recibirás <strong>{money(c.value_at_maturity)}</strong>. Gana unos {money(c.daily_interest)} por día.</>}
          </p>
        </>
      ) : (
        <p className="cdt-note">Gana unos {money(c.daily_interest)} por día. Si no retiras, en un año tendría {money(c.value_in_one_year)}.</p>
      )}

      <div className="cdt-actions">
        {!c.matured && (
          <div className="sim-time">
            <span className="muted" style={{ fontSize: 12 }}><FastForward size={13} /> Simular el paso del tiempo</span>
            <div className="row" style={{ gap: 6 }}>
              <button className="chip" onClick={() => onAdvance(30, "1 mes")}>+1 mes</button>
              <button className="chip" onClick={() => onAdvance(90, "3 meses")}>+3 meses</button>
              {isCdt
                ? <button className="chip" onClick={() => onAdvance(Math.ceil(c.days_to_maturity), "hasta el vencimiento")}>Hasta el vencimiento</button>
                : <button className="chip" onClick={() => onAdvance(365, "1 año")}>+1 año</button>}
            </div>
          </div>
        )}
        <div className="row" style={{ gap: 8, justifyContent: "flex-end" }}>
          {!isCdt && <button className="btn btn-secondary btn-sm" onClick={onDeposit}>Aportar</button>}
          {isCdt && c.matured && <button className="btn btn-secondary btn-sm" onClick={onRenew}><RefreshCw size={14} /> Renovar</button>}
          <button className="btn btn-primary btn-sm" disabled={!c.can_withdraw} onClick={onWithdraw}
                  title={c.can_withdraw ? "" : "Un CDT solo se cobra al vencimiento"}>{isCdt ? "Cobrar" : "Retirar todo"}</button>
        </div>
      </div>
    </article>
  );
}

function DepositModal({ account, onClose, onDone }) {
  const toast = useToast();
  const [amount, setAmount] = useState("");
  const [error, setError] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/savings/accounts/${account.id}/deposit/`, { amount });
      toast(`Aportaste ${money(amount)} a «${account.name}».`);
      onDone();
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };
  return (
    <Modal title={`Aportar a ${account.name}`} onClose={onClose}>
      <form onSubmit={submit}>
        <div className="field">
          <label htmlFor="da">Monto</label>
          <div className="input-group"><span className="prefix">US$</span>
            <input id="da" className="input" type="number" min="1" step="any" autoFocus value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
        </div>
        {error && <p className="loss" style={{ fontSize: 14 }}>{error}</p>}
        <button className="btn btn-primary btn-block" disabled={!Number(amount)}>Aportar</button>
      </form>
    </Modal>
  );
}
