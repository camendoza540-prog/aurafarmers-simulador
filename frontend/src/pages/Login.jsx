import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { errorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";
import AuthSide from "./AuthSide";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(form.username.trim(), form.password);
      navigate(location.state?.from || "/", { replace: true });
    } catch (err) {
      setError(err?.response?.status === 401 ? "Usuario o contraseña incorrectos." : errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth">
      <AuthSide />
      <section className="auth-form">
        <form className="auth-card" onSubmit={submit}>
          <h2>Inicia sesión</h2>
          <p className="muted">Continúa donde dejaste tu simulación.</p>
          <div className="field">
            <label htmlFor="u">Usuario</label>
            <input id="u" className="input" autoComplete="username" autoFocus value={form.username}
                   onChange={(e) => setForm({ ...form, username: e.target.value })} required />
          </div>
          <div className="field">
            <label htmlFor="p">Contraseña</label>
            <input id="p" type="password" className="input" autoComplete="current-password" value={form.password}
                   onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          </div>
          {error && <p className="loss" style={{ fontSize: 14 }}>{error}</p>}
          <button className="btn btn-primary btn-block" disabled={busy}>{busy ? "Entrando…" : "Entrar"}</button>
          <p style={{ marginTop: 16, fontSize: 14 }}>¿No tienes cuenta? <Link to="/registro">Crea una gratis</Link></p>
          <p className="legal-links"><Link to="/legal#terminos">Términos y condiciones</Link> · <Link to="/legal#privacidad">Política de datos</Link></p>
        </form>
      </section>
    </div>
  );
}
