import { Link } from "react-router-dom";
import { Trophy, UserPlus } from "lucide-react";
import api, { errorMessage } from "../api/client";
import { useToast } from "../context/ToastContext";
import usePolling from "../hooks/usePolling";
import Avatar from "../components/Avatar";
import { Empty, ErrorBox, Loader } from "../components/Feedback";
import { money, pct, signed, tone } from "../utils/format";

const MEDAL = ["#d99a1e", "#9aa7a0", "#b5603f"];

export default function Ranking() {
  const toast = useToast();
  const { data, error, loading, reload } = usePolling("/auth/ranking/", 30000);

  const add = async (r) => {
    try {
      const { data: d } = await api.post("/social/requests/", { to_user: r.user_id });
      toast(d.detail);
    } catch (e) {
      toast(errorMessage(e), "info");
    }
  };

  if (loading && !data) return <Loader />;
  if (error && !data) return <ErrorBox error={error} onRetry={reload} />;
  const podium = data.filter((r) => r.position <= 3);
  const rest = data;

  return (
    <div className="stack">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1>Ranking de inversionistas</h1>
          <p>Ordenado por la ganancia total del patrimonio frente al saldo inicial de US$ 100.000. Se actualiza con los precios en vivo.</p>
        </div>
      </div>

      {podium.length > 0 && (
        <section className="podium">
          {[1, 0, 2].map((i) => podium[i] && (
            <div key={podium[i].user_id} className={`podium-col p${podium[i].position}`}>
              <div className="podium-medal" style={{ background: MEDAL[podium[i].position - 1] }}><Trophy size={16} /> {podium[i].position}</div>
              <Avatar name={podium[i].name} url={podium[i].avatar_url} size={podium[i].position === 1 ? 84 : 68} />
              <strong className="podium-name">{podium[i].name}{podium[i].is_me && " (tú)"}</strong>
              <span className="muted" style={{ fontSize: 13 }}>@{podium[i].username}</span>
              <span className={`podium-profit ${tone(podium[i].profit)}`}>{signed(podium[i].profit)}</span>
              <span className={tone(podium[i].gain_pct)}>{pct(podium[i].gain_pct)}</span>
              <div className="podium-base" />
            </div>
          ))}
        </section>
      )}

      <section className="panel panel-flush">
        {rest.length === 0 ? <Empty title="Aún no hay inversionistas en el ranking" /> : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>#</th><th>Inversionista</th><th className="num">Patrimonio</th><th className="num">Ganancia</th><th className="num">Rendimiento</th><th className="num">Operaciones</th><th className="num">Ganadoras</th><th /></tr>
              </thead>
              <tbody>
                {rest.map((r) => (
                  <tr key={r.user_id} className={r.is_me ? "me-row" : ""}>
                    <td><strong>{r.position}</strong></td>
                    <td>
                      <div className="row" style={{ gap: 10, flexWrap: "nowrap" }}>
                        <Avatar name={r.name} url={r.avatar_url} size={34} />
                        <div><strong>{r.name}{r.is_me && " (tú)"}</strong><div className="muted" style={{ fontSize: 12.5 }}>@{r.username}</div></div>
                      </div>
                    </td>
                    <td className="num">{money(r.total)}</td>
                    <td className={`num ${tone(r.profit)}`}><strong>{signed(r.profit)}</strong></td>
                    <td className={`num ${tone(r.gain_pct)}`}>{pct(r.gain_pct)}</td>
                    <td className="num">{r.trades}</td>
                    <td className="num">{r.wins}</td>
                    <td className="num">
                      {!r.is_me && <button className="btn btn-ghost btn-sm" onClick={() => add(r)}><UserPlus size={14} /> Agregar</button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <p className="muted" style={{ fontSize: 13 }}>¿No quieres aparecer? Desactívalo en <Link to="/perfil">Mi perfil</Link>. El equipo de soporte y los administradores no participan.</p>
    </div>
  );
}
