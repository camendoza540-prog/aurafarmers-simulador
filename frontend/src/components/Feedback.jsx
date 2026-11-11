import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { errorMessage } from "../api/client";
import { pct, tone } from "../utils/format";

export function Loader({ label = "Cargando…" }) {
  return (
    <div className="loader" role="status">
      <div className="spinner" />
      <span style={{ marginTop: 10 }}>{label}</span>
    </div>
  );
}

export function ErrorBox({ error, onRetry }) {
  if (!error) return null;
  return (
    <div className="error-box row between">
      <span>{errorMessage(error)}</span>
      {onRetry && <button className="btn btn-secondary btn-sm" onClick={() => onRetry()}>Reintentar</button>}
    </div>
  );
}

export function Empty({ title, children, action }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

export function Delta({ value, pill = false, icon = true, digits = 2 }) {
  const t = tone(value);
  const Icon = t === "loss" ? ArrowDownRight : ArrowUpRight;
  return (
    <span className={`delta ${t} ${pill ? "delta-pill" : ""}`}>
      {icon && t !== "flat" && <Icon size={14} aria-hidden />}
      {pct(value, true, digits)}
    </span>
  );
}

const TYPE_TAGS = {
  STOCK: ["Acción", "tag-stock"], ETF: ["ETF", "tag-etf"], FOREX: ["Forex", "tag-fx"],
  INDEX: ["Índice", "tag-index"], COMMODITY: ["Materia prima", "tag-cmd"], CRYPTO: ["Cripto", "tag-crypto"],
};

export function TypeTag({ type }) {
  const [label, cls] = TYPE_TAGS[type] || [type, ""];
  return <span className={`tag ${cls}`}>{label}</span>;
}

export function Metric({ label, value, note, className = "" }) {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${className}`}>{value}</div>
      {note && <div className="metric-note">{note}</div>}
    </div>
  );
}
