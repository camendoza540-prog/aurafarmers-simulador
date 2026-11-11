import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  Area, AreaChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { AlertTriangle, ArrowLeft, CheckCircle2, Info, Pencil, Sprout } from "lucide-react";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import usePolling from "../hooks/usePolling";
import ChartTooltip from "../components/ChartTooltip";
import { Delta, Empty, ErrorBox, Loader, Metric, TypeTag } from "../components/Feedback";
import Modal from "../components/Modal";
import { OpenPositionsTable } from "../components/PositionsTable";
import ProtectionModal from "../components/ProtectionModal";
import { axisMoney, dateLong, dateShort, dateTime, money, number, pct, price, qty, signed, tone } from "../utils/format";
import PortfolioForm from "./PortfolioForm";

const PALETTE = ["#1e5a43", "#d99a1e", "#3c7aa6", "#b5603f", "#6f8a3c", "#7a4d7e", "#9db8a6", "#14261e", "#c7b07a", "#5e7066"];
const INSIGHT_ICON = { warning: AlertTriangle, success: CheckCircle2, info: Info };

export default function PortfolioDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { refreshUser } = useAuth();
  const { data: p, error, loading, reload } = usePolling(`/portfolios/${id}/`, 10000);
  const [range, setRange] = useState("1A");
  const perf = usePolling(`/portfolios/${id}/performance/?range=${range}`, 30000);
  const txs = usePolling(`/portfolios/${id}/transactions/`, 0);
  const [view, setView] = useState("backtest");
  const [alloc, setAlloc] = useState("asset");
  const [protect, setProtect] = useState(null);
  const [cashModal, setCashModal] = useState(null);
  const [editing, setEditing] = useState(false);
  const [closing, setClosing] = useState(false);

  const refreshAll = () => { reload(true); perf.reload(true); txs.reload(true); refreshUser(); };

  if (loading && !p) return <Loader />;
  if (error && !p) return <ErrorBox error={error} onRetry={reload} />;

  const allocData = alloc === "asset"
    ? [...p.holdings.map((h) => ({ name: h.symbol, value: Number(h.market_value) })), ...(Number(p.cash) > 0 ? [{ name: "Efectivo", value: Number(p.cash) }] : [])]
    : (alloc === "sector" ? p.allocation.by_sector : p.allocation.by_asset_class).map((x) => ({ name: x.name, value: Number(x.value) }));
  const allocTotal = allocData.reduce((a, b) => a + b.value, 0) || 1;
  const r = p.risk;
  const bt = perf.data?.backtest;
  const snaps = (perf.data?.snapshots || []).map((s) => ({ ...s, ts: new Date(s.t).getTime() }));

  return (
    <div className="stack">
      <Link to="/portafolios" className="btn btn-ghost btn-sm" style={{ alignSelf: "flex-start" }}><ArrowLeft size={15} /> Portafolios</Link>

      <section className={`harvest plot color-${p.color}`} style={{ borderLeftWidth: 8 }}>
        <div className="row between" style={{ alignItems: "flex-start" }}>
          <div>
            <h1>{p.name}</h1>
            {p.description && <p className="muted" style={{ margin: "4px 0 0" }}>{p.description}</p>}
          </div>
          <div className="row">
            <button className="btn btn-secondary btn-sm" onClick={() => setCashModal("deposit")}>Aportar</button>
            <button className="btn btn-secondary btn-sm" onClick={() => setCashModal("withdraw")}>Retirar</button>
            <button className="btn btn-ghost btn-sm" onClick={() => setEditing(true)} aria-label="Editar"><Pencil size={15} /></button>
            <Link className="btn btn-ghost btn-sm" to={`/escenarios?portafolio=${p.id}`}><Sprout size={15} /> Simular crisis</Link>
          </div>
        </div>
        <div className="harvest-value" style={{ fontSize: "clamp(34px, 5vw, 52px)" }}>{money(p.total_value)}</div>
        <div className="row" style={{ gap: 18 }}>
          <span className={`harvest-change ${tone(p.total_return)}`}>{signed(p.total_return)} ({pct(p.total_return_pct)}) total</span>
          <span className={`harvest-change ${tone(p.day_change)}`}>{signed(p.day_change)} ({pct(p.day_change_pct)}) hoy</span>
        </div>
        <div className="metrics" style={{ marginTop: 18 }}>
          <Metric label="Invertido" value={money(p.invested_value)} />
          <Metric label="Efectivo" value={money(p.cash)} />
          <Metric label="Aportes netos" value={money(p.net_contributions)} />
          <Metric label="Ganancia no realizada" value={signed(p.unrealized_pnl)} className={tone(p.unrealized_pnl)} />
          <Metric label="Ganancia realizada" value={signed(p.realized_pnl)} className={tone(p.realized_pnl)} />
          <Metric label="Comisiones pagadas" value={money(p.fees_paid)} />
          {p.margin.open_positions > 0 && <Metric label="Posiciones CFD" value={money(p.cfd_value)} note={`Margen ${money(p.margin.margin_used)} ${Number(p.margin.unrealized_pnl) >= 0 ? "+" : "−"} ${money(Math.abs(p.margin.unrealized_pnl))}`} />}
        </div>
      </section>

      <div className="grid grid-main">
        <div className="stack">
          <section className="panel">
            <div className="panel-head">
              <div className="segmented">
                <button className={view === "backtest" ? "on" : ""} onClick={() => setView("backtest")}>Composición actual vs. S&amp;P 500</button>
                <button className={view === "real" ? "on" : ""} onClick={() => setView("real")}>Evolución real</button>
              </div>
              {view === "backtest" && (
                <div className="segmented">
                  {["1M", "3M", "6M", "1A", "2A"].map((x) => <button key={x} className={range === x ? "on" : ""} onClick={() => setRange(x)}>{x}</button>)}
                </div>
              )}
            </div>
            {view === "backtest" ? (
              !bt || bt.points.length === 0 ? (
                <Empty title="Sin posiciones para comparar">Compra instrumentos y verás cómo le habría ido a esta composición en el pasado.</Empty>
              ) : (
                <>
                  <p className="muted" style={{ fontSize: 13.5 }}>
                    Si hubieras tenido estas mismas posiciones durante el periodo: <Delta value={bt.portfolio_return} /> frente a <Delta value={bt.benchmark_return} /> del S&amp;P 500 (SPY).
                  </p>
                  <div style={{ height: 300 }}>
                    <ResponsiveContainer>
                      <LineChart data={bt.points} margin={{ top: 6, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid stroke="var(--line-soft)" vertical={false} />
                        <XAxis dataKey="date" tickFormatter={dateShort} minTickGap={40} tickLine={false} axisLine={false} />
                        <YAxis tickFormatter={axisMoney} domain={["auto", "auto"]} width={56} tickLine={false} axisLine={false} />
                        <Tooltip content={<ChartTooltip labelFormat={dateLong} rows={[
                          { key: "portfolio", label: "Tu portafolio", format: money, color: "var(--pine)" },
                          { key: "benchmark", label: "S&P 500", format: money, color: "var(--wheat)" },
                        ]} />} />
                        <Line dataKey="portfolio" stroke="var(--pine)" strokeWidth={2.2} dot={false} isAnimationActive={false} />
                        <Line dataKey="benchmark" stroke="var(--wheat)" strokeWidth={1.6} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="legend-inline"><span><i style={{ background: "var(--pine)" }} />Tu portafolio</span><span><i style={{ background: "var(--wheat)" }} />S&amp;P 500 (misma inversión inicial)</span></div>
                </>
              )
            ) : snaps.length < 2 ? (
              <Empty title="Aún no hay suficiente historia">Se guarda una foto del valor de tu portafolio cada minuto que lo consultas y en cada operación.</Empty>
            ) : (
              <>
                <p className="muted" style={{ fontSize: 13.5 }}>Valor del portafolio desde que lo creaste frente a lo que has aportado.</p>
                <div style={{ height: 300 }}>
                  <ResponsiveContainer>
                    <AreaChart data={snaps} margin={{ top: 6, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid stroke="var(--line-soft)" vertical={false} />
                      <XAxis dataKey="ts" type="number" domain={["dataMin", "dataMax"]} scale="time" tickFormatter={(v) => dateTime(new Date(v).toISOString())} minTickGap={60} tickLine={false} axisLine={false} />
                      <YAxis tickFormatter={axisMoney} domain={["auto", "auto"]} width={56} tickLine={false} axisLine={false} />
                      <Tooltip content={<ChartTooltip labelFormat={(v) => dateTime(new Date(v).toISOString())} rows={[
                        { key: "value", label: "Valor", format: money, color: "var(--pine)" },
                        { key: "contributions", label: "Aportes", format: money, color: "var(--wheat)" },
                      ]} />} />
                      <Area type="stepAfter" dataKey="contributions" stroke="var(--wheat)" fill="var(--wheat-tint)" isAnimationActive={false} />
                      <Area type="monotone" dataKey="value" stroke="var(--pine)" strokeWidth={2} fill="var(--pine-tint)" fillOpacity={0.6} isAnimationActive={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </>
            )}
          </section>

        </div>

        <div className="stack">
          <section className="panel">
            <div className="panel-head">
              <h2>Distribución</h2>
              <div className="segmented">
                <button className={alloc === "asset" ? "on" : ""} onClick={() => setAlloc("asset")}>Activo</button>
                <button className={alloc === "sector" ? "on" : ""} onClick={() => setAlloc("sector")}>Sector</button>
                <button className={alloc === "class" ? "on" : ""} onClick={() => setAlloc("class")}>Clase</button>
              </div>
            </div>
            <div style={{ height: 200 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={allocData} dataKey="value" nameKey="name" innerRadius={58} outerRadius={90} paddingAngle={1.5} isAnimationActive={false} stroke="none">
                    {allocData.map((d, k) => <Cell key={d.name} fill={d.name === "Efectivo" ? "#c9d6cd" : PALETTE[k % PALETTE.length]} />)}
                  </Pie>
                  <Tooltip content={<ChartTooltip labelFormat={(_, d) => d.name} rows={[{ key: "value", label: "Valor", format: (v) => `${money(v)} (${pct((v / allocTotal) * 100, false, 1)})` }]} />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="stack" style={{ gap: 6, marginTop: 8 }}>
              {allocData.map((d, k) => (
                <div key={d.name} className="row between" style={{ fontSize: 13.5 }}>
                  <span className="row" style={{ gap: 8 }}><span className="dot" style={{ background: d.name === "Efectivo" ? "#c9d6cd" : PALETTE[k % PALETTE.length] }} />{d.name}</span>
                  <span>{pct((d.value / allocTotal) * 100, false, 1)}</span>
                </div>
              ))}
            </div>
          </section>

        </div>
      </div>

      <section className="panel panel-flush">
        <div className="panel-head" style={{ paddingBottom: 12 }}>
          <h2>Posiciones</h2>
          <Link to="/mercado" className="btn btn-primary btn-sm">Comprar instrumentos</Link>
        </div>
        {p.holdings.length === 0 ? (
          <Empty title="Sin posiciones" action={<Link className="btn btn-secondary" to="/mercado">Ir al mercado</Link>}>
            Tienes {money(p.cash)} listos para invertir.
          </Empty>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Instrumento</th><th className="num">Unidades</th><th className="num">Costo prom.</th>
                  <th className="num">Precio</th><th className="num">Valor</th><th className="num">Ganancia</th>
                  <th className="num">Peso</th><th />
                </tr>
              </thead>
              <tbody>
                {p.holdings.map((h) => (
                  <tr key={h.symbol}>
                    <td>
                      <Link to={`/mercado/${h.symbol}`} className="sym" style={{ color: "inherit" }}>{h.symbol}</Link> <TypeTag type={h.type} />
                      <div className="sym-name">{h.name}</div>
                    </td>
                    <td className="num">{qty(h.quantity)}</td>
                    <td className="num">{price(h.avg_cost)}</td>
                    <td className="num">{price(h.price)}<div><Delta value={h.day_change_pct} /></div></td>
                    <td className="num"><strong>{money(h.market_value)}</strong></td>
                    <td className={`num ${tone(h.unrealized_pnl)}`}>{signed(h.unrealized_pnl)}<div style={{ fontSize: 13 }}>{pct(h.unrealized_pnl_pct)}</div></td>
                    <td className="num">{pct(h.weight, false, 1)}</td>
                    <td className="num">
                      <div className="row" style={{ gap: 6, justifyContent: "flex-end", flexWrap: "nowrap" }}>
                        <button className="btn btn-ghost btn-sm" onClick={() => setProtect(h)} title="Take profit y stop loss">TP/SL</button>
                        <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/mercado/${h.symbol}?portafolio=${p.id}&modo=contado&lado=BUY`)}>Comprar</button>
                        <button className="btn btn-danger btn-sm" onClick={() => navigate(`/mercado/${h.symbol}?portafolio=${p.id}&modo=contado&lado=SELL`)}>Vender</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel panel-flush">
        <div className="panel-head" style={{ paddingBottom: 12 }}>
          <div>
            <h2>Posiciones con margen (CFD)</h2>
            {p.margin.open_positions > 0 && (
              <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                Capital {money(p.margin.equity)} · Margen usado {money(p.margin.margin_used)} · Libre {money(p.margin.free_margin)} ·
                Nivel de margen <strong className={p.margin.margin_call ? "loss" : "gain"}>{p.margin.margin_level === null ? "—" : `${number(p.margin.margin_level, 0)} %`}</strong>
              </div>
            )}
          </div>
          <Link to={`/mercado/SPY?portafolio=${p.id}`} className="btn btn-secondary btn-sm">Abrir operación</Link>
        </div>
        <OpenPositionsTable positions={p.open_positions} showPortfolio={false} onChange={refreshAll}
          emptyText="Con CFD puedes usar apalancamiento y ganar también cuando el precio baja (venta en corto)." />
      </section>

      <div className="grid grid-2">
        <section className="panel">
          <div className="panel-head"><h2>Riesgo</h2><span className="muted" style={{ fontSize: 12.5 }}>Último año</span></div>
          {r.volatility_annual === null ? (
            <p className="muted" style={{ fontSize: 14 }}>Compra al menos un instrumento para calcular las métricas de riesgo.</p>
          ) : (
            <div className="metrics" style={{ borderTop: 0, gridTemplateColumns: "1fr 1fr" }}>
              <Metric label="Volatilidad anual" value={pct(r.volatility_annual, false)} />
              <Metric label="Rendimiento histórico" value={pct(r.expected_return_annual)} className={tone(r.expected_return_annual)} />
              <Metric label="Sharpe" value={number(r.sharpe)} />
              <Metric label="Beta" value={number(r.beta)} />
              <Metric label="VaR 95 % (1 día)" value={money(r.var95_1d)} note="Pérdida que no deberías superar 19 de cada 20 días" />
              <Metric label="Caída máxima" value={pct(r.max_drawdown_1y)} className="loss" />
              <Metric label="Diversificación" value={`${number(r.diversification_score, 0)} / 100`} note={`Equivale a ${number(r.effective_assets, 1)} activos de igual peso`} />
            </div>
          )}
        </section>

        <section className="panel">
          <h2 style={{ marginBottom: 6 }}>Retroalimentación</h2>
          {p.insights.map((x, k) => {
            const Icon = INSIGHT_ICON[x.level] || Info;
            return (
              <div key={k} className={`insight ${x.level}`}>
                <Icon size={18} aria-hidden />
                <div><h4>{x.title}</h4><p>{x.text}</p></div>
              </div>
            );
          })}
        </section>

      </div>

      <section className="panel panel-flush">
        <div className="panel-head" style={{ paddingBottom: 12 }}><h2>Historial de operaciones</h2></div>
        {!txs.data ? <Loader /> : txs.data.length === 0 ? <Empty title="Sin operaciones" /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Fecha</th><th>Tipo</th><th>Instrumento</th><th className="num">Unidades</th><th className="num">Precio</th><th className="num">Comisión</th><th className="num">Monto</th><th className="num">Ganancia realizada</th></tr></thead>
              <tbody>
                {txs.data.map((t) => (
                  <tr key={t.id}>
                    <td className="muted nowrap">{dateTime(t.created_at)}</td>
                    <td><strong className={t.type === "BUY" || t.type === "CFD_OPEN" ? "gain" : t.type === "SELL" || t.type === "CFD_CLOSE" ? "loss" : ""}>{t.type_label}</strong>{t.note && <div className="muted" style={{ fontSize: 12 }}>{t.note}</div>}</td>
                    <td>{t.symbol || "—"}</td>
                    <td className="num">{t.symbol ? qty(t.quantity) : "—"}</td>
                    <td className="num">{t.symbol ? price(t.price) : "—"}</td>
                    <td className="num">{Number(t.fee) ? money(t.fee) : "—"}</td>
                    <td className="num">{money(t.total)}</td>
                    <td className={`num ${tone(t.realized_pnl)}`}>{t.realized_pnl === null ? "—" : signed(t.realized_pnl)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn-danger" onClick={() => setClosing(true)}>Cerrar portafolio</button>
      </div>

      {protect && <ProtectionModal holding={protect} portfolioId={p.id} onClose={() => setProtect(null)} onSaved={refreshAll} />}
      {cashModal && <CashModal kind={cashModal} portfolio={p} onClose={() => setCashModal(null)} onDone={refreshAll} />}
      {editing && <PortfolioForm portfolio={p} onClose={() => setEditing(false)} onSaved={refreshAll} />}
      {closing && (
        <Modal title="Cerrar portafolio" onClose={() => setClosing(false)}>
          <p>Se venderán todas las posiciones a precio de mercado (con comisión) y el efectivo volverá a tu cuenta principal. Esta acción no se puede deshacer.</p>
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button className="btn btn-ghost" onClick={() => setClosing(false)}>Cancelar</button>
            <button className="btn btn-sell" onClick={async () => {
              try {
                const { data } = await api.delete(`/portfolios/${p.id}/`);
                toast(data.detail);
                refreshUser();
                navigate("/portafolios");
              } catch (e) { toast(errorMessage(e), "error"); }
            }}>Vender todo y cerrar</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function CashModal({ kind, portfolio, onClose, onDone }) {
  const { user } = useAuth();
  const toast = useToast();
  const [amount, setAmount] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const deposit = kind === "deposit";
  const max = deposit ? Number(user?.profile?.cash_balance || 0) : Number(portfolio.cash);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post(`/portfolios/${portfolio.id}/${kind}/`, { amount });
      toast(deposit ? `Aportaste ${money(amount)} a ${portfolio.name}.` : `Retiraste ${money(amount)} a tu cuenta principal.`);
      onDone();
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={deposit ? "Aportar efectivo" : "Retirar efectivo"} onClose={onClose}>
      <form onSubmit={submit}>
        <p className="muted" style={{ fontSize: 14 }}>
          {deposit ? "Mueve dinero de tu cuenta principal a este portafolio." : "Devuelve efectivo del portafolio a tu cuenta principal. Para retirar más, primero vende posiciones."}
        </p>
        <div className="field">
          <label htmlFor="ca">Monto</label>
          <div className="input-group">
            <span className="prefix">US$</span>
            <input id="ca" className="input" type="number" min="0" step="any" autoFocus value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
          <span className="hint">Disponible: {money(max)} <button type="button" className="btn btn-ghost btn-sm" onClick={() => setAmount(max.toFixed(2))}>Usar todo</button></span>
        </div>
        {error && <p className="loss" style={{ fontSize: 14 }}>{error}</p>}
        <button className="btn btn-primary btn-block" disabled={busy || !Number(amount)}>{busy ? "Procesando…" : deposit ? "Aportar" : "Retirar"}</button>
      </form>
    </Modal>
  );
}
