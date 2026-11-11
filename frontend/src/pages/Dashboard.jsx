import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import Avatar from "../components/Avatar";
import NewsList from "../components/NewsList";
import { useAuth } from "../context/AuthContext";
import usePolling from "../hooks/usePolling";
import { Delta, Empty, ErrorBox, Loader, Metric } from "../components/Feedback";
import { dateTime, money, pct, price, qty, signed, tone } from "../utils/format";

const SEGMENTS = [
  { key: "cash", label: "Efectivo disponible", color: "var(--sage)" },
  { key: "portfolios", label: "Portafolios", color: "var(--pine)" },
  { key: "savings", label: "Ahorro y CDT", color: "var(--wheat)" },
];

export default function Dashboard() {
  const { user } = useAuth();
  const { data, error, loading, reload } = usePolling("/dashboard/", 15000);
  const market = usePolling("/market/overview/", 15000);

  if (loading && !data) return <Loader />;
  if (error && !data) return <ErrorBox error={error} onRetry={reload} />;

  const nw = data.net_worth;
  const total = Number(nw.total) || 1;

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Hola, {user?.first_name || user?.username}</h1>
          <p>Así va tu cosecha. Los precios se actualizan solos cada pocos segundos.</p>
        </div>
      </div>

      <section className="harvest" aria-label="Patrimonio total">
        <div className="harvest-label">Patrimonio total simulado</div>
        <div className="harvest-value">{money(nw.total)}</div>
        <div className={`harvest-change ${tone(nw.gain)}`}>
          {signed(nw.gain)} ({pct(nw.gain_pct)}) desde tu saldo inicial de {money(nw.initial_balance, true)}
        </div>
        <div className="furrow" role="img" aria-label="Distribución del patrimonio">
          {SEGMENTS.map((s) => (
            <span key={s.key} style={{ width: `${(Number(nw[s.key]) / total) * 100}%`, background: s.color }} />
          ))}
        </div>
        <div className="furrow-legend">
          {SEGMENTS.map((s) => (
            <span key={s.key}><i style={{ background: s.color }} />{s.label} <strong>{money(nw[s.key])}</strong> · {pct((Number(nw[s.key]) / total) * 100, false, 1)}</span>
          ))}
        </div>
      </section>

      <div className="grid grid-main">
        <div className="stack">
          <section className="panel">
            <div className="panel-head">
              <h2>Tus portafolios</h2>
              <Link to="/portafolios" className="btn btn-ghost btn-sm">Ver todos <ArrowRight size={15} /></Link>
            </div>
            {data.portfolios.length === 0 ? (
              <Empty title="Aún no tienes portafolios" action={<Link className="btn btn-primary" to="/portafolios?nuevo=1">Crear mi primer portafolio</Link>}>
                Un portafolio agrupa tus inversiones. Puedes tener varios con estrategias distintas.
              </Empty>
            ) : (
              <div className="grid grid-2">
                {data.portfolios.map((p) => (
                  <Link key={p.id} to={`/portafolios/${p.id}`} className={`plot color-${p.color}`}>
                    <h3>{p.name}</h3>
                    <div className="value">{money(p.total_value)}</div>
                    <div className="row" style={{ gap: 14, fontSize: 13 }}>
                      <span>Total <Delta value={p.total_return_pct} /></span>
                      <span>Hoy <Delta value={p.day_change_pct} /></span>
                      <span className="muted">{p.positions} {p.positions === 1 ? "posición" : "posiciones"}{p.cfd_positions ? ` · ${p.cfd_positions} CFD` : ""}</span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </section>

          <section className="panel panel-flush">
            <div className="panel-head"><h2>Últimos movimientos</h2></div>
            {data.recent_transactions.length === 0 ? (
              <Empty title="Sin movimientos todavía">Tus compras, ventas y aportes aparecerán aquí.</Empty>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Fecha</th><th>Operación</th><th>Portafolio</th><th className="num">Monto</th></tr></thead>
                  <tbody>
                    {data.recent_transactions.map((t) => (
                      <tr key={t.id}>
                        <td className="muted nowrap">{dateTime(t.created_at)}</td>
                        <td>
                          <strong className={t.type === "BUY" ? "gain" : t.type === "SELL" ? "loss" : ""}>{t.type_label}</strong>{" "}
                          {t.symbol && <span>{qty(t.quantity)} {t.symbol} a {price(t.price)}</span>}
                        </td>
                        <td>{t.portfolio_name}</td>
                        <td className="num">{money(t.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>

        <div className="stack">
          <section className="panel">
            <div className="panel-head">
              <h2>Mercado hoy</h2>
              <Link to="/mercado" className="btn btn-ghost btn-sm">Mercado <ArrowRight size={15} /></Link>
            </div>
            {market.data ? (
              <>
                {market.data.benchmark && (
                  <div className="row between" style={{ marginBottom: 12 }}>
                    <div>
                      <div className="muted" style={{ fontSize: 13 }}>S&amp;P 500 (SPY)</div>
                      <strong style={{ fontSize: 20 }}>{price(market.data.benchmark.current_price)}</strong>
                    </div>
                    <Delta value={market.data.benchmark.change_pct} pill />
                  </div>
                )}
                <div className="muted" style={{ fontSize: 13, marginBottom: 6 }}>
                  {market.data.breadth.advancing} suben · {market.data.breadth.declining} bajan
                </div>
                <h3 style={{ margin: "14px 0 6px" }}>Más suben</h3>
                {market.data.gainers.slice(0, 3).map((i) => <MoverRow key={i.symbol} i={i} />)}
                <h3 style={{ margin: "14px 0 6px" }}>Más bajan</h3>
                {market.data.losers.slice(0, 3).map((i) => <MoverRow key={i.symbol} i={i} />)}
              </>
            ) : <Loader />}
          </section>

          <section className="panel">
            <div className="panel-head"><h2>Ahorro y CDT</h2><Link to="/ahorro" className="btn btn-ghost btn-sm">Abrir <ArrowRight size={15} /></Link></div>
            <div className="metrics" style={{ borderTop: 0 }}>
              <Metric label="Saldo" value={money(data.savings.value)} />
              <Metric label="Intereses" value={money(data.savings.interest)} className="gain" />
              <Metric label="Cuentas activas" value={data.savings.accounts} />
            </div>
          </section>

          <section className="panel">
            <div className="panel-head"><h2>Ranking</h2><Link to="/ranking" className="btn btn-ghost btn-sm">Ver todo <ArrowRight size={15} /></Link></div>
            {data.ranking.map((r) => (
              <div key={r.user_id} className="rank-row" style={{ fontWeight: r.is_me ? 700 : 400 }}>
                <span className="muted rank-pos">{r.position}</span>
                <Avatar name={r.name} url={r.avatar_url} size={28} />
                <span className="ellipsis" style={{ flex: 1 }}>{r.name}{r.is_me && " (tú)"}</span>
                <span className={tone(r.profit)} style={{ whiteSpace: "nowrap" }}>{signed(r.profit)}</span>
              </div>
            ))}
          </section>

          <section className="panel">
            <div className="panel-head"><h2>Noticias del mercado</h2></div>
            <NewsList url="/market/news/" limit={5} compact />
          </section>
        </div>
      </div>
    </div>
  );
}

function MoverRow({ i }) {
  return (
    <Link to={`/mercado/${i.symbol}`} className="row between" style={{ padding: "6px 0", textDecoration: "none", color: "inherit" }}>
      <span><strong>{i.symbol}</strong> <span className="muted" style={{ fontSize: 13 }}>{price(i.current_price, i.quote_currency)}</span></span>
      <Delta value={i.change_pct} />
    </Link>
  );
}

