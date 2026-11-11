import { Fragment, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Check, MessageCircle, Search, Send, UserMinus, UserPlus, X } from "lucide-react";
import api, { errorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import usePolling from "../hooks/usePolling";
import Avatar from "../components/Avatar";
import { Empty } from "../components/Feedback";
import { pct, tone } from "../utils/format";

const time = (iso) => new Date(iso).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" });
const day = (iso) => new Date(iso).toLocaleDateString("es-CO", { weekday: "long", day: "numeric", month: "long" });

/** Convierte $AAPL en un enlace al terminal de ese activo. */
function renderBody(text) {
  return text.split(/(\$[A-Z]{1,5}\b)/g).map((part, i) =>
    /^\$[A-Z]{1,5}$/.test(part)
      ? <Link key={i} className="ticker-chip" to={`/mercado/${part.slice(1)}`}>{part}</Link>
      : <Fragment key={i}>{part}</Fragment>);
}

export default function Community() {
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const friends = usePolling("/social/friends/", 6000);
  const requests = usePolling("/social/requests/", 8000);
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);
  const active = params.get("chat");

  useEffect(() => {
    if (q.trim().length < 2) { setResults(null); return undefined; }
    const t = setTimeout(async () => {
      try {
        const { data } = await api.get(`/social/users/?q=${encodeURIComponent(q.trim())}`);
        setResults(data);
      } catch { setResults([]); }
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  const refresh = () => { friends.reload(true); requests.reload(true); };

  const sendRequest = async (u) => {
    try {
      const { data } = await api.post("/social/requests/", { to_user: u.id });
      toast(data.detail);
      setResults((r) => r?.map((x) => (x.id === u.id ? { ...x, relationship: { status: data.status === "accepted" ? "friends" : "sent" } } : x)));
      refresh();
    } catch (e) { toast(errorMessage(e), "error"); }
  };
  const respond = async (id, action) => {
    try {
      const { data } = await api.post(`/social/requests/${id}/${action}/`);
      toast(data.detail);
      refresh();
    } catch (e) { toast(errorMessage(e), "error"); }
  };
  const cancel = async (id) => { await api.delete(`/social/requests/${id}/`); refresh(); };

  const incoming = requests.data?.incoming || [];
  const outgoing = requests.data?.outgoing || [];

  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Comunidad</h1>
          <p>Busca a otros inversionistas, envíales una solicitud y, cuando la acepten, conversen y compartan ideas. Escribe <strong>$AAPL</strong> para enlazar un activo.</p>
        </div>
      </div>

      <div className="chat-layout">
        <aside className="panel chat-side">
          <div className="input-group">
            <Search size={15} className="prefix" />
            <input className="input" placeholder="Buscar por nombre o usuario" value={q} onChange={(e) => setQ(e.target.value)} style={{ paddingLeft: 34 }} />
          </div>

          {results && (
            <div className="side-block">
              <h4>Resultados</h4>
              {results.length === 0 && <p className="muted" style={{ fontSize: 13 }}>Nadie coincide con «{q}».</p>}
              {results.map((u) => (
                <div key={u.id} className="person">
                  <Avatar name={u.name} url={u.avatar_url} size={36} />
                  <div className="person-info">
                    <strong>{u.name}</strong>
                    <span className="muted">@{u.username}{u.gain_pct !== undefined && <> · <span className={tone(u.gain_pct)}>{pct(u.gain_pct)}</span></>}</span>
                  </div>
                  {u.relationship.status === "none" && <button className="btn btn-secondary btn-sm" onClick={() => sendRequest(u)}><UserPlus size={14} /> Agregar</button>}
                  {u.relationship.status === "sent" && <span className="tag">Enviada</span>}
                  {u.relationship.status === "received" && <button className="btn btn-primary btn-sm" onClick={() => sendRequest(u)}><Check size={14} /> Aceptar</button>}
                  {u.relationship.status === "friends" && <button className="btn btn-ghost btn-sm" onClick={() => { setParams({ chat: u.id }); setQ(""); }}><MessageCircle size={14} /></button>}
                </div>
              ))}
            </div>
          )}

          {incoming.length > 0 && (
            <div className="side-block">
              <h4>Solicitudes recibidas <span className="count">{incoming.length}</span></h4>
              {incoming.map((r) => (
                <div key={r.id} className="person">
                  <Avatar name={r.user.name} url={r.user.avatar_url} size={36} />
                  <div className="person-info"><strong>{r.user.name}</strong><span className="muted">@{r.user.username}</span></div>
                  <button className="icon-btn ok" onClick={() => respond(r.id, "accept")} aria-label="Aceptar"><Check size={18} /></button>
                  <button className="icon-btn" onClick={() => respond(r.id, "reject")} aria-label="Rechazar"><X size={18} /></button>
                </div>
              ))}
            </div>
          )}

          <div className="side-block">
            <h4>Amigos</h4>
            {friends.data?.length === 0 && <p className="muted" style={{ fontSize: 13 }}>Aún no tienes amigos. Búscalos arriba o desde el Ranking.</p>}
            {friends.data?.map((f) => (
              <button key={f.id} className={`person conv ${String(f.id) === active ? "on" : ""}`} onClick={() => setParams({ chat: f.id })}>
                <Avatar name={f.name} url={f.avatar_url} size={38} />
                <div className="person-info">
                  <strong>{f.name}</strong>
                  <span className="muted ellipsis">{f.last_message ? `${f.last_message.mine ? "Tú: " : ""}${f.last_message.body}` : "Saluda para empezar"}</span>
                </div>
                {f.unread > 0 && <span className="badge">{f.unread}</span>}
              </button>
            ))}
          </div>

          {outgoing.length > 0 && (
            <div className="side-block">
              <h4>Solicitudes enviadas</h4>
              {outgoing.map((r) => (
                <div key={r.id} className="person">
                  <Avatar name={r.user.name} url={r.user.avatar_url} size={30} />
                  <div className="person-info"><strong style={{ fontSize: 13.5 }}>{r.user.name}</strong></div>
                  <button className="btn btn-ghost btn-sm" onClick={() => cancel(r.id)}>Cancelar</button>
                </div>
              ))}
            </div>
          )}
        </aside>

        <section className="panel chat-main">
          {active ? <Conversation userId={active} onChange={refresh} onLeave={() => setParams({})} key={active} /> : (
            <Empty title="Elige una conversación">Selecciona a un amigo a la izquierda. Solo pueden escribirse los usuarios que aceptaron la solicitud.</Empty>
          )}
        </section>
      </div>
    </div>
  );
}

function Conversation({ userId, onChange, onLeave }) {
  const toast = useToast();
  const [data, setData] = useState(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const listRef = useRef(null);
  const lastId = useRef(0);

  useEffect(() => {
    let alive = true;
    const load = async (initial) => {
      try {
        const { data: d } = await api.get(`/social/messages/${userId}/${initial ? "" : `?after=${lastId.current}`}`);
        if (!alive) return;
        if (initial) setData(d);
        else if (d.messages.length) setData((prev) => ({ ...d, messages: [...(prev?.messages || []), ...d.messages] }));
        const all = d.messages;
        if (all.length) lastId.current = all[all.length - 1].id;
        if (all.length) onChange();
      } catch (e) {
        if (initial && alive) setData({ error: errorMessage(e) });
      }
    };
    load(true);
    const id = setInterval(() => document.visibilityState === "visible" && load(false), 3000);
    return () => { alive = false; clearInterval(id); };
  }, [userId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [data?.messages?.length]);

  const send = async () => {
    const body = text.trim();
    if (!body) return;
    setSending(true);
    try {
      const { data: m } = await api.post(`/social/messages/${userId}/`, { body });
      setData((d) => ({ ...d, messages: [...d.messages, m] }));
      lastId.current = m.id;
      setText("");
      onChange();
    } catch (e) {
      toast(errorMessage(e), "error");
    } finally {
      setSending(false);
    }
  };

  const unfriend = async () => {
    if (!window.confirm("¿Eliminar a esta persona de tus amigos? Ya no podrán escribirse.")) return;
    await api.delete(`/social/friends/${userId}/`);
    onChange();
    onLeave();
  };

  if (!data) return <div className="loader"><div className="spinner" /></div>;
  if (data.error) return <Empty title="No se pudo abrir la conversación">{data.error}</Empty>;
  const u = data.user;
  let lastDay = "";

  return (
    <div className="conv-wrap">
      <header className="conv-head">
        <Avatar name={u.name} url={u.avatar_url} size={42} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <strong>{u.name}</strong>
          <div className="muted" style={{ fontSize: 12.5 }}>@{u.username} · perfil {u.risk_profile.toLowerCase()}{u.gain_pct !== undefined && <> · rendimiento <span className={tone(u.gain_pct)}>{pct(u.gain_pct)}</span></>}</div>
          {u.description && <div className="conv-desc">{u.description}</div>}
        </div>
        <button className="btn btn-ghost btn-sm" onClick={unfriend} title="Eliminar amigo"><UserMinus size={15} /></button>
      </header>
      <div className="messages" ref={listRef}>
        {data.messages.length === 0 && <p className="muted" style={{ textAlign: "center", marginTop: 40 }}>Aún no hay mensajes. ¡Rompe el hielo!</p>}
        {data.messages.map((m) => {
          const d = day(m.created_at);
          const sep = d !== lastDay;
          lastDay = d;
          return (
            <Fragment key={m.id}>
              {sep && <div className="day-sep"><span>{d}</span></div>}
              <div className={`msg ${m.mine ? "mine" : ""}`}>
                <div className="bubble">{renderBody(m.body)}</div>
                <span className="msg-time">{time(m.created_at)}{m.mine && m.read ? " · leído" : ""}</span>
              </div>
            </Fragment>
          );
        })}
      </div>
      <div className="composer">
        <textarea className="input" rows={1} placeholder="Escribe un mensaje… (Enter para enviar)" value={text} maxLength={2000}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
        <button className="btn btn-primary" onClick={send} disabled={sending || !text.trim()} aria-label="Enviar"><Send size={16} /></button>
      </div>
    </div>
  );
}
