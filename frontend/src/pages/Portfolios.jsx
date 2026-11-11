import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Plus } from "lucide-react";
import usePolling from "../hooks/usePolling";
import { Delta, Empty, ErrorBox, Loader } from "../components/Feedback";
import { money } from "../utils/format";
import PortfolioForm from "./PortfolioForm";

export default function Portfolios() {
  const { data, error, loading, reload } = usePolling("/portfolios/", 15000);
  const [params, setParams] = useSearchParams();
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (params.get("nuevo")) {
      setCreating(true);
      setParams({}, { replace: true });
    }
  }, [params, setParams]);

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Portafolios</h1>
          <p>Cada portafolio tiene su propio efectivo. Úsalos para comparar estrategias: uno conservador, uno agresivo, uno solo de Colombia…</p>
        </div>
        <button className="btn btn-primary" onClick={() => setCreating(true)}><Plus size={16} /> Nuevo portafolio</button>
      </div>

      {error && !data && <ErrorBox error={error} onRetry={reload} />}
      {loading && !data ? <Loader /> : data?.length === 0 ? (
        <section className="panel">
          <Empty title="Empieza tu primer portafolio" action={<button className="btn btn-primary" onClick={() => setCreating(true)}>Crear portafolio</button>}>
            Asigna una parte de tus US$ 100.000 ficticios y empieza a comprar acciones o ETFs.
          </Empty>
        </section>
      ) : (
        <div className="grid grid-3">
          {data?.map((p) => (
            <Link key={p.id} to={`/portafolios/${p.id}`} className={`plot color-${p.color}`}>
              <h3>{p.name}</h3>
              {p.description && <p className="muted" style={{ fontSize: 13, margin: "4px 0 0" }}>{p.description}</p>}
              <div className="value">{money(p.total_value)}</div>
              <div className="row" style={{ gap: 14, fontSize: 13 }}>
                <span>Total <Delta value={p.total_return_pct} /></span>
                <span>Hoy <Delta value={p.day_change_pct} /></span>
              </div>
              <div className="row between" style={{ marginTop: 12, fontSize: 13, color: "var(--muted)" }}>
                <span>Efectivo {money(p.cash)}</span>
                <span>{p.positions} {p.positions === 1 ? "posición" : "posiciones"}</span>
              </div>
              {p.top_holdings.length > 0 && (
                <div className="row" style={{ gap: 6, marginTop: 10 }}>
                  {p.top_holdings.map((s) => <span key={s} className="tag">{s}</span>)}
                </div>
              )}
            </Link>
          ))}
        </div>
      )}
      {creating && <PortfolioForm onClose={() => setCreating(false)} onSaved={reload} />}
    </div>
  );
}
