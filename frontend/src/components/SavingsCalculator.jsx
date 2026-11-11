import { useEffect, useState } from "react";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api, { errorMessage } from "../api/client";
import ChartTooltip from "./ChartTooltip";
import { Metric } from "./Feedback";
import { axisMoney, money, number, pct } from "../utils/format";

/** Calculadora de interés compuesto: aportes, tasa E.A. o nominal, inflación. */
export default function Calculator() {
  const [form, setForm] = useState({ initial: 5000, monthly: 200, rate: 9.5, years: 15, rate_type: "EA", periods_per_year: 12, inflation: 5 });
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "range" || e.target.type === "number" ? Number(e.target.value) : e.target.value });

  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const { data } = await api.post("/savings/calculator/", form);
        setResult(data);
        setError("");
      } catch (e) {
        setError(errorMessage(e));
      }
    }, 250);
    return () => clearTimeout(t);
  }, [form]);

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Calculadora de interés compuesto</h2>
          <p className="muted" style={{ margin: "4px 0 0", fontSize: 14 }}>Compara el interés compuesto con el simple y descuenta la inflación para ver el valor real.</p>
        </div>
      </div>
      <div className="grid grid-side">
        <div>
          <div className="field">
            <label htmlFor="ci">Aporte inicial</label>
            <div className="input-group"><span className="prefix">US$</span><input id="ci" className="input" type="number" min="0" value={form.initial} onChange={set("initial")} /></div>
          </div>
          <div className="field">
            <label htmlFor="cm">Aporte mensual</label>
            <div className="input-group"><span className="prefix">US$</span><input id="cm" className="input" type="number" min="0" value={form.monthly} onChange={set("monthly")} /></div>
          </div>
          <div className="range-field">
            <div className="row"><label htmlFor="cr">Tasa anual</label><output>{number(form.rate, 2)} %</output></div>
            <input id="cr" type="range" min="0" max="30" step="0.25" value={form.rate} onChange={set("rate")} />
          </div>
          <div className="field">
            <label htmlFor="ct">Tipo de tasa</label>
            <select id="ct" className="input" value={form.rate_type} onChange={set("rate_type")}>
              <option value="EA">Efectiva anual (E.A.)</option>
              <option value="NOMINAL">Nominal</option>
            </select>
          </div>
          {form.rate_type === "NOMINAL" && (
            <div className="field">
              <label htmlFor="cp">Capitalización</label>
              <select id="cp" className="input" value={form.periods_per_year} onChange={(e) => setForm({ ...form, periods_per_year: Number(e.target.value) })}>
                <option value={12}>Mensual (N.M.V.)</option><option value={4}>Trimestral (N.T.V.)</option>
                <option value={2}>Semestral</option><option value={1}>Anual</option><option value={365}>Diaria</option>
              </select>
            </div>
          )}
          <div className="range-field">
            <div className="row"><label htmlFor="cy">Años</label><output>{form.years}</output></div>
            <input id="cy" type="range" min="1" max="40" value={form.years} onChange={set("years")} />
          </div>
          <div className="range-field">
            <div className="row"><label htmlFor="cf">Inflación anual</label><output>{number(form.inflation, 1)} %</output></div>
            <input id="cf" type="range" min="0" max="15" step="0.5" value={form.inflation} onChange={set("inflation")} />
          </div>
        </div>
        <div>
          {error && <p className="loss">{error}</p>}
          {result && (
            <>
              <div className="metrics" style={{ borderTop: 0 }}>
                <Metric label="Saldo final" value={money(result.final_balance, true)} />
                <Metric label="Total aportado" value={money(result.total_contributed, true)} />
                <Metric label="Intereses ganados" value={money(result.total_interest, true)} className="gain" />
                <Metric label="Ventaja vs. interés simple" value={money(result.compound_advantage, true)} />
                <Metric label="Valor real (sin inflación)" value={money(result.final_real, true)} note="En dinero de hoy" />
                <Metric label="Se duplica en" value={result.years_to_double ? `${number(result.years_to_double, 1)} años` : "—"} note={`Regla del 72: ${number(result.rule_of_72, 1)} años`} />
              </div>
              <div style={{ height: 280, marginTop: 10 }}>
                <ResponsiveContainer>
                  <ComposedChart data={result.rows} margin={{ top: 6, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="var(--line-soft)" vertical={false} />
                    <XAxis dataKey="year" tickFormatter={(v) => `${v} a`} tickLine={false} axisLine={false} />
                    <YAxis tickFormatter={axisMoney} width={56} tickLine={false} axisLine={false} />
                    <Tooltip content={<ChartTooltip labelFormat={(l) => `Año ${l}`} rows={[
                      { key: "balance", label: "Compuesto", format: money, color: "var(--pine)" },
                      { key: "simple", label: "Simple", format: money, color: "var(--ink)" },
                      { key: "real", label: "Valor real", format: money, color: "var(--loss)" },
                      { key: "contributed", label: "Aportado", format: money, color: "var(--wheat)" },
                    ]} />} />
                    <Area dataKey="balance" stroke="var(--pine)" strokeWidth={2} fill="var(--pine-tint)" isAnimationActive={false} />
                    <Area dataKey="contributed" stroke="var(--wheat)" fill="var(--wheat-tint)" isAnimationActive={false} />
                    <Line dataKey="simple" stroke="var(--ink)" strokeDasharray="5 4" dot={false} isAnimationActive={false} />
                    <Line dataKey="real" stroke="var(--loss)" strokeDasharray="2 3" dot={false} isAnimationActive={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              <div className="legend-inline" style={{ marginTop: 6 }}>
                <span><i style={{ background: "var(--pine)" }} />Interés compuesto</span>
                <span><i style={{ background: "var(--wheat)" }} />Total aportado</span>
                <span><i style={{ background: "var(--ink)" }} />Interés simple</span>
                <span><i style={{ background: "var(--loss)" }} />Valor real (descontando inflación)</span>
              </div>
              <p className="muted" style={{ fontSize: 13, marginTop: 12, marginBottom: 0 }}>
                Tasa efectiva anual {pct(result.effective_annual, false, 2)} · equivale a {pct(result.monthly_rate, false, 3)} mensual · nominal mes vencido {pct(result.nominal_monthly_equivalent, false, 2)}.
              </p>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
