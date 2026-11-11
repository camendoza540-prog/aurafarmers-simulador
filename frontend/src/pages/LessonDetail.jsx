import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft, ArrowRight } from "lucide-react";
import api, { errorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import usePolling from "../hooks/usePolling";
import { ErrorBox, Loader } from "../components/Feedback";

const TRY_LABEL = { "/mercado": "Explorar el mercado", "/portafolios": "Ir a mis portafolios", "/ahorro": "Abrir un CDT", "/escenarios": "Simular una crisis" };

export default function LessonDetail() {
  const { slug } = useParams();
  const toast = useToast();
  const { data, error, loading, reload } = usePolling(`/learning/lessons/${slug}/`);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);

  useEffect(() => { setAnswers({}); setResult(null); window.scrollTo(0, 0); }, [slug]);

  if (loading && !data) return <Loader />;
  if (error && !data) return <ErrorBox error={error} onRetry={reload} />;

  const submit = async () => {
    try {
      const { data: r } = await api.post(`/learning/lessons/${slug}/quiz/`, { answers });
      setResult(r);
      toast(`Obtuviste ${r.score} de ${r.total}.`, r.score === r.total ? "success" : "info");
    } catch (e) {
      toast(errorMessage(e), "error");
    }
  };
  const byId = Object.fromEntries((result?.results || []).map((r) => [r.id, r]));

  return (
    <div className="stack">
      <Link to="/aprende" className="btn btn-ghost btn-sm" style={{ alignSelf: "flex-start" }}><ArrowLeft size={15} /> Lecciones</Link>
      <section className="panel" style={{ padding: "28px 32px" }}>
        <div className="muted" style={{ fontSize: 13 }}>Lección {data.order} · {data.category_label} · {data.minutes} min</div>
        <h1 style={{ margin: "6px 0 18px" }}>{data.title}</h1>
        <div className="prose"><ReactMarkdown remarkPlugins={[remarkGfm]}>{data.content}</ReactMarkdown></div>
        {data.try_it && <Link className="btn btn-secondary" to={data.try_it} style={{ marginTop: 12 }}>{TRY_LABEL[data.try_it] || "Practicar"} <ArrowRight size={15} /></Link>}
      </section>

      <section className="panel" style={{ padding: "24px 32px" }}>
        <h2>Comprueba lo que aprendiste</h2>
        {data.questions.map((q, qi) => {
          const r = byId[q.id];
          return (
            <div key={q.id} className="quiz-q">
              <strong>{qi + 1}. {q.question}</strong>
              {q.options.map((opt, oi) => {
                const sel = Number(answers[q.id]) === oi && answers[q.id] !== undefined;
                const cls = r ? (oi === r.correct_index ? "right" : sel ? "wrong" : "") : sel ? "sel" : "";
                return (
                  <label key={oi} className={`quiz-opt ${cls}`}>
                    <input type="radio" name={`q${q.id}`} disabled={!!r} checked={sel} onChange={() => setAnswers({ ...answers, [q.id]: oi })} />
                    <span>{opt}</span>
                  </label>
                );
              })}
              {r && <p style={{ fontSize: 13.5, marginTop: 8 }} className={r.correct ? "gain" : "loss"}>{r.correct ? "Correcto. " : "Incorrecto. "}<span style={{ color: "var(--ink-2)" }}>{r.explanation}</span></p>}
            </div>
          );
        })}
        <div className="row between" style={{ marginTop: 18 }}>
          {result ? (
            <>
              <strong>Resultado: {result.score} de {result.total}</strong>
              <button className="btn btn-secondary" onClick={() => { setResult(null); setAnswers({}); }}>Intentar de nuevo</button>
            </>
          ) : (
            <button className="btn btn-primary" disabled={Object.keys(answers).length < data.questions.length} onClick={submit}>Revisar respuestas</button>
          )}
        </div>
      </section>

      <div className="row between">
        {data.previous ? <Link className="btn btn-ghost" to={`/aprende/${data.previous.slug}`}><ArrowLeft size={15} /> {data.previous.title}</Link> : <span />}
        {data.next && <Link className="btn btn-primary" to={`/aprende/${data.next.slug}`}>{data.next.title} <ArrowRight size={15} /></Link>}
      </div>
    </div>
  );
}
