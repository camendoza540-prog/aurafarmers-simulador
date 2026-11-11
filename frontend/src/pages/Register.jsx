import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { errorMessage, fieldErrors } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import AuthSide from "./AuthSide";

const RISK = [
  { v: "conservador", t: "Conservador", d: "Prefiero ganar poco a perder" },
  { v: "moderado", t: "Moderado", d: "Acepto altibajos razonables" },
  { v: "agresivo", t: "Agresivo", d: "Busco crecer aunque haya caídas fuertes" },
];

export default function Register() {
  const { register } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    first_name: "", last_name: "", username: "", email: "", password: "", password2: "",
    risk_profile: "moderado", experience: "ninguna", accept_terms: false,
  });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    try {
      await register(form);
      toast("Cuenta creada. Tienes US$ 100.000 ficticios para empezar.");
      navigate("/", { replace: true });
    } catch (err) {
      const fe = fieldErrors(err);
      setErrors(Object.keys(fe).length ? fe : { general: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  const F = ({ id, label, type = "text", auto, hint }) => (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} type={type} className={`input ${errors[id] ? "invalid" : ""}`} autoComplete={auto}
             value={form[id]} onChange={set(id)} required={id !== "last_name"} />
      {errors[id] ? <span className="error">{errors[id]}</span> : hint && <span className="hint">{hint}</span>}
    </div>
  );

  return (
    <div className="auth">
      <AuthSide />
      <section className="auth-form">
        <form className="auth-card" onSubmit={submit} noValidate>
          <h2>Crea tu cuenta</h2>
          <p className="muted">Recibirás US$ 100.000 ficticios para practicar.</p>
          <div className="grid grid-2" style={{ gap: 12 }}>
            {F({ id: "first_name", label: "Nombre", auto: "given-name" })}
            {F({ id: "last_name", label: "Apellido", auto: "family-name" })}
          </div>
          {F({ id: "username", label: "Usuario", auto: "username", hint: "Entre 3 y 30 caracteres, sin espacios." })}
          {F({ id: "email", label: "Correo", type: "email", auto: "email" })}
          <div className="grid grid-2" style={{ gap: 12 }}>
            {F({ id: "password", label: "Contraseña", type: "password", auto: "new-password", hint: "Mínimo 8 caracteres." })}
            {F({ id: "password2", label: "Repítela", type: "password", auto: "new-password" })}
          </div>
          <div className="field">
            <label>¿Cómo reaccionas ante el riesgo?</label>
            <div className="stack" style={{ gap: 8 }}>
              {RISK.map((r) => (
                <label key={r.v} className={`quiz-opt ${form.risk_profile === r.v ? "sel" : ""}`} style={{ marginTop: 0 }}>
                  <input type="radio" name="risk" checked={form.risk_profile === r.v} onChange={() => setForm({ ...form, risk_profile: r.v })} />
                  <span><strong>{r.t}</strong> <span className="muted">— {r.d}</span></span>
                </label>
              ))}
            </div>
          </div>
          <div className="field">
            <label htmlFor="exp">Experiencia invirtiendo</label>
            <select id="exp" className="input" value={form.experience} onChange={set("experience")}>
              <option value="ninguna">Ninguna</option>
              <option value="basica">Básica</option>
              <option value="intermedia">Intermedia</option>
              <option value="avanzada">Avanzada</option>
            </select>
          </div>
          <div className="field">
            <label className={`check-line ${errors.accept_terms ? "invalid" : ""}`}>
              <input id="accept_terms" type="checkbox" checked={form.accept_terms}
                     onChange={(e) => setForm({ ...form, accept_terms: e.target.checked })} />
              <span>Acepto los <Link to="/legal#terminos" target="_blank" rel="noopener">términos y condiciones</Link> y autorizo el tratamiento de mis datos personales según la <Link to="/legal#privacidad" target="_blank" rel="noopener">política de datos</Link> (Ley 1581 de 2012).</span>
            </label>
            {errors.accept_terms && <span className="error">{errors.accept_terms}</span>}
          </div>
          {errors.general && <p className="loss">{errors.general}</p>}
          <button className="btn btn-primary btn-block" disabled={busy}>{busy ? "Creando cuenta…" : "Crear cuenta"}</button>
          <p style={{ marginTop: 16, fontSize: 14 }}>¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link></p>
          <p className="legal-links"><Link to="/legal#terminos">Términos y condiciones</Link> · <Link to="/legal#privacidad">Política de datos</Link></p>
        </form>
      </section>
    </div>
  );
}
