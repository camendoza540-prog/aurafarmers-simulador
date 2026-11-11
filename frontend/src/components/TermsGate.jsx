import { useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { TERMS_VERSION } from "../legal";

/** Cuentas creadas antes de la versión vigente: deben aceptarla para seguir (Ley 1581). */
export default function TermsGate() {
  const { user, refreshUser, logout } = useAuth();
  const [ok, setOk] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  if (!user || user.profile?.terms_current !== false) return null;

  const accept = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post("/auth/accept-terms/", { accept: true });
      await refreshUser();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="gate-title">
      <div className="modal terms-gate">
        <ShieldCheck size={32} className="gate-icon" />
        <h2 id="gate-title">Actualizamos nuestros términos</h2>
        <p className="muted">Para seguir usando Aura Farmers necesitamos que aceptes los términos y condiciones y que autorices el tratamiento de tus datos personales (versión {TERMS_VERSION}).</p>
        <p style={{ fontSize: 14 }}>Léelos en <Link to="/legal#terminos" target="_blank" rel="noopener">términos y condiciones</Link> y <Link to="/legal#privacidad" target="_blank" rel="noopener">política de datos</Link>.</p>
        <label className="check-line">
          <input type="checkbox" checked={ok} onChange={(e) => setOk(e.target.checked)} />
          <span>Acepto los términos y condiciones y autorizo el tratamiento de mis datos personales según la política (Ley 1581 de 2012).</span>
        </label>
        {error && <p className="loss" style={{ fontSize: 14 }}>{error}</p>}
        <div className="row" style={{ justifyContent: "flex-end", marginTop: 16 }}>
          <button className="btn btn-ghost" onClick={logout}>Cerrar sesión</button>
          <button className="btn btn-primary" disabled={!ok || busy} onClick={accept}>{busy ? "Guardando…" : "Aceptar y continuar"}</button>
        </div>
      </div>
    </div>
  );
}
