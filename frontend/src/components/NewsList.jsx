import { ExternalLink, Newspaper } from "lucide-react";
import usePolling from "../hooks/usePolling";
import { Loader } from "./Feedback";

function ago(iso) {
  if (!iso) return "";
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 60) return `hace ${Math.max(mins, 1)} min`;
  const h = Math.round(mins / 60);
  if (h < 24) return `hace ${h} h`;
  const d = Math.round(h / 24);
  return `hace ${d} ${d === 1 ? "día" : "días"}`;
}

/** Titulares recientes con enlace a la nota original (Google Noticias / Yahoo Finance). */
export default function NewsList({ url, limit = 10, compact = false }) {
  const { data, loading } = usePolling(url, 10 * 60 * 1000);
  if (loading && !data) return <Loader label="Buscando noticias…" />;
  const items = (data?.items || []).slice(0, limit);
  if (!items.length) {
    return (
      <div className="empty" style={{ padding: "24px 12px" }}>
        <Newspaper size={22} color="var(--muted)" />
        <h3 style={{ marginTop: 8 }}>{data?.available === false ? "Noticias no disponibles" : "Sin noticias recientes"}</h3>
        <p>{data?.available === false
          ? "No se pudo conectar con las fuentes de noticias. Verifica la conexión a internet del servidor."
          : "No encontramos titulares de los últimos 14 días para este activo."}</p>
      </div>
    );
  }
  return (
    <ul className={`news ${compact ? "compact" : ""}`}>
      {items.map((n) => (
        <li key={n.url}>
          <a href={n.url} target="_blank" rel="noopener noreferrer">
            <span className="news-title">{n.title}</span>
            <span className="news-meta">{n.source}{n.published ? ` · ${ago(n.published)}` : ""} <ExternalLink size={12} /></span>
          </a>
        </li>
      ))}
    </ul>
  );
}
