import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Area, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Play, Trash2 } from "lucide-react";
import api, { errorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import usePolling from "../hooks/usePolling";
import ChartTooltip from "../components/ChartTooltip";
import { Delta, Empty, Loader, Metric } from "../components/Feedback";
import { axisMoney, dateTime, money, number, pct, tone } from "../utils/format";

const SLIDERS = [
  { key: "market_shock", label: "Choque al mercado", min: -60, max: 40, step: 1, fmt: (v) => `${v > 0 ? "+" : ""}${v} %`,
    help: "Caída (o subida) total del mercado accionario. Cada activo la recibe según su beta y su tipo." },
  { key: "shock_days", label: "Duración del choque", min: 0, max: 400, step: 1, fmt: (v) => (v ? `${v} días` : "Inmediato"),
    help: "Días hábiles en los que se reparte el choque." },
  { key: "recovery", label: "Recuperación posterior", min: 0, max: 100, step: 5, fmt: (v) => `${v} %`,
    help: "Porcentaje de la caída que se recupera en el resto del horizonte." },
  { key: "volatility_multiplier", label: "Volatilidad", min: 0.5, max: 3, step: 0.1, fmt: (v) => `${number(v, 1)}×`,
    help: "Multiplica la volatilidad normal de todos los activos." },
  { key: "rate_change", label: "Cambio en tasas de interés", min: -5, max: 6, step: 0.25, fmt: (v) => `${v > 0 ? "+" : ""}${number(v, 2)} pts`,
    help: "Afecta sobre todo a los bonos (por su duración), al sector inmobiliario y al rendimiento del efectivo." },
  { key: "drift_adjustment", label: "Ajuste al rendimiento anual", min: -15, max: 15, step: 0.5, fmt: (v) => `${v > 0 ? "+" : ""}${number(v, 1)} pts`,
    help: "Suma o resta puntos al rendimiento esperado de todos los activos." },
  { key: "horizon_days", label: "Horizonte", min: 21, max: 1260, step: 21, fmt: (v) => (v >= 252 ? `${number(v / 252, 1)} años` : `${Math.round(v / 21)} meses`),
    help: "Cuánto tiempo hacia adelante se simula (252 días hábiles = 1 año)." },
];

export default function Scenarios() {
  const toast = useToast();
  const [params] = useSearchParams();
  const portfolios = usePolling("/portfolios/");
  const presets = usePolling("/scenarios/presets/");
  const history = usePolling("/scenarios/history/");
  const [portfolioId, setPortfolioId] = useState(params.get("portafolio") || "");
  const [preset, setPreset] = useState("crisis_2008");
  const [values, setValues] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const resultRef = useRef(null);

  useEffect(() => {
    if (!portfolioId && portfolios.data?.length) {
      const withPositions = portfolios.data.find((p) => p.positions + (p.cfd_positions || 0) > 0) || portfolios.data[0];
      setPortfolioId(String(withPositions.id));
    }
  }, [portfolios.data, portfolioId]);

  useEffect(() => {
    if (presets.data && !values) setValues(presets.data.find((p) => p.key === preset).params);
  }, [presets.data, preset, values]);

  const choosePreset = (p) => {
    setPreset(p.key);
    setValues(p.params);
  };

  const setValue = (k, v) => {
    setPreset("custom");
    const next = { ...values, [k]: Number(v) };
    if (k === "horizon_days" && next.shock_days > next.horizon_days) next.shock_days = next.horizon_days;
    setValues(next);
  };

  const run = async () => {
    setBusy(true);
    try {
      const body = { portfolio_id: Number(portfolioId), preset, ...values, shock_days: Math.min(values.shock_days, values.horizon_days) };
      const { data } = await api.post("/scenarios/simulate/", body);
      setResult(data);
      history.reload(true);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
    } catch (e) {
      toast(errorMessage(e), "error");
    } finally {
      setBusy(false);
    }
  };

  const current = presets.data?.find((p) => p.key === preset);

  if (portfolios.loading || presets.loading || !values) return <Loader />;
  if (portfolios.data.length === 0) {
    return (
      <section className="panel">
        <Empty title="Necesitas un portafolio con inversiones" action={<Link className="btn btn-primary" to="/portafolios?nuevo=1">Crear portafolio</Link>}>
          Los escenarios ponen a prueba un portafolio real tuyo frente a crisis y cambios de tasas.
        </Empty>
      </section>
    );
  }

  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Simulación de escenarios</h1>
          <p>¿Qué le pasaría a tu portafolio en una crisis como la de 2008, una pandemia o un alza fuerte de tasas? Simulamos mil futuros posibles con el método de Monte Carlo.</p>
        </div>
      </div>

      <div className="grid grid-side">
        <section className="panel">
          <div className="field">
            <label htmlFor="sp">Portafolio a simular</label>
            <select id="sp" className="input" value={portfolioId} onChange={(e) => { setPortfolioId(e.target.value); setResult(null); }}>
              {portfolios.data.map((p) => <option key={p.id} value={p.id}>{p.name} — {money(p.total_value, true)}{p.positions + (p.cfd_positions || 0) === 0 ? " (sin posiciones)" : p.cfd_positions ? ` · ${p.cfd_positions} CFD` : ""}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Escenario</label>
            <div className="chips">
              {presets.data.map((p) => <button key={p.key} type="button" className={`chip ${preset === p.key ? "on" : ""}`} onClick={() => choosePreset(p)}>{p.name}</button>)}
              <button type="button" className={`chip ${preset === "custom" ? "on" : ""}`} onClick={() => setPreset("custom")}>Personalizado</button>
            </div>
          </div>
          {current && <div className="callout" style={{ marginBottom: 16 }}><strong>{current.summary}</strong><br />{current.context}</div>}
          {SLIDERS.map((s) => (
            <div key={s.key} className="range-field">
              <div className="row"><label htmlFor={s.key}>{s.label}</label><output>{s.fmt(values[s.key])}</output></div>
              <input id={s.key} type="range" min={s.min} max={s.key === "shock_days" ? Math.min(s.max, values.horizon_days) : s.max} step={s.step}
                     value={values[s.key]} onChange={(e) => setValue(s.key, e.target.value)} title={s.help} />
              <div className="muted" style={{ fontSize: 12 }}>{s.help}</div>
            </div>
          ))}
          <button className="btn btn-primary btn-block" onClick={run} disabled={busy || !portfolioId}>
            <Play size={16} /> {busy ? "Simulando 1.000 futuros…" : "Simular"}
          </button>
        </section>

        <div className="stack" ref={resultRef} style={{ position: "relative" }}>
          {busy && <div className="busy-overlay"><div className="spinner" /><span>Simulando 1.000 futuros posibles…</span></div>}
          {!result ? (
            <section className="panel">
              <Empty title="Elige un escenario y pulsa «Simular»">
                Verás un abanico con el rango de valores posibles de tu portafolio: el centro es el caso típico y los bordes, los casos extremos.
              </Empty>
            </section>
          ) : <Result result={result} />}

          <section className="panel panel-flush">
            <div className="panel-head" style={{ paddingBottom: 12 }}><h2>Simulaciones anteriores</h2></div>
            {!history.data?.length ? <Empty title="Aún no hay simulaciones" /> : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Fecha</th><th>Portafolio</th><th>Escenario</th><th className="num">Mediana final</th><th className="num">Prob. pérdida</th><th /></tr></thead>
                  <tbody>
                    {history.data.map((h) => (
                      <tr key={h.id}>
                        <td className="muted nowrap">{dateTime(h.created_at)}</td>
                        <td>{h.portfolio_name}</td>
                        <td>{presets.data.find((p) => p.key === h.preset)?.name || "Personalizado"}</td>
                        <td className="num">{money(h.summary.median_final, true)} <Delta value={h.summary.median_return_pct} icon={false} /></td>
                        <td className="num">{pct(h.summary.prob_loss, false, 1)}</td>
                        <td className="num">
                          <button className="icon-btn" aria-label="Eliminar" onClick={async () => { await api.delete(`/scenarios/history/${h.id}/`); history.reload(true); }}>
                            <Trash2 size={15} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function Result({ result }) {
  const s = result.summary;
  const dayLabel = (d) => (d >= 252 ? `Año ${number(d / 252, 1)}` : `Mes ${Math.round(d / 21)}`);
  return (
    <>
      <section className="panel">
        <div className="panel-head">
          <h2>Abanico de resultados</h2>
          <span className="muted" style={{ fontSize: 13 }}>{s.paths} trayectorias · {s.horizon_days} días hábiles</span>
        </div>
        <div style={{ height: 340 }}>
          <ResponsiveContainer>
            <ComposedChart data={result.bands} margin={{ top: 6, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="var(--line-soft)" vertical={false} />
              <XAxis dataKey="day" tickFormatter={dayLabel} minTickGap={50} tickLine={false} axisLine={false} />
              <YAxis tickFormatter={axisMoney} width={56} tickLine={false} axisLine={false} domain={["auto", "auto"]} />
              <ReferenceLine y={s.initial_value} stroke="var(--muted)" strokeDasharray="2 4" />
              <Tooltip content={<ChartTooltip labelFormat={(d) => `Día ${d}`} rows={[
                { key: "p95", label: "Caso optimista (95 %)", format: money },
                { key: "p75", label: "Percentil 75", format: money },
                { key: "p50", label: "Caso típico (mediana)", format: money, color: "var(--pine)" },
                { key: "p25", label: "Percentil 25", format: money },
                { key: "p5", label: "Caso pesimista (5 %)", format: money },
                { key: "baseline", label: "Sin escenario", format: money, color: "var(--wheat)" },
              ]} />} />
              <Area dataKey="band_outer" stroke="none" fill="var(--pine)" fillOpacity={0.12} isAnimationActive={false} />
              <Area dataKey="band_inner" stroke="none" fill="var(--pine)" fillOpacity={0.22} isAnimationActive={false} />
              <Line dataKey="p50" stroke="var(--pine)" strokeWidth={2.4} dot={false} isAnimationActive={false} />
              <Line dataKey="baseline" stroke="var(--wheat)" strokeWidth={1.8} strokeDasharray="6 4" dot={false} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <div className="legend-inline" style={{ marginTop: 6 }}>
          <span><i style={{ background: "var(--pine)" }} />Caso típico</span>
          <span><i style={{ background: "rgba(30,90,67,.35)", height: 10 }} />50 % central</span>
          <span><i style={{ background: "rgba(30,90,67,.15)", height: 10 }} />90 % de los casos</span>
          <span><i style={{ background: "var(--wheat)" }} />Mercado normal (sin escenario)</span>
          <span><i style={{ background: "var(--muted)" }} />Valor inicial</span>
        </div>
        <div className="metrics" style={{ marginTop: 16 }}>
          <Metric label="Valor inicial" value={money(s.initial_value, true)} />
          <Metric label="Caso típico al final" value={money(s.median_final, true)} note={<Delta value={s.median_return_pct} icon={false} />} />
          <Metric label="Probabilidad de pérdida" value={pct(s.prob_loss, false, 1)} className={s.prob_loss > 50 ? "loss" : ""} />
          <Metric label="Perder más de 20 %" value={pct(s.prob_loss_20, false, 1)} />
          <Metric label="VaR 95 %" value={money(s.var95, true)} note="Pérdida en el 5 % peor" />
          <Metric label="Caída máxima típica" value={pct(s.median_max_drawdown_pct)} className="loss" />
        </div>
      </section>

      <div className="grid grid-2">
        <section className="panel">
          <h2 style={{ marginBottom: 10 }}>¿Qué significa?</h2>
          <ul style={{ paddingLeft: 18, margin: 0, fontSize: 14 }}>
            {result.explanation.map((t, i) => <li key={i} style={{ marginBottom: 8 }}>{t}</li>)}
          </ul>
        </section>
        <section className="panel">
          <h2 style={{ marginBottom: 10 }}>Distribución del rendimiento final</h2>
          <div style={{ height: 210 }}>
            <ResponsiveContainer>
              <BarChart data={result.histogram} margin={{ top: 4, right: 4, left: -18, bottom: 0 }}>
                <XAxis dataKey="mid" tickFormatter={(v) => `${Math.round(v)} %`} minTickGap={24} tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip cursor={{ fill: "var(--field)" }} content={<ChartTooltip labelFormat={(_, d) => `${number(d.from, 1)} % a ${number(d.to, 1)} %`} rows={[{ key: "count", label: "Trayectorias" }]} />} />
                <Bar dataKey="count" isAnimationActive={false} radius={[3, 3, 0, 0]}>
                  {result.histogram.map((b) => <Cell key={b.mid} fill={b.mid < 0 ? "var(--loss)" : "var(--gain)"} fillOpacity={0.8} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <section className="panel panel-flush">
        <div className="panel-head" style={{ paddingBottom: 12 }}>
          <h2>Impacto por activo</h2>
          {s.has_leverage && <span className="muted" style={{ fontSize: 12.5 }}>Los CFD se cierran en la simulación si su capital cae a la mitad del margen. No se consideran TP/SL.</span>}
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Activo</th><th>Tipo</th><th>Clase</th><th className="num">Valor hoy</th><th className="num">Choque directo</th><th className="num">Caso típico al final</th></tr></thead>
            <tbody>
              {result.assets.map((a) => (
                <tr key={a.symbol + a.kind}>
                  <td><span className="sym">{a.symbol}</span><div className="sym-name">{a.name}</div></td>
                  <td><span className={`tag ${a.kind === "Contado" ? "" : "tag-etf"}`}>{a.kind}</span></td>
                  <td className="muted">{a.asset_class}</td>
                  <td className="num">{money(a.initial_value, true)}</td>
                  <td className={`num ${tone(a.shock_pct)}`}>{pct(a.shock_pct, true, 1)}</td>
                  <td className="num">{money(a.median_final, true)} <Delta value={a.median_return_pct} icon={false} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
