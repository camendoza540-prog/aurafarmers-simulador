import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Info } from "lucide-react";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { money, price as fmtPrice, qty as fmtQty } from "../utils/format";

const num = (v) => (v === "" || v === null || v === undefined ? null : Number(v));
const round = (v, d = 2) => Math.round(v * 10 ** d) / 10 ** d;

/**
 * Boleta de órdenes.
 *  · Contado: compra/venta del activo real con comisión de 0,1 %.
 *  · CFD: largo o corto con apalancamiento, margen, spread, TP y SL.
 */
export default function OrderTicket({ quote, account, portfolioId, setPortfolioId, defaults = {}, onExecuted }) {
  const toast = useToast();
  const { refreshUser } = useAuth();
  const cfdOnly = !!quote?.cfd_only;
  const [mode, setMode] = useState(cfdOnly ? "cfd" : defaults.mode || "cfd");
  const [side, setSide] = useState(defaults.side || "BUY");
  const [unit, setUnit] = useState("usd");
  const [value, setValue] = useState("");
  const [leverage, setLeverage] = useState(1);
  const [useTp, setUseTp] = useState(false);
  const [useSl, setUseSl] = useState(false);
  const [tp, setTp] = useState("");
  const [sl, setSl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const pf = account?.portfolios?.find((p) => String(p.id) === String(portfolioId));
  const maxLev = quote?.max_leverage || 5;
  const levOptions = (account?.leverage_options || [1, 2, 3, 5, 10, 20]);
  const isBuy = side === "BUY";
  const dir = isBuy ? 1 : -1;
  const mid = Number(quote?.current_price || 0);
  const bid = Number(quote?.bid || mid);
  const ask = Number(quote?.ask || mid);
  const holding = pf?.holdings?.[quote?.symbol];
  const owned = holding ? Number(holding.quantity) : 0;

  useEffect(() => { if (leverage > maxLev) setLeverage(1); }, [maxLev, leverage]);
  useEffect(() => { if (cfdOnly && mode !== "cfd") setMode("cfd"); }, [cfdOnly, mode]);
  const ccy = quote?.quote_currency || "USD";
  // Factor de conversión a USD: 1 si cotiza en USD; 1/precio si la base es el dólar (USDJPY, USDCOP…)
  const fxAt = (p) => (ccy === "USD" || !p ? 1 : 1 / p);
  useEffect(() => { setError(""); }, [mode, side, value, leverage, tp, sl, portfolioId]);
  // TP/SL dependen de la dirección: al cambiar de modo o de lado se reinician para no quedar del lado equivocado
  useEffect(() => { setUseTp(false); setUseSl(false); setTp(""); setSl(""); }, [mode, side]);

  const calc = useMemo(() => {
    const v = num(value) || 0;
    const rate = account?.commission_rate ?? 0.001;
    const minFee = account?.min_commission ?? 1;
    if (mode === "spot") {
      const p = mid;
      let units = unit === "usd" ? (isBuy ? Math.max((v - Math.max(v * rate, minFee)) / p, 0) : v / p) : v;
      const gross = units * p;
      const fee = gross > 0 ? Math.max(gross * rate, minFee) : 0;
      return { entry: p, units, gross, fee, total: isBuy ? gross + fee : gross - fee, margin: null };
    }
    const entry = isBuy ? ask : bid;
    const fx = fxAt(entry);
    let units, notional, margin;
    if (unit === "usd") {
      margin = v;
      notional = v * leverage;
      units = entry ? notional / (entry * fx) : 0;
    } else {
      units = v;
      notional = v * entry * fx;
      margin = notional / leverage;
    }
    return {
      entry, units, notional, margin,
      spreadCost: units * (ask - bid) * fx,
      liquidation: entry * (1 - dir * 0.5 / leverage),
      perPct: notional / 100,
    };
  }, [value, unit, mode, isBuy, mid, bid, ask, leverage, dir, account, ccy]); // eslint-disable-line react-hooks/exhaustive-deps

  const tpN = useTp ? num(tp) : null;
  const slN = useSl ? num(sl) : null;
  const pnlAt = (level) => (level ? (level - calc.entry) * calc.units * (mode === "spot" ? 1 : dir) * fxAt(level) : null);

  const cash = Number(pf?.cash || 0);
  const m = pf?.margin;
  const available = mode === "cfd" && m && Number(m.margin_used) > 0 ? Math.min(cash, Number(m.free_margin)) : cash;
  let problem = "";
  if (!pf) problem = "Selecciona un portafolio.";
  else if (mode === "spot" && isBuy && calc.total > cash + 0.005) problem = `Efectivo insuficiente en el portafolio (${money(cash)}).`;
  else if (mode === "spot" && !isBuy && calc.units > owned + 1e-6) problem = owned ? `Solo tienes ${fmtQty(owned)} unidades.` : `No tienes ${quote?.symbol} de contado en este portafolio. Para ganar con caídas usa CFD en corto.`;
  else if (mode === "cfd" && calc.margin > available + 0.005) problem = `Margen insuficiente: disponible ${money(available)}.`;
  else if (mode === "cfd" && calc.margin > 0 && calc.margin < 1) problem = "El margen mínimo es US$ 1.";
  const protSide = mode === "spot" ? 1 : dir;
  if (!problem && tpN !== null && (protSide > 0 ? tpN <= mid : tpN >= mid)) problem = `El take profit debe estar ${protSide > 0 ? "por encima" : "por debajo"} del precio actual.`;
  if (!problem && slN !== null && (protSide > 0 ? slN >= mid : slN <= mid)) problem = `El stop loss debe estar ${protSide > 0 ? "por debajo" : "por encima"} del precio actual.`;

  const quick = (kind, pctv) => {
    const sign = kind === "tp" ? protSide : -protSide;
    const level = round(mid * (1 + (sign * pctv) / 100), mid < 10 ? 4 : 2);
    if (kind === "tp") { setUseTp(true); setTp(String(level)); } else { setUseSl(true); setSl(String(level)); }
  };

  const submit = async () => {
    if (!num(value)) { setError("Escribe un monto o una cantidad."); return; }
    setBusy(true);
    setError("");
    try {
      let label;
      if (mode === "spot") {
        const body = { symbol: quote.symbol, side, ...(unit === "usd" ? { amount: Number(value).toFixed(2) } : { quantity: value }) };
        if (isBuy && tpN) body.take_profit = tpN;
        if (isBuy && slN) body.stop_loss = slN;
        const { data } = await api.post(`/portfolios/${pf.id}/trade/`, body);
        label = `${isBuy ? "Compraste" : "Vendiste"} ${fmtQty(data.quantity)} ${quote.symbol} a ${fmtPrice(data.price)}`;
      } else {
        const body = {
          symbol: quote.symbol, side: isBuy ? "LONG" : "SHORT", leverage,
          ...(unit === "usd" ? { margin_amount: Number(value).toFixed(2) } : { quantity: value }),
          take_profit: tpN, stop_loss: slN,
        };
        const { data } = await api.post(`/portfolios/${pf.id}/positions/`, body);
        label = `Posición abierta: ${isBuy ? "compra" : "venta en corto"} de ${fmtQty(data.quantity)} ${quote.symbol} 1:${data.leverage} a ${fmtPrice(data.entry_price, ccy)}`;
      }
      toast(label);
      setValue("");
      refreshUser();
      onExecuted?.();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  if (account && account.portfolios.length === 0) {
    return (
      <aside className="ticket">
        <h3>Abrir operación</h3>
        <p className="muted" style={{ fontSize: 14 }}>Las operaciones se registran dentro de un portafolio con su propio efectivo.</p>
        <Link className="btn btn-primary btn-block" to="/portafolios?nuevo=1">Crear mi primer portafolio</Link>
      </aside>
    );
  }

  return (
    <aside className="ticket" aria-label="Boleta de órdenes">
      <div className="segmented ticket-mode">
        <button className={mode === "cfd" ? "on" : ""} onClick={() => setMode("cfd")}>CFD con margen</button>
        <button className={mode === "spot" ? "on" : ""} onClick={() => setMode("spot")} disabled={cfdOnly}
                title={cfdOnly ? "Este activo solo se opera como CFD" : ""}>Contado</button>
      </div>
      {cfdOnly && <p className="risk-note info" style={{ marginTop: 10 }}><Info size={14} /> {quote?.type_label}: se opera solo como CFD. Ganas si aciertas la dirección, sin comprar el activo.</p>}

      <div className="field" style={{ marginTop: 12 }}>
        <label htmlFor="tk-pf">Portafolio</label>
        <select id="tk-pf" className="input" value={portfolioId || ""} onChange={(e) => setPortfolioId(e.target.value)}>
          {account?.portfolios.map((p) => <option key={p.id} value={p.id}>{p.name} — {money(p.cash)}</option>)}
        </select>
      </div>

      <div className="sides">
        <button className={`side side-sell ${!isBuy ? "on" : ""}`} onClick={() => setSide("SELL")}>
          <span>{mode === "cfd" ? "Vender (corto)" : "Vender"}</span>
          <strong>{fmtPrice(mode === "cfd" ? bid : mid, ccy)}</strong>
        </button>
        <button className={`side side-buy ${isBuy ? "on" : ""}`} onClick={() => setSide("BUY")}>
          <span>{mode === "cfd" ? "Comprar (largo)" : "Comprar"}</span>
          <strong>{fmtPrice(mode === "cfd" ? ask : mid, ccy)}</strong>
        </button>
      </div>
      {mode === "cfd" && <div className="spread-note">Spread {fmtPrice(ask - bid, ccy)} · {((quote?.spread_pct || 0) * 100).toFixed(2).replace(".", ",")} %{quote?.type === "FOREX" && " · 1 lote = 100.000 unidades"}</div>}

      <div className="field">
        <div className="row between">
          <label htmlFor="tk-v">{mode === "cfd" ? (unit === "usd" ? "Margen a invertir" : "Unidades") : unit === "usd" ? "Monto" : "Unidades"}</label>
          <div className="segmented mini">
            <button className={unit === "usd" ? "on" : ""} onClick={() => { setUnit("usd"); setValue(""); }}>US$</button>
            <button className={unit === "qty" ? "on" : ""} onClick={() => { setUnit("qty"); setValue(""); }}>Unid.</button>
          </div>
        </div>
        <div className="input-group">
          {unit === "usd" && <span className="prefix">US$</span>}
          <input id="tk-v" className="input" type="number" min="0" step="any" inputMode="decimal" value={value}
                 onChange={(e) => setValue(e.target.value)} placeholder={unit === "usd" ? "1000" : "5"} />
        </div>
        <div className="row" style={{ gap: 6 }}>
          {mode === "spot" && !isBuy && owned > 0
            ? [0.5, 1].map((f) => <button key={f} className="chip" onClick={() => { setUnit("qty"); setValue(String(+(owned * f).toFixed(6))); }}>{f === 1 ? "Todo" : "50 %"}</button>)
            : [0.1, 0.25, 0.5].map((f) => <button key={f} className="chip" onClick={() => { setUnit("usd"); setValue((available * f).toFixed(2)); }}>{f * 100} %</button>)}
        </div>
      </div>

      {mode === "cfd" && (
        <div className="field">
          <label>Apalancamiento <span className="muted" style={{ fontWeight: 400 }}>(máx. 1:{maxLev} para este activo)</span></label>
          <div className="lev">
            {levOptions.map((l) => (
              <button key={l} className={`chip ${leverage === l ? "on" : ""}`} disabled={l > maxLev} onClick={() => setLeverage(l)}
                      title={l > maxLev ? "Supera el límite ESMA para esta clase de activo" : ""}>1:{l}</button>
            ))}
          </div>
        </div>
      )}

      {(mode === "cfd" || isBuy) && (
        <div className="protect">
          <ProtRow label="Take profit" color="gain" on={useTp} setOn={setUseTp} value={tp} setValue={setTp}
                   pnl={tpN && calc.units ? pnlAt(tpN) : null} onQuick={(p) => quick("tp", p)} />
          <ProtRow label="Stop loss" color="loss" on={useSl} setOn={setUseSl} value={sl} setValue={setSl}
                   pnl={slN && calc.units ? pnlAt(slN) : null} onQuick={(p) => quick("sl", p)} />
        </div>
      )}

      <dl className="ticket-sum">
        <div><dt>Precio de ejecución</dt><dd>{fmtPrice(calc.entry, ccy)}</dd></div>
        <div><dt>Unidades</dt><dd>{fmtQty(calc.units)}</dd></div>
        {mode === "cfd" ? (
          <>
            <div><dt>Valor nocional</dt><dd>{money(calc.notional)}</dd></div>
            <div><dt>Margen requerido</dt><dd><strong>{money(calc.margin)}</strong></dd></div>
            <div><dt>Costo del spread</dt><dd>{money(calc.spreadCost)}</dd></div>
            <div><dt>Cada 1 % de movimiento</dt><dd>{money(calc.perPct)}</dd></div>
            {calc.units > 0 && <div><dt>Cierre forzoso aprox.</dt><dd>{fmtPrice(calc.liquidation, ccy)}</dd></div>}
          </>
        ) : (
          <>
            <div><dt>Comisión (0,1 %, mín. US$ 1)</dt><dd>{money(calc.fee)}</dd></div>
            <div><dt>{isBuy ? "Total a pagar" : "Recibirás"}</dt><dd><strong>{money(calc.total)}</strong></dd></div>
            {!isBuy && <div><dt>Tienes</dt><dd>{fmtQty(owned)} unid.</dd></div>}
          </>
        )}
        <div><dt>{mode === "cfd" ? "Margen disponible" : "Efectivo del portafolio"}</dt><dd>{money(available)}</dd></div>
      </dl>

      {mode === "cfd" && leverage > 1 && (
        <p className="risk-note"><AlertTriangle size={14} /> Con 1:{leverage}, un movimiento de 1 % en contra equivale a perder {leverage} % de tu margen.</p>
      )}
      {mode === "spot" && !isBuy && <p className="risk-note info"><Info size={14} /> En contado solo vendes lo que tienes. Para apostar a la baja usa CFD en corto.</p>}
      {(problem && num(value)) || error ? <p className="loss" style={{ fontSize: 13.5, margin: "8px 0" }}>{error || problem}</p> : null}

      <button className={`btn btn-block ${isBuy ? "btn-buy" : "btn-sell"}`} disabled={busy || !num(value) || !!problem} onClick={submit}>
        {busy ? "Enviando orden…" : `${isBuy ? (mode === "cfd" ? "Abrir compra" : "Comprar") : mode === "cfd" ? "Abrir venta en corto" : "Vender"} ${quote?.symbol || ""}`}
      </button>
      <p className="muted" style={{ fontSize: 11.5, margin: "8px 0 0" }}>Operación simulada con dinero ficticio. Se ejecuta al precio del momento.</p>
    </aside>
  );
}

function ProtRow({ label, color, on, setOn, value, setValue, pnl, onQuick }) {
  return (
    <div className={`prot ${on ? "on" : ""}`}>
      <label className="row" style={{ gap: 8, cursor: "pointer" }}>
        <input type="checkbox" checked={on} onChange={(e) => setOn(e.target.checked)} />
        <span className={`prot-label ${color}`}>{label}</span>
        {on && pnl !== null && <span className={`prot-pnl ${pnl >= 0 ? "gain" : "loss"}`}>{pnl >= 0 ? "+" : "−"}{money(Math.abs(pnl))}</span>}
      </label>
      {on && (
        <>
          <input className="input" type="number" step="any" min="0" value={value} onChange={(e) => setValue(e.target.value)} placeholder="Precio" />
          <div className="row" style={{ gap: 4 }}>
            {[1, 2, 5].map((p) => <button key={p} className="chip chip-xs" onClick={() => onQuick(p)}>{p} %</button>)}
          </div>
        </>
      )}
      {!on && (
        <div className="row" style={{ gap: 4 }}>
          {[1, 2, 5].map((p) => <button key={p} className="chip chip-xs" onClick={() => onQuick(p)}>{p} %</button>)}
        </div>
      )}
    </div>
  );
}
