import { useState } from "react";
import api, { errorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import { price as fmtPrice } from "../utils/format";
import Modal from "./Modal";

/**
 * Editar take profit / stop loss de una posición CFD (`position`) o de una posición de contado
 * (`holding` + `portfolioId`).
 */
export default function ProtectionModal({ position, holding, portfolioId, onClose, onSaved }) {
  const toast = useToast();
  const target = position || holding;
  const side = position ? position.side : "LONG";
  const current = Number(position ? position.current_price : holding.price);
  const [tp, setTp] = useState(target.take_profit ?? "");
  const [sl, setSl] = useState(target.stop_loss ?? "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const up = side === "LONG";

  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    const body = { take_profit: tp === "" ? null : tp, stop_loss: sl === "" ? null : sl };
    try {
      if (position) await api.patch(`/positions/${position.id}/`, body);
      else await api.post(`/portfolios/${portfolioId}/holdings/${holding.symbol}/protection/`, body);
      toast("Protección actualizada.");
      onSaved?.();
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={`Take profit y stop loss · ${target.symbol}`} onClose={onClose} width={440}>
      <form onSubmit={save}>
        <p className="muted" style={{ fontSize: 14 }}>
          Precio actual <strong style={{ color: "var(--ink)" }}>{fmtPrice(current)}</strong>.
          {up ? " El take profit va por encima y el stop loss por debajo." : " En corto, el take profit va por debajo y el stop loss por encima."}
          {" "}Déjalo vacío para quitarlo.
        </p>
        <div className="grid grid-2" style={{ gap: 12 }}>
          <div className="field">
            <label htmlFor="pm-tp" className="gain">Take profit</label>
            <input id="pm-tp" className="input" type="number" step="any" min="0" value={tp} onChange={(e) => setTp(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="pm-sl" className="loss">Stop loss</label>
            <input id="pm-sl" className="input" type="number" step="any" min="0" value={sl} onChange={(e) => setSl(e.target.value)} />
          </div>
        </div>
        {error && <p className="loss" style={{ fontSize: 14 }}>{error}</p>}
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary" disabled={busy}>{busy ? "Guardando…" : "Guardar"}</button>
        </div>
      </form>
    </Modal>
  );
}
