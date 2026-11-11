import { useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import usePolling from "../hooks/usePolling";
import { ErrorBox, Loader } from "../components/Feedback";

export default function Learn() {
  const { data, error, loading, reload } = usePolling("/learning/lessons/");
  const glossary = usePolling("/learning/glossary/");
  const [q, setQ] = useState("");

  if (loading && !data) return <Loader />;
  if (error && !data) return <ErrorBox error={error} onRetry={reload} />;
  const terms = (glossary.data || []).filter((t) => !q || t.term.toLowerCase().includes(q.toLowerCase()) || t.definition.toLowerCase().includes(q.toLowerCase()));

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Aprende</h1>
          <p>Ocho lecciones cortas, de lo básico a las crisis financieras. Cada una termina con tres preguntas y te lleva a practicar en el simulador.</p>
        </div>
        <div style={{ minWidth: 220 }}>
          <div className="row between" style={{ fontSize: 13, marginBottom: 6 }}><span className="muted">Tu progreso</span><strong>{data.completed} de {data.total}</strong></div>
          <div className="furrow" style={{ height: 10, margin: 0 }}><span style={{ width: `${(data.completed / data.total) * 100}%`, background: "var(--wheat)" }} /></div>
        </div>
      </div>

      <div className="grid grid-main">
        <section className="panel">
          <div className="lesson-list">
            {data.lessons.map((l) => (
              <Link key={l.slug} to={`/aprende/${l.slug}`} className={`lesson-item ${l.completed ? "done" : ""}`}>
                <span className="lesson-num">{l.completed ? <CheckCircle2 size={26} /> : l.order}</span>
                <div>
                  <h3 style={{ fontSize: 16 }}>{l.title}</h3>
                  <div className="muted" style={{ fontSize: 13.5 }}>{l.summary}</div>
                </div>
                <div style={{ textAlign: "right", fontSize: 12.5 }} className="muted">
                  <div>{l.category_label}</div>
                  <div>{l.minutes} min · {l.level_label}</div>
                  {l.score && <div className="gain">{l.score.score}/{l.score.total} correctas</div>}
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2 style={{ marginBottom: 10 }}>Glosario</h2>
          <input className="input" placeholder="Buscar un término" value={q} onChange={(e) => setQ(e.target.value)} style={{ marginBottom: 10 }} />
          <div style={{ maxHeight: 620, overflowY: "auto" }}>
            {terms.map((t) => (
              <div key={t.id} style={{ padding: "10px 0", borderBottom: "1px solid var(--line-soft)" }}>
                <strong>{t.term}</strong>
                <p style={{ margin: "2px 0 0", fontSize: 13.5, color: "var(--ink-2)" }}>{t.definition}</p>
              </div>
            ))}
            {terms.length === 0 && <p className="muted">Sin coincidencias.</p>}
          </div>
        </section>
      </div>
    </div>
  );
}
