import { useState } from "react";
import api, { errorMessage, fieldErrors } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import Modal from "../components/Modal";
import { money } from "../utils/format";

export const COLORS = ["pine", "gold", "clay", "sky", "plum", "moss"];

/** Crear o editar un portafolio. */
export default function PortfolioForm({ portfolio, onClose, onSaved }) {
  const { user, refreshUser } = useAuth();
  const toast = useToast();
  const editing = !!portfolio;
  const [form, setForm] = useState({
    name: portfolio?.name || "",
    description: portfolio?.description || "",
    color: portfolio?.color || "pine",
    initial_deposit: "10000",
  });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const cash = Number(user?.profile?.cash_balance || 0);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    try {
      const body = { name: form.name, description: form.description, color: form.color };
      const { data } = editing
        ? await api.patch(`/portfolios/${portfolio.id}/`, body)
        : await api.post("/portfolios/", { ...body, initial_deposit: form.initial_deposit || 0 });
      toast(editing ? "Portafolio actualizado." : `Portafolio «${data.name}» creado.`);
      refreshUser();
      onSaved?.(data);
      onClose();
    } catch (err) {
      const fe = fieldErrors(err);
      setErrors(fe.detail ? { general: fe.detail } : Object.keys(fe).length ? fe : { general: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={editing ? "Editar portafolio" : "Nuevo portafolio"} onClose={onClose}>
      <form onSubmit={submit}>
        <div className="field">
          <label htmlFor="pn">Nombre</label>
          <input id="pn" className={`input ${errors.name ? "invalid" : ""}`} value={form.name} autoFocus maxLength={60}
                 onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Ej.: Largo plazo, Tecnología, Jubilación" required />
          {errors.name && <span className="error">{errors.name}</span>}
        </div>
        <div className="field">
          <label htmlFor="pd">Estrategia (opcional)</label>
          <textarea id="pd" className="input" rows={2} maxLength={240} value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="¿Qué buscas con este portafolio?" />
        </div>
        <div className="field">
          <label>Color</label>
          <div className="row">
            {COLORS.map((c) => (
              <button type="button" key={c} aria-label={c} className={`swatch color-${c} ${form.color === c ? "on" : ""}`} onClick={() => setForm({ ...form, color: c })} />
            ))}
          </div>
        </div>
        {!editing && (
          <div className="field">
            <label htmlFor="pi">Aporte inicial</label>
            <div className="input-group">
              <span className="prefix">US$</span>
              <input id="pi" type="number" min="0" step="any" className="input" value={form.initial_deposit}
                     onChange={(e) => setForm({ ...form, initial_deposit: e.target.value })} />
            </div>
            <span className="hint">Se transfiere desde tu efectivo disponible: {money(cash)}.</span>
          </div>
        )}
        {errors.general && <p className="loss" style={{ fontSize: 14 }}>{errors.general}</p>}
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary" disabled={busy}>{busy ? "Guardando…" : editing ? "Guardar cambios" : "Crear portafolio"}</button>
        </div>
      </form>
    </Modal>
  );
}
