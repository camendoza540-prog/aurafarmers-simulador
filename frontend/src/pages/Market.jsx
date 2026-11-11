import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import usePolling from "../hooks/usePolling";
import { Delta, Empty, ErrorBox, Loader, TypeTag } from "../components/Feedback";
import Sparkline from "../components/Sparkline";
import { price } from "../utils/format";

const TYPES = [
  ["", "Todos"], ["STOCK", "Acciones"], ["ETF", "ETFs"], ["FOREX", "Forex"],
  ["INDEX", "Índices"], ["COMMODITY", "Materias primas"], ["CRYPTO", "Cripto"],
];

export default function Market() {
  const navigate = useNavigate();
  const { data, error, loading, reload } = usePolling("/market/instruments/", 5000);
  const [type, setType] = useState("");
  const [sector, setSector] = useState("");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState({ key: "symbol", dir: 1 });

  const sectors = useMemo(() => [...new Set((data || []).filter((i) => !type || i.type === type).map((i) => i.sector))].sort(), [data, type]);

  const rows = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    return data
      .filter((i) => (!type || i.type === type) && (!sector || i.sector === sector))
      .filter((i) => !q || i.symbol.toLowerCase().includes(q) || i.name.toLowerCase().includes(q))
      .sort((a, b) => {
        const av = a[sort.key], bv = b[sort.key];
        return (typeof av === "string" ? av.localeCompare(bv) : av - bv) * sort.dir;
      });
  }, [data, type, sector, query, sort]);

  const sortBy = (key) => setSort((s) => ({ key, dir: s.key === key ? -s.dir : key === "symbol" ? 1 : -1 }));
  const arrow = (key) => (sort.key === key ? (sort.dir > 0 ? " ↑" : " ↓") : "");

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Mercado</h1>
          <p>Acciones, ETFs, divisas, índices, materias primas y criptomonedas con precios en vivo. Elige un activo para abrir su gráfico, operar y leer sus noticias. Divisas, índices, materias primas y cripto se operan solo como CFD con margen.</p>
        </div>
      </div>

      <section className="panel panel-flush">
        <div className="panel-head" style={{ paddingBottom: 14 }}>
          <div className="row">
            <div className="segmented">
              {TYPES.map(([v, l]) => (
                <button key={v} className={type === v ? "on" : ""} onClick={() => { setType(v); setSector(""); }}>
                  {l} {data && <span className="seg-count">{v ? data.filter((i) => i.type === v).length : data.length}</span>}
                </button>
              ))}
            </div>
            <select className="input" style={{ width: "auto" }} value={sector} onChange={(e) => setSector(e.target.value)} aria-label="Filtrar por sector">
              <option value="">Todos los sectores</option>
              {sectors.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div className="input-group" style={{ width: 260 }}>
            <Search size={16} className="prefix" style={{ left: 12 }} />
            <input className="input" placeholder="Buscar símbolo o nombre" value={query} onChange={(e) => setQuery(e.target.value)} style={{ paddingLeft: 36 }} />
          </div>
        </div>

        {error && !data && <div style={{ padding: 20 }}><ErrorBox error={error} onRetry={reload} /></div>}
        {loading && !data ? <Loader /> : rows.length === 0 ? (
          <Empty title="Sin resultados">Prueba con otro filtro o término de búsqueda.</Empty>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ cursor: "pointer" }} onClick={() => sortBy("symbol")}>Instrumento{arrow("symbol")}</th>
                  <th>Tipo</th>
                  <th>Sector</th>
                  <th>30 días</th>
                  <th className="num" style={{ cursor: "pointer" }} onClick={() => sortBy("current_price")}>Precio{arrow("current_price")}</th>
                  <th className="num" style={{ cursor: "pointer" }} onClick={() => sortBy("change_pct")}>Hoy{arrow("change_pct")}</th>
                  <th className="num"><span className="sr-only">Acciones</span></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((i) => (
                  <tr key={i.symbol} className="clickable" onClick={() => navigate(`/mercado/${i.symbol}`)}>
                    <td><div className="sym">{i.symbol}</div><div className="sym-name">{i.name}</div></td>
                    <td><TypeTag type={i.type} /></td>
                    <td className="muted" style={{ fontSize: 13.5 }}>{i.sector}</td>
                    <td><Sparkline data={i.sparkline} /></td>
                    <td className="num"><strong>{price(i.current_price, i.quote_currency)}</strong>{i.max_leverage > 5 && <div className="muted" style={{ fontSize: 11.5 }}>hasta 1:{i.max_leverage}</div>}</td>
                    <td className="num"><Delta value={i.change_pct} /></td>
                    <td className="num" onClick={(e) => e.stopPropagation()}>
                      <button className="btn btn-primary btn-sm" onClick={() => navigate(`/mercado/${i.symbol}`)}>Operar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
