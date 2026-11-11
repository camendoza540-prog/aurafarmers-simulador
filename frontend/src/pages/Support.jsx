import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ChevronDown, Headphones, LifeBuoy, Plus, Search, Send } from "lucide-react";
import api, { errorMessage, fieldErrors } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import usePolling from "../hooks/usePolling";
import Avatar from "../components/Avatar";
import { Empty, Loader } from "../components/Feedback";
import { dateTime } from "../utils/format";

const STATUS_CLASS = { open: "tag-etf", answered: "tag-alcista", closed: "" };

export default function Support() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const staff = user.is_staff;
  const [filter, setFilter] = useState(staff ? "open" : "");
  const list = usePolling(`/support/tickets/${filter ? `?status=${filter}` : ""}`, 8000);
  const faq = usePolling("/support/faq/");
  const active = params.get("ticket");
  const creating = params.get("nuevo") === "1";

  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>{staff ? "Bandeja de soporte" : "Soporte"}</h1>
          <p>{staff
            ? "Responde las solicitudes de los usuarios. Los tickets respondidos le aparecen al usuario con una notificación."
            : "¿Tienes una duda sobre la plataforma? Revisa las preguntas frecuentes o escribe al equipo de soporte."}</p>
        </div>
        {!staff && <button className="btn btn-primary" onClick={() => setParams({ nuevo: "1" })}><Plus size={16} /> Nueva solicitud</button>}
      </div>

      {!staff && !active && !creating && faq.data && <Faq items={faq.data.faq} onAsk={() => setParams({ nuevo: "1" })} />}

      <div className="support-layout">
        <aside className="panel panel-flush">
          <div className="panel-head" style={{ paddingBottom: 10 }}>
            <h2>{staff ? "Tickets" : "Mis solicitudes"}</h2>
            <select className="input" style={{ width: "auto", padding: "6px 10px" }} value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filtrar por estado">
              <option value="">Todos</option>
              <option value="open">Esperando respuesta</option>
              <option value="answered">Respondidos</option>
              <option value="closed">Cerrados</option>
            </select>
          </div>
          {!list.data ? <Loader /> : list.data.length === 0 ? (
            <Empty title="Sin solicitudes">{staff ? "No hay tickets en este estado." : "Cuando escribas al soporte, tus solicitudes aparecerán aquí."}</Empty>
          ) : (
            <div className="ticket-list">
              {list.data.map((t) => (
                <button key={t.id} className={`ticket-item ${String(t.id) === active ? "on" : ""}`} onClick={() => setParams({ ticket: t.id })}>
                  <div className="row between" style={{ flexWrap: "nowrap" }}>
                    <strong className="ellipsis">#{t.id} · {t.subject}</strong>
                    {!staff && !t.user_seen && <span className="badge">Nueva respuesta</span>}
                  </div>
                  <div className="row between" style={{ marginTop: 4 }}>
                    <span className={`tag ${STATUS_CLASS[t.status]}`}>{t.status_label}</span>
                    <span className="muted" style={{ fontSize: 12 }}>{dateTime(t.updated_at)}</span>
                  </div>
                  {staff && <div className="muted" style={{ fontSize: 12.5, marginTop: 4 }}>{t.user.name} · {t.category_label}</div>}
                  <div className="muted ellipsis" style={{ fontSize: 12.5, marginTop: 2 }}>{t.last_message}</div>
                </button>
              ))}
            </div>
          )}
        </aside>

        <section className="panel">
          {creating ? <NewTicket categories={faq.data?.categories || []} onCreated={(t) => { list.reload(true); setParams({ ticket: t.id }); }} onCancel={() => setParams({})} />
            : active ? <Thread id={active} staff={staff} onChange={() => list.reload(true)} key={active} />
            : (
              <div className="empty">
                <LifeBuoy size={36} color="var(--pine)" />
                <h3 style={{ marginTop: 10 }}>{staff ? "Selecciona un ticket para responder" : "Estamos para ayudarte"}</h3>
                <p>{staff ? "Los tickets en espera aparecen primero." : "Selecciona una solicitud a la izquierda o crea una nueva. Te respondemos en el mismo hilo."}</p>
                {!staff && <button className="btn btn-primary" onClick={() => setParams({ nuevo: "1" })}>Escribir al soporte</button>}
              </div>
            )}
        </section>
      </div>
    </div>
  );
}

function Faq({ items, onAsk }) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(null);
  const shown = items.filter((f) => !q || (f.q + f.a).toLowerCase().includes(q.toLowerCase()));
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Preguntas frecuentes</h2>
        <div className="input-group" style={{ width: 280 }}>
          <Search size={15} className="prefix" />
          <input className="input" placeholder="Buscar en las preguntas" value={q} onChange={(e) => setQ(e.target.value)} style={{ paddingLeft: 34 }} />
        </div>
      </div>
      <div className="faq">
        {shown.map((f, i) => (
          <div key={f.q} className={`faq-item ${open === i ? "open" : ""}`}>
            <button onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i}>
              <span>{f.q}</span><ChevronDown size={18} />
            </button>
            {open === i && <p>{f.a}</p>}
          </div>
        ))}
        {shown.length === 0 && <p className="muted">No encontramos esa pregunta. <button className="btn btn-ghost btn-sm" onClick={onAsk}>Escríbele al soporte</button></p>}
      </div>
    </section>
  );
}

function NewTicket({ categories, onCreated, onCancel }) {
  const toast = useToast();
  const [form, setForm] = useState({ subject: "", category: "operaciones", body: "" });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    try {
      const { data } = await api.post("/support/tickets/", form);
      toast(`Solicitud #${data.id} enviada. Te responderemos en este hilo.`);
      onCreated(data);
    } catch (err) {
      const fe = fieldErrors(err);
      setErrors(Object.keys(fe).length ? fe : { general: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  };
  return (
    <form onSubmit={submit}>
      <h2 style={{ marginBottom: 14 }}>Nueva solicitud de soporte</h2>
      <div className="field">
        <label htmlFor="st-c">¿Sobre qué es tu consulta?</label>
        <select id="st-c" className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
          {categories.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
      </div>
      <div className="field">
        <label htmlFor="st-s">Asunto</label>
        <input id="st-s" className={`input ${errors.subject ? "invalid" : ""}`} maxLength={120} value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} placeholder="Ej.: Mi posición se cerró sola" />
        {errors.subject && <span className="error">{errors.subject}</span>}
      </div>
      <div className="field">
        <label htmlFor="st-b">Cuéntanos qué pasó</label>
        <textarea id="st-b" className={`input ${errors.body ? "invalid" : ""}`} rows={6} maxLength={4000} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })}
                  placeholder="Describe lo que intentabas hacer, qué esperabas y qué ocurrió. Si es sobre un activo, menciona su símbolo." />
        {errors.body && <span className="error">{errors.body}</span>}
      </div>
      {errors.general && <p className="loss">{errors.general}</p>}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancelar</button>
        <button className="btn btn-primary" disabled={busy}><Send size={15} /> {busy ? "Enviando…" : "Enviar al soporte"}</button>
      </div>
    </form>
  );
}

function Thread({ id, staff, onChange }) {
  const toast = useToast();
  const [t, setT] = useState(null);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = () => api.get(`/support/tickets/${id}/`).then(({ data }) => { if (alive) { setT(data); onChange(); } }).catch(() => {});
    load();
    const iv = setInterval(() => document.visibilityState === "visible" && load(), 6000);
    return () => { alive = false; clearInterval(iv); };
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const send = async () => {
    if (!reply.trim()) return;
    setBusy(true);
    try {
      const { data } = await api.post(`/support/tickets/${id}/messages/`, { body: reply });
      setT(data);
      setReply("");
      onChange();
    } catch (e) {
      toast(errorMessage(e), "error");
    } finally {
      setBusy(false);
    }
  };
  const close = async () => {
    const { data } = await api.post(`/support/tickets/${id}/close/`);
    setT(data);
    onChange();
    toast("Solicitud cerrada. ¡Gracias por escribirnos!");
  };

  if (!t) return <Loader />;
  return (
    <div className="thread">
      <header className="row between" style={{ alignItems: "flex-start", marginBottom: 12 }}>
        <div>
          <h2>#{t.id} · {t.subject}</h2>
          <div className="muted" style={{ fontSize: 13 }}>{t.category_label} · abierto el {dateTime(t.created_at)}{staff && <> · por <strong>{t.user.name}</strong> (@{t.user.username})</>}</div>
        </div>
        <div className="row">
          <span className={`tag ${STATUS_CLASS[t.status]}`}>{t.status_label}</span>
          {t.status !== "closed" && <button className="btn btn-ghost btn-sm" onClick={close}>{staff ? "Cerrar ticket" : "Marcar como resuelto"}</button>}
        </div>
      </header>
      <div className="thread-msgs">
        {t.messages.map((m) => (
          <div key={m.id} className={`tmsg ${m.author.staff ? "staff" : ""}`}>
            {m.author.staff
              ? <span className="avatar support-avatar"><Headphones size={18} /></span>
              : <Avatar name={m.author.name} url={m.author.avatar_url} size={36} />}
            <div className="tmsg-body">
              <div className="tmsg-head"><strong>{m.author.name}</strong><span className="muted">{dateTime(m.created_at)}</span></div>
              <p>{m.body}</p>
            </div>
          </div>
        ))}
      </div>
      {t.status !== "closed" ? (
        <div className="composer" style={{ marginTop: 12 }}>
          <textarea className="input" rows={3} placeholder={staff ? "Escribe la respuesta para el usuario…" : "Agrega más detalles o responde al equipo…"} value={reply} onChange={(e) => setReply(e.target.value)} />
          <button className="btn btn-primary" onClick={send} disabled={busy || !reply.trim()}><Send size={15} /> {staff ? "Responder" : "Enviar"}</button>
        </div>
      ) : <p className="muted" style={{ marginTop: 12 }}>Esta solicitud está cerrada. Si necesitas más ayuda, abre una nueva.</p>}
    </div>
  );
}
