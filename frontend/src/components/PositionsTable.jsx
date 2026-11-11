import { useState } from "react";
import { Link } from "react-router-dom";
import { Pencil, X } from "lucide-react";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { Empty } from "./Feedback";
import ProtectionModal from "./ProtectionModal";
import { dateTime, money, pct, price, qty, signed, tone } from "../utils/format";

/** Tabla de posiciones CFD abiertas, con edición de TP/SL y cierre. */
export function OpenPositionsTable({ positions, onChange, showPortfolio = true, emptyText }) {
  const toast = useToast();
  const { refreshUser } = useAuth();
  const [editing, setEditing] = useState(null);
  const [closing, setClosing] = useState(null);

  const close = async (p) => {
    setClosing(p.id);
    try {
      const { data } = await api.post(`/positions/${p.id}/close/`);
      toast(`Cerraste ${p.symbol}: ${signed(data.realized_pnl)}`, Number(data.realized_pnl) >= 0 ? "success" : "info");
      refreshUser();
      onChange?.();
    } catch (e) {
      toast(errorMessage(e), "error");
    } finally {
      setClosing(null);
    }
  };

  if (!positions?.length) return <Empty title="Sin posiciones abiertas">{emptyText || "Abre una operación desde la boleta de órdenes."}</Empty>;

  return (
    <div className="table-wrap">
      <table className="dense">
        <thead>
          <tr>
            {showPortfolio && <th>Portafolio</th>}
            <th>Activo</th><th>Dirección</th><th className="num">Unidades</th><th className="num">Apal.</th>
            <th className="num">Entrada</th><th className="num">Actual</th><th className="num">TP</th><th className="num">SL</th>
            <th className="num">Margen</th><th className="num">G/P</th><th />
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => (
            <tr key={p.id}>
              {showPortfolio && <td className="muted">{p.portfolio_name}</td>}
              <td><Link to={`/mercado/${p.symbol}`} className="sym" style={{ color: "inherit" }}>{p.symbol}</Link></td>
              <td><span className={`tag ${p.side === "LONG" ? "tag-alcista" : "tag-bajista"}`}>{p.side === "LONG" ? "Compra" : "Venta"}</span></td>
              <td className="num">{qty(p.quantity)}</td>
              <td className="num">1:{p.leverage}</td>
              <td className="num">{price(p.entry_price, p.quote_currency)}</td>
              <td className="num">{price(p.current_price, p.quote_currency)}</td>
              <td className="num gain">{p.take_profit ? price(p.take_profit, p.quote_currency) : "—"}</td>
              <td className="num loss">{p.stop_loss ? price(p.stop_loss, p.quote_currency) : "—"}</td>
              <td className="num">{money(p.margin)}</td>
              <td className={`num ${tone(p.unrealized_pnl)}`}><strong>{signed(p.unrealized_pnl)}</strong><div style={{ fontSize: 12 }}>{pct(p.pnl_pct_margin)}</div></td>
              <td className="num">
                <div className="row" style={{ gap: 4, justifyContent: "flex-end", flexWrap: "nowrap" }}>
                  <button className="btn btn-ghost btn-sm" onClick={() => setEditing(p)} title="Editar take profit y stop loss"><Pencil size={14} /> TP/SL</button>
                  <button className="btn btn-danger btn-sm" disabled={closing === p.id} onClick={() => close(p)}><X size={14} /> Cerrar</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {editing && <ProtectionModal position={editing} onClose={() => setEditing(null)} onSaved={onChange} />}
    </div>
  );
}

export function ClosedPositionsTable({ positions }) {
  if (!positions?.length) return <Empty title="Aún no has cerrado posiciones" />;
  return (
    <div className="table-wrap">
      <table className="dense">
        <thead>
          <tr><th>Cierre</th><th>Activo</th><th>Dirección</th><th className="num">Unidades</th><th className="num">Apal.</th>
            <th className="num">Entrada</th><th className="num">Salida</th><th>Motivo</th><th className="num">Resultado</th></tr>
        </thead>
        <tbody>
          {positions.map((p) => (
            <tr key={p.id}>
              <td className="muted nowrap">{dateTime(p.closed_at)}</td>
              <td className="sym">{p.symbol}</td>
              <td>{p.side === "LONG" ? "Compra" : "Venta"}</td>
              <td className="num">{qty(p.quantity)}</td>
              <td className="num">1:{p.leverage}</td>
              <td className="num">{price(p.entry_price, p.quote_currency)}</td>
              <td className="num">{price(p.close_price, p.quote_currency)}</td>
              <td><span className={`tag ${p.close_reason === "TP" ? "tag-alcista" : p.close_reason === "SL" || p.close_reason === "STOP_OUT" ? "tag-bajista" : ""}`}>{p.close_reason_label}</span></td>
              <td className={`num ${tone(p.realized_pnl)}`}><strong>{signed(p.realized_pnl)}</strong></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
