import { useRef, useState } from "react";
import { Camera, CheckCircle2, Eye, EyeOff, ShieldCheck, Trash2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import api, { errorMessage, fieldErrors, tokens } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import Avatar from "../components/Avatar";
import { Metric } from "../components/Feedback";
import Modal from "../components/Modal";
import { dateLong, money, pct, tone } from "../utils/format";

function strength(pw) {
  let s = 0;
  if (pw.length >= 8) s++;
  if (pw.length >= 12) s++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) s++;
  if (/\d/.test(pw)) s++;
  if (/[^A-Za-z0-9]/.test(pw)) s++;
  return [
    { label: "Muy débil", color: "var(--loss)" }, { label: "Débil", color: "var(--loss)" },
    { label: "Aceptable", color: "var(--wheat)" }, { label: "Buena", color: "var(--gain)" },
    { label: "Fuerte", color: "var(--gain)" }, { label: "Muy fuerte", color: "var(--gain)" },
  ][s];
}

export default function Profile() {
  const { user, refreshUser, logout } = useAuth();
  const navigate = useNavigate();
  const [delOpen, setDelOpen] = useState(false);
  const [del, setDel] = useState({ password: "", confirm: "" });
  const [delErrors, setDelErrors] = useState({});
  const [deleting, setDeleting] = useState(false);
  const toast = useToast();
  const fileRef = useRef(null);
  const p = user.profile;
  const [form, setForm] = useState({
    first_name: user.first_name, last_name: user.last_name, email: user.email,
    description: p.description || "", show_in_ranking: p.show_in_ranking,
    risk_profile: p.risk_profile, experience: p.experience, bio: p.bio || "",
  });
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [pw, setPw] = useState({ current_password: "", new_password: "", new_password2: "" });
  const [pwErrors, setPwErrors] = useState({});
  const [pwOk, setPwOk] = useState(false);
  const [showPw, setShowPw] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [confirm, setConfirm] = useState("");
  const nw = user.net_worth;
  const name = `${user.first_name} ${user.last_name}`.trim() || user.username;
  const st = strength(pw.new_password);

  const save = async (e) => {
    e.preventDefault();
    setErrors({});
    setSaving(true);
    try {
      const { first_name, last_name, email, ...prof } = form;
      await api.patch("/auth/me/", { first_name, last_name, email, profile: prof });
      await refreshUser();
      toast("Perfil actualizado.");
    } catch (err) {
      setErrors(fieldErrors(err));
    } finally {
      setSaving(false);
    }
  };

  const upload = async (file) => {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { toast("La imagen no puede superar 5 MB.", "error"); return; }
    setUploading(true);
    const fd = new FormData();
    fd.append("avatar", file);
    try {
      await api.post("/auth/avatar/", fd, { headers: { "Content-Type": "multipart/form-data" } });
      await refreshUser();
      toast("Foto de perfil actualizada.");
    } catch (err) {
      toast(errorMessage(err), "error");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const removeAvatar = async () => {
    await api.delete("/auth/avatar/");
    await refreshUser();
    toast("Foto eliminada.");
  };

  const changePw = async (e) => {
    e.preventDefault();
    setPwErrors({});
    setPwOk(false);
    if (pw.new_password !== pw.new_password2) {
      setPwErrors({ new_password2: "Las contraseñas nuevas no coinciden." });
      return;
    }
    try {
      const { data } = await api.post("/auth/change-password/", pw);
      tokens.set(data.tokens);
      setPw({ current_password: "", new_password: "", new_password2: "" });
      setPwOk(true);
      toast(data.detail);
    } catch (err) {
      const fe = fieldErrors(err);
      setPwErrors(Object.keys(fe).length ? fe : { general: errorMessage(err) });
    }
  };

  const deleteAccount = async () => {
    setDeleting(true);
    setDelErrors({});
    try {
      await api.post("/auth/delete-account/", del);
      logout();
      toast("Tu cuenta y todos tus datos fueron eliminados.");
      navigate("/login", { replace: true });
    } catch (err) {
      const fe = fieldErrors(err);
      setDelErrors(Object.keys(fe).length ? fe : { general: errorMessage(err) });
    } finally {
      setDeleting(false);
    }
  };

  const reset = async () => {
    try {
      const { data } = await api.post("/auth/reset/", { confirm });
      await refreshUser();
      setResetOpen(false);
      setConfirm("");
      toast(data.detail);
    } catch (err) {
      toast(errorMessage(err), "error");
    }
  };

  const PwInput = ({ id, label, auto }) => (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="input-group">
        <input id={id} type={showPw ? "text" : "password"} autoComplete={auto} className={`input ${pwErrors[id] ? "invalid" : ""}`}
               value={pw[id]} onChange={(e) => { setPw({ ...pw, [id]: e.target.value }); setPwOk(false); }} style={{ paddingRight: 42 }} />
        <button type="button" className="icon-btn pw-eye" onClick={() => setShowPw(!showPw)} aria-label={showPw ? "Ocultar contraseñas" : "Mostrar contraseñas"}>
          {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
      {pwErrors[id] && <span className="error">{pwErrors[id]}</span>}
    </div>
  );

  return (
    <div className="stack">
      <section className="profile-hero panel">
        <div className="avatar-edit">
          <Avatar name={name} url={p.avatar_url} size={104} />
          <button className="avatar-btn" onClick={() => fileRef.current?.click()} disabled={uploading} aria-label="Cambiar foto de perfil">
            <Camera size={16} />
          </button>
          <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={(e) => upload(e.target.files?.[0])} />
        </div>
        <div style={{ flex: 1, minWidth: 220 }}>
          <h1>{name}</h1>
          <div className="muted">@{user.username} · miembro desde {dateLong(user.date_joined)}</div>
          <p style={{ margin: "10px 0 0", maxWidth: "60ch" }}>{p.description || <span className="muted">Aún no has escrito una descripción. Cuéntale a la comunidad qué tipo de inversionista eres.</span>}</p>
          <div className="row" style={{ marginTop: 12 }}>
            <button className="btn btn-secondary btn-sm" onClick={() => fileRef.current?.click()} disabled={uploading}><Camera size={14} /> {uploading ? "Subiendo…" : p.avatar_url ? "Cambiar foto" : "Subir foto"}</button>
            {p.avatar_url && <button className="btn btn-ghost btn-sm" onClick={removeAvatar}><Trash2 size={14} /> Quitar foto</button>}
          </div>
        </div>
        <div className="metrics profile-metrics">
          <Metric label="Patrimonio" value={money(nw.total)} />
          <Metric label="Ganancia" value={pct(nw.gain_pct)} className={tone(nw.gain_pct)} />
          <Metric label="Efectivo" value={money(nw.cash)} />
        </div>
      </section>

      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <form className="panel" onSubmit={save}>
          <h2 style={{ marginBottom: 14 }}>Información pública</h2>
          <div className="grid grid-2" style={{ gap: 12 }}>
            <div className="field"><label htmlFor="fn">Nombre</label><input id="fn" className="input" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></div>
            <div className="field"><label htmlFor="ln">Apellido</label><input id="ln" className="input" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></div>
          </div>
          <div className="field">
            <div className="row between"><label htmlFor="desc">Descripción breve</label><span className="muted" style={{ fontSize: 12 }}>{form.description.length}/400</span></div>
            <textarea id="desc" className="input" rows={3} maxLength={400} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                      placeholder="Ej.: Estudiante de Ingeniería de Sistemas. Invierto a largo plazo en ETFs y me interesa el mercado colombiano." />
            <span className="hint">La ven tus amigos y quienes te encuentren en la comunidad.</span>
          </div>
          <label className="row" style={{ gap: 8, marginBottom: 14, fontSize: 14, cursor: "pointer" }}>
            <input type="checkbox" checked={form.show_in_ranking} onChange={(e) => setForm({ ...form, show_in_ranking: e.target.checked })} />
            Mostrar mi nombre y resultados en el ranking de inversionistas
          </label>
          <div className="field">
            <label htmlFor="em">Correo</label>
            <input id="em" type="email" className={`input ${errors.email ? "invalid" : ""}`} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            {errors.email && <span className="error">{errors.email}</span>}
          </div>
          <h3 style={{ margin: "8px 0 12px" }}>Preferencias de inversión</h3>
          <div className="grid grid-2" style={{ gap: 12 }}>
            <div className="field">
              <label htmlFor="rp">Perfil de riesgo</label>
              <select id="rp" className="input" value={form.risk_profile} onChange={(e) => setForm({ ...form, risk_profile: e.target.value })}>
                <option value="conservador">Conservador</option><option value="moderado">Moderado</option><option value="agresivo">Agresivo</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="ex">Experiencia</label>
              <select id="ex" className="input" value={form.experience} onChange={(e) => setForm({ ...form, experience: e.target.value })}>
                <option value="ninguna">Ninguna</option><option value="basica">Básica</option><option value="intermedia">Intermedia</option><option value="avanzada">Avanzada</option>
              </select>
            </div>
          </div>
          <div className="field">
            <label htmlFor="bio">Objetivo de inversión</label>
            <input id="bio" className="input" maxLength={240} value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} placeholder="Ej.: ahorrar para un posgrado en cinco años" />
          </div>
          <button className="btn btn-primary" disabled={saving}>{saving ? "Guardando…" : "Guardar cambios"}</button>
        </form>

        <div className="stack">
          <form className="panel" onSubmit={changePw}>
            <h2 style={{ marginBottom: 6 }}>Seguridad</h2>
            <p className="muted" style={{ fontSize: 14, marginBottom: 14 }}>Cambia tu contraseña. Usa al menos 8 caracteres y evita datos personales.</p>
            {PwInput({ id: "current_password", label: "Contraseña actual", auto: "current-password" })}
            {PwInput({ id: "new_password", label: "Nueva contraseña", auto: "new-password" })}
            {pw.new_password && (
              <div className="pw-meter">
                <div className="furrow" style={{ height: 6, margin: 0 }}><span style={{ width: `${(["Muy débil", "Débil", "Aceptable", "Buena", "Fuerte", "Muy fuerte"].indexOf(st.label) + 1) / 6 * 100}%`, background: st.color }} /></div>
                <span style={{ color: st.color }}>{st.label}</span>
              </div>
            )}
            {PwInput({ id: "new_password2", label: "Confirma la nueva contraseña", auto: "new-password" })}
            {pwErrors.general && <p className="loss" style={{ fontSize: 14 }}>{pwErrors.general}</p>}
            {pwOk && <p className="pw-ok"><CheckCircle2 size={16} /> Contraseña actualizada. Úsala la próxima vez que inicies sesión.</p>}
            <button className="btn btn-primary" disabled={!pw.current_password || !pw.new_password || !pw.new_password2}>Cambiar contraseña</button>
          </form>

          <section className="panel">
            <h2 style={{ marginBottom: 8 }}>Reiniciar simulación</h2>
            <p className="muted" style={{ fontSize: 14 }}>Borra portafolios, posiciones, ahorros y escenarios, y vuelve a empezar con {money(p.initial_balance, true)}. Tus amigos, mensajes y lecciones se conservan.</p>
            <button className="btn btn-danger" onClick={() => setResetOpen(true)}>Reiniciar desde cero</button>
          </section>

          <section className="panel">
            <h2 style={{ marginBottom: 8 }}>Privacidad y datos</h2>
            <p className="privacy-line"><ShieldCheck size={16} />
              {p.terms_accepted_at
                ? <span>Autorizaste el tratamiento de tus datos (versión {p.terms_version}) el {dateLong(p.terms_accepted_at)}.</span>
                : <span>Aún no has aceptado la versión vigente de los términos.</span>}
            </p>
            <p className="muted" style={{ fontSize: 14 }}>Puedes actualizar tus datos en este perfil. Consulta los <Link to="/legal#terminos">términos y condiciones</Link> y la <Link to="/legal#privacidad">política de datos</Link>.</p>
            <button className="btn btn-danger" onClick={() => setDelOpen(true)}><Trash2 size={16} /> Eliminar mi cuenta</button>
          </section>
        </div>
      </div>

      {delOpen && (
        <Modal title="Eliminar mi cuenta" onClose={() => setDelOpen(false)}>
          <p>Se borrarán de forma <strong>definitiva</strong> tu cuenta y toda tu información: perfil, foto, portafolios, ahorros, simulaciones, mensajes, solicitudes de soporte y progreso. Esta acción no se puede deshacer.</p>
          <div className="field">
            <label htmlFor="del-pw">Tu contraseña</label>
            <input id="del-pw" type="password" className={`input ${delErrors.password ? "invalid" : ""}`} autoComplete="current-password"
                   value={del.password} onChange={(e) => setDel({ ...del, password: e.target.value })} />
            {delErrors.password && <span className="error">{delErrors.password}</span>}
          </div>
          <div className="field">
            <label htmlFor="del-confirm">Escribe <strong>ELIMINAR</strong> para confirmar</label>
            <input id="del-confirm" className={`input ${delErrors.confirm ? "invalid" : ""}`} value={del.confirm} onChange={(e) => setDel({ ...del, confirm: e.target.value })} />
            {delErrors.confirm && <span className="error">{delErrors.confirm}</span>}
          </div>
          {delErrors.general && <p className="loss" style={{ fontSize: 14 }}>{delErrors.general}</p>}
          <div className="row" style={{ justifyContent: "flex-end", marginTop: 14 }}>
            <button className="btn btn-ghost" onClick={() => setDelOpen(false)}>Cancelar</button>
            <button className="btn btn-sell" disabled={!del.password || del.confirm.trim().toUpperCase() !== "ELIMINAR" || deleting} onClick={deleteAccount}>
              {deleting ? "Eliminando…" : "Eliminar definitivamente"}
            </button>
          </div>
        </Modal>
      )}

      {resetOpen && (
        <Modal title="Reiniciar simulación" onClose={() => setResetOpen(false)}>
          <p>Esta acción elimina toda tu actividad de inversión y no se puede deshacer. Escribe <strong>REINICIAR</strong> para confirmar.</p>
          <input className="input" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoFocus />
          <div className="row" style={{ justifyContent: "flex-end", marginTop: 14 }}>
            <button className="btn btn-ghost" onClick={() => setResetOpen(false)}>Cancelar</button>
            <button className="btn btn-sell" disabled={confirm !== "REINICIAR"} onClick={reset}>Reiniciar</button>
          </div>
        </Modal>
      )}
    </div>
  );
}
