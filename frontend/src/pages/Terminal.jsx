import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  BarChart3, CandlestickChart, ChevronDown, Eraser, Expand, LineChart, Minus, MousePointer2, Search, TrendingUp,
} from "lucide-react";
import api from "../api/client";
import { useToast } from "../context/ToastContext";
import usePolling from "../hooks/usePolling";
import { Delta, Empty, Metric, TypeTag } from "../components/Feedback";
import NewsList from "../components/NewsList";
import OrderTicket from "../components/OrderTicket";
import ProtectionModal from "../components/ProtectionModal";
import { ClosedPositionsTable, OpenPositionsTable } from "../components/PositionsTable";
import TradingChart from "../components/chart/TradingChart";
import { INDICATORS } from "../components/chart/indicators";
import { money, number, pct, price, qty, signed, tone } from "../utils/format";

const TIMEFRAMES = [
  { v: "1m", l: "1m" }, { v: "5m", l: "5m" }, { v: "15m", l: "15m" }, { v: "30m", l: "30m" }, { v: "1h", l: "1h" },
  { v: "1D", l: "1D" }, { v: "1S", l: "1S" }, { v: "1M", l: "1M" },
];
const TYPES = [
  { v: "candles", l: "Velas", icon: CandlestickChart },
  { v: "heikin", l: "Heikin Ashi", icon: CandlestickChart },
  { v: "bars", l: "Barras OHLC", icon: BarChart3 },
  { v: "line", l: "Línea", icon: LineChart },
  { v: "area", l: "Área", icon: TrendingUp },
];
const PREFS_KEY = "af_chart_prefs";

function loadPrefs() {
  try {
    return { tf: "5m", type: "candles", indicators: ["sma20", "volume"], ...JSON.parse(localStorage.getItem(PREFS_KEY) || "{}") };
  } catch {
    return { tf: "5m", type: "candles", indicators: ["sma20", "volume"] };
  }
}

export default function Terminal() {
  const { symbol: rawSymbol } = useParams();
  const symbol = rawSymbol.toUpperCase();
  const navigate = useNavigate();
  const toast = useToast();
  const [params] = useSearchParams();
  const prefs = useMemo(loadPrefs, []);
  const [tf, setTf] = useState(prefs.tf);
  const [chartType, setChartType] = useState(prefs.type);
  const [indicators, setIndicators] = useState(prefs.indicators);
  const [tool, setTool] = useState("cursor");
  const [status, setStatus] = useState(null);
  const [menu, setMenu] = useState(null);
  const [tab, setTab] = useState("positions");
  const [onlySymbol, setOnlySymbol] = useState(false);
  const [quote, setQuote] = useState(null);
  const [flash, setFlash] = useState("");
  const [portfolioId, setPortfolioId] = useState(params.get("portafolio") || "");
  const [editHolding, setEditHolding] = useState(null);
  const chartRef = useRef(null);
  const lastPrice = useRef(null);
  const knownOpen = useRef(null);

  useEffect(() => {
    try { localStorage.setItem(PREFS_KEY, JSON.stringify({ tf, type: chartType, indicators })); } catch { /* sin almacenamiento */ }
  }, [tf, chartType, indicators]);

  const instruments = usePolling("/market/instruments/", 0);
  const info = usePolling(`/market/instruments/${symbol}/`, 60000);
  const account = usePolling("/trading/account/", 4000);
  const openPos = usePolling("/positions/?status=OPEN", 2000);
  const closedPos = usePolling("/positions/?status=CLOSED", 0);

  useEffect(() => {
    if (!portfolioId && account.data?.portfolios?.length) setPortfolioId(String(account.data.portfolios[0].id));
  }, [account.data, portfolioId]);

  // Cotización en vivo cada segundo
  useEffect(() => {
    let alive = true;
    setQuote(null);
    lastPrice.current = null;
    const load = async () => {
      if (document.visibilityState !== "visible") return;
      try {
        const { data } = await api.get(`/market/quotes/?symbols=${symbol}`);
        const q = data[0];
        if (!alive || !q) return;
        const p = Number(q.current_price);
        if (lastPrice.current !== null && p !== lastPrice.current) {
          setFlash(p > lastPrice.current ? "up" : "down");
          setTimeout(() => alive && setFlash(""), 450);
        }
        lastPrice.current = p;
        setQuote(q);
      } catch { /* reintenta en el siguiente segundo */ }
    };
    load();
    const id = setInterval(load, 1000);
    return () => { alive = false; clearInterval(id); };
  }, [symbol]);

  // Avisar cuando una posición se cierra sola (TP, SL o cierre forzoso)
  useEffect(() => {
    if (!openPos.data) return;
    const ids = new Set(openPos.data.map((p) => p.id));
    if (knownOpen.current) {
      const gone = [...knownOpen.current].filter((id) => !ids.has(id));
      if (gone.length) {
        api.get("/positions/?status=CLOSED").then(({ data }) => {
          closedPos.setData(data);
          data.filter((p) => gone.includes(p.id) && p.close_reason !== "MANUAL").forEach((p) => {
            toast(`${p.close_reason_label} en ${p.symbol}: ${signed(p.realized_pnl)}`, Number(p.realized_pnl) >= 0 ? "success" : "error");
          });
        });
        account.reload(true);
      }
    }
    knownOpen.current = ids;
  }, [openPos.data]); // eslint-disable-line react-hooks/exhaustive-deps

  const refreshAll = useCallback(() => {
    openPos.reload(true);
    closedPos.reload(true);
    account.reload(true);
  }, [openPos, closedPos, account]);

  const q = quote || info.data;
  const pf = account.data?.portfolios?.find((p) => String(p.id) === String(portfolioId));
  const holding = pf?.holdings?.[symbol];

  const priceLines = useMemo(() => {
    const lines = [];
    (openPos.data || []).filter((p) => p.symbol === symbol).forEach((p) => {
      lines.push({ price: Number(p.entry_price), color: "#3c7aa6", title: `${p.side === "LONG" ? "Compra" : "Venta"} 1:${p.leverage}`, width: 2 });
      if (p.take_profit) lines.push({ price: Number(p.take_profit), color: "#23855a", title: "TP", dashed: true });
      if (p.stop_loss) lines.push({ price: Number(p.stop_loss), color: "#c2412d", title: "SL", dashed: true });
    });
    if (holding) {
      lines.push({ price: Number(holding.avg_cost), color: "#6f8a3c", title: "Costo contado" });
      if (holding.take_profit) lines.push({ price: Number(holding.take_profit), color: "#23855a", title: "TP contado", dashed: true });
      if (holding.stop_loss) lines.push({ price: Number(holding.stop_loss), color: "#c2412d", title: "SL contado", dashed: true });
    }
    return lines;
  }, [openPos.data, holding, symbol]);

  const toggleIndicator = (k) => setIndicators((arr) => (arr.includes(k) ? arr.filter((x) => x !== k) : [...arr, k]));
  const positions = (openPos.data || []).filter((p) => !onlySymbol || p.symbol === symbol);
  const totalPnl = (openPos.data || []).reduce((a, p) => a + Number(p.unrealized_pnl || 0), 0);
  const stats = info.data?.stats || {};
  const currentType = TYPES.find((t) => t.v === chartType) || TYPES[0];
  const onToolChange = useCallback((t) => setTool(t), []);
  const onStatus = useCallback((s) => setStatus(s), []);

  return (
    <div className="terminal" onClick={() => menu && setMenu(null)}>
      <header className="term-head">
        <SymbolPicker symbol={symbol} instruments={instruments.data} onPick={(s) => navigate(`/mercado/${s}${portfolioId ? `?portafolio=${portfolioId}` : ""}`)} />
        <div className="term-quote">
          <span className={`term-price ${flash}`}>{q ? price(q.current_price, q.quote_currency) : "—"}</span>
          {q && <Delta value={q.change_pct} pill />}
        </div>
        <div className="term-meta">
          <div><span>Bid</span><strong className="loss">{q ? price(q.bid, q.quote_currency) : "—"}</strong></div>
          <div><span>Ask</span><strong className="gain">{q ? price(q.ask, q.quote_currency) : "—"}</strong></div>
          <div><span>Cierre ant.</span><strong>{q ? price(q.previous_close, q.quote_currency) : "—"}</strong></div>
          <div><span>Apal. máx.</span><strong>1:{q?.max_leverage ?? "—"}</strong></div>
        </div>
        <span className="live-badge"><span className="pulse" /> En vivo</span>
      </header>

      <div className="term-body">
        <section className="term-chart panel">
          <div className="toolbar" onClick={(e) => e.stopPropagation()}>
            <div className="tf-group" role="group" aria-label="Temporalidad">
              {TIMEFRAMES.map((t, i) => (
                <button key={t.v} className={`tb ${tf === t.v ? "on" : ""} ${i === 5 ? "sep" : ""}`} onClick={() => setTf(t.v)}>{t.l}</button>
              ))}
            </div>
            <div className="dd">
              <button className="tb" onClick={() => setMenu(menu === "type" ? null : "type")}>
                <currentType.icon size={15} /> {currentType.l} <ChevronDown size={13} />
              </button>
              {menu === "type" && (
                <div className="dd-menu">
                  {TYPES.map((t) => (
                    <button key={t.v} className={chartType === t.v ? "on" : ""} onClick={() => { setChartType(t.v); setMenu(null); }}>
                      <t.icon size={15} /> {t.l}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="dd">
              <button className="tb" onClick={() => setMenu(menu === "ind" ? null : "ind")}>
                Indicadores {indicators.length > 0 && <span className="count">{indicators.length}</span>} <ChevronDown size={13} />
              </button>
              {menu === "ind" && (
                <div className="dd-menu wide">
                  {INDICATORS.map((i) => (
                    <label key={i.key} className="dd-check">
                      <input type="checkbox" checked={indicators.includes(i.key)} onChange={() => toggleIndicator(i.key)} />
                      <span className="dot" style={{ background: i.color }} /> {i.label}
                    </label>
                  ))}
                </div>
              )}
            </div>
            <div className="tool-group" role="group" aria-label="Herramientas de dibujo">
              <button className={`tb icon ${tool === "cursor" ? "on" : ""}`} title="Cursor" onClick={() => { setTool("cursor"); setStatus(null); }}><MousePointer2 size={15} /></button>
              <button className={`tb icon ${tool === "hline" ? "on" : ""}`} title="Línea horizontal (soporte / resistencia)" onClick={() => { setTool("hline"); setStatus("Haz clic en el precio donde quieres la línea."); }}><Minus size={15} /></button>
              <button className={`tb icon ${tool === "trend" ? "on" : ""}`} title="Línea de tendencia" onClick={() => { setTool("trend"); setStatus("Haz clic en el primer punto de la línea de tendencia."); }}><TrendingUp size={15} /></button>
              <button className="tb icon" title="Borrar dibujos" onClick={() => { chartRef.current?.clearDrawings(); setTool("cursor"); setStatus(null); }}><Eraser size={15} /></button>
              <button className="tb icon" title="Ajustar al contenido" onClick={() => chartRef.current?.fit()}><Expand size={15} /></button>
            </div>
          </div>
          {status && <div className="draw-hint">{status} <button className="btn btn-ghost btn-sm" onClick={() => { setTool("cursor"); setStatus(null); }}>Cancelar</button></div>}
          <TradingChart
            ref={chartRef} symbol={symbol} tf={tf} chartType={chartType} indicators={indicators}
            tool={tool} onToolChange={onToolChange} onStatus={onStatus} priceLines={priceLines} quote={quote}
          />
          <p className="chart-foot">
            Velas intradía en hora de Colombia · el mercado simulado corre 6 veces más rápido que el reloj real · gráficos con{" "}
            <a href="https://www.tradingview.com/lightweight-charts/" target="_blank" rel="noopener noreferrer">Lightweight Charts™</a> de TradingView.
          </p>
        </section>

        <OrderTicket
          key={symbol} quote={q} account={account.data} portfolioId={portfolioId} setPortfolioId={setPortfolioId}
          defaults={{ mode: params.get("modo") === "contado" ? "spot" : "cfd", side: params.get("lado") === "SELL" ? "SELL" : "BUY" }}
          onExecuted={refreshAll}
        />
      </div>

      <section className="panel panel-flush term-bottom">
        <div className="tabs" role="tablist">
          <button className={tab === "positions" ? "on" : ""} onClick={() => setTab("positions")}>
            Posiciones CFD <span className="count">{openPos.data?.length || 0}</span>
            {openPos.data?.length > 0 && <span className={`tab-pnl ${tone(totalPnl)}`}>{signed(totalPnl)}</span>}
          </button>
          <button className={tab === "spot" ? "on" : ""} onClick={() => setTab("spot")}>Contado</button>
          <button className={tab === "history" ? "on" : ""} onClick={() => { setTab("history"); closedPos.reload(true); }}>Historial</button>
          <button className={tab === "news" ? "on" : ""} onClick={() => setTab("news")}>Noticias de {symbol}</button>
          <button className={tab === "info" ? "on" : ""} onClick={() => setTab("info")}>Datos del activo</button>
          {tab === "positions" && (
            <label className="row only-sym"><input type="checkbox" checked={onlySymbol} onChange={(e) => setOnlySymbol(e.target.checked)} /> Solo {symbol}</label>
          )}
        </div>
        <div className="tab-body">
          {tab === "positions" && (
            <>
              {pf?.margin?.open_positions > 0 && <MarginBar m={pf.margin} name={pf.name} />}
              <OpenPositionsTable positions={positions} onChange={refreshAll} />
            </>
          )}
          {tab === "spot" && (
            pf && Object.keys(pf.holdings).length ? (
              <div className="table-wrap">
                <table className="dense">
                  <thead><tr><th>Activo</th><th className="num">Unidades</th><th className="num">Costo prom.</th><th className="num">TP</th><th className="num">SL</th><th /></tr></thead>
                  <tbody>
                    {Object.entries(pf.holdings).map(([sym, h]) => (
                      <tr key={sym}>
                        <td><Link to={`/mercado/${sym}?portafolio=${pf.id}`} className="sym" style={{ color: "inherit" }}>{sym}</Link></td>
                        <td className="num">{qty(h.quantity)}</td>
                        <td className="num">{price(h.avg_cost)}</td>
                        <td className="num gain">{h.take_profit ? price(h.take_profit) : "—"}</td>
                        <td className="num loss">{h.stop_loss ? price(h.stop_loss) : "—"}</td>
                        <td className="num">
                          <button className="btn btn-ghost btn-sm" onClick={async () => {
                            const { data } = await api.get(`/market/quotes/?symbols=${sym}`);
                            setEditHolding({ symbol: sym, price: data[0].current_price, take_profit: h.take_profit, stop_loss: h.stop_loss });
                          }}>TP/SL</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <Empty title="Sin inversiones de contado en este portafolio" />
          )}
          {tab === "history" && <ClosedPositionsTable positions={closedPos.data} />}
          {tab === "news" && <NewsList url={`/market/instruments/${symbol}/news/`} />}
          {tab === "info" && info.data && (
            <div className="info-grid">
              <div>
                <div className="row" style={{ gap: 8, marginBottom: 8 }}>
                  <TypeTag type={info.data.type} /><span className="tag">{info.data.sector}</span><span className="tag">{info.data.country}</span>
                </div>
                <h3 style={{ marginBottom: 6 }}>{info.data.name}</h3>
                <p style={{ fontSize: 14 }}>{info.data.description}</p>
              </div>
              <div className="metrics" style={{ borderTop: 0 }}>
                <Metric label="Hoy" value={<Delta value={stats.returns?.["1D"]} icon={false} />} />
                <Metric label="1 mes" value={<Delta value={stats.returns?.["1M"]} icon={false} />} />
                <Metric label="1 año" value={<Delta value={stats.returns?.["1A"]} icon={false} />} />
                <Metric label="Volatilidad anual" value={pct(stats.volatility_annual, false)} />
                <Metric label="Beta vs. S&P 500" value={number(stats.beta)} />
                <Metric label="Máx. 52 semanas" value={price(stats.high_52w, info.data.quote_currency)} />
                <Metric label="Mín. 52 semanas" value={price(stats.low_52w, info.data.quote_currency)} />
                <Metric label="Apalancamiento máximo" value={`1:${info.data.max_leverage}`} note={info.data.cfd_only ? "Solo CFD" : "Contado o CFD"} />
                <Metric label="Caída máxima 1 año" value={pct(stats.max_drawdown_1y)} />
              </div>
            </div>
          )}
        </div>
      </section>
      {editHolding && pf && <ProtectionModal holding={editHolding} portfolioId={pf.id} onClose={() => setEditHolding(null)} onSaved={refreshAll} />}
    </div>
  );
}

function MarginBar({ m, name }) {
  const level = m.margin_level === null ? null : Number(m.margin_level);
  const width = level === null ? 0 : Math.min(level / 300, 1) * 100;
  const color = level === null ? "var(--sage)" : level < m.stop_out_level * 1.5 ? "var(--loss)" : level < m.margin_call_level * 1.5 ? "var(--wheat)" : "var(--gain)";
  return (
    <div className="margin-bar">
      <div className="row between" style={{ fontSize: 13 }}>
        <span><strong>{name}</strong> · Capital {money(m.equity)} · Margen usado {money(m.margin_used)} · Libre {money(m.free_margin)}</span>
        <span>Nivel de margen <strong style={{ color }}>{level === null ? "—" : `${number(level, 0)} %`}</strong></span>
      </div>
      <div className="furrow" style={{ height: 6, margin: "6px 0 2px" }}><span style={{ width: `${width}%`, background: color }} /></div>
      <div className="muted" style={{ fontSize: 11.5 }}>Aviso bajo {m.margin_call_level} % · cierre forzoso bajo {m.stop_out_level} %</div>
    </div>
  );
}

function SymbolPicker({ symbol, instruments, onPick }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const list = (instruments || []).filter((i) => !q || i.symbol.toLowerCase().includes(q.toLowerCase()) || i.name.toLowerCase().includes(q.toLowerCase()));
  const current = instruments?.find((i) => i.symbol === symbol);
  return (
    <div className="dd" onClick={(e) => e.stopPropagation()}>
      <button className="sym-picker" onClick={() => setOpen(!open)}>
        <span className="sym-big">{symbol}</span>
        <span className="muted">{current?.name}</span>
        <ChevronDown size={16} />
      </button>
      {open && (
        <div className="dd-menu picker">
          <div className="input-group" style={{ margin: 6 }}>
            <Search size={15} className="prefix" />
            <input className="input" autoFocus placeholder="Buscar activo" value={q} onChange={(e) => setQ(e.target.value)} style={{ paddingLeft: 34 }} />
          </div>
          <div className="picker-list">
            {list.map((i) => (
              <button key={i.symbol} onClick={() => { setOpen(false); setQ(""); onPick(i.symbol); }} className={i.symbol === symbol ? "on" : ""}>
                <span><strong>{i.symbol}</strong> <span className="muted">{i.name}</span></span>
                <span className="row" style={{ gap: 8, flexWrap: "nowrap" }}><TypeTag type={i.type} /><span className={tone(i.change_pct)}>{pct(i.change_pct)}</span></span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
