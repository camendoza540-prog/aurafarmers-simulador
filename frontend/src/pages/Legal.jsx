import { useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Link, useLocation } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import Logo from "../components/Logo";
import { useAuth } from "../context/AuthContext";
import { PRIVACY_MD, TERMS_DATE, TERMS_MD, TERMS_VERSION } from "../legal";

/** Términos y condiciones + política de tratamiento de datos (Ley 1581 de 2012). Pública. */
export default function Legal() {
  const { user } = useAuth();
  const { hash } = useLocation();

  useEffect(() => {
    const el = hash && document.getElementById(hash.slice(1));
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    else window.scrollTo(0, 0);
  }, [hash]);

  return (
    <div className="legal-page">
      <header className="legal-head">
        <Link to={user ? "/" : "/login"} className="legal-brand"><Logo /> <strong>Aura Farmers</strong></Link>
        <Link to={user ? "/perfil" : "/registro"} className="btn btn-ghost btn-sm"><ArrowLeft size={16} /> Volver</Link>
      </header>
      <main className="legal-main">
        <p className="legal-version">Versión {TERMS_VERSION} · vigente desde el {TERMS_DATE}</p>
        <nav className="legal-nav">
          <a href="#terminos">Términos y condiciones</a>
          <a href="#privacidad">Política de tratamiento de datos</a>
        </nav>
        <section id="terminos" className="legal-section">
          <h1>Términos y condiciones</h1>
          <div className="prose"><ReactMarkdown remarkPlugins={[remarkGfm]}>{TERMS_MD}</ReactMarkdown></div>
        </section>
        <section id="privacidad" className="legal-section">
          <h1>Política de tratamiento de datos personales</h1>
          <div className="prose"><ReactMarkdown remarkPlugins={[remarkGfm]}>{PRIVACY_MD}</ReactMarkdown></div>
        </section>
      </main>
    </div>
  );
}
