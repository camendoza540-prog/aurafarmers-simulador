import Logo from "../components/Logo";

/** Panel lateral de las pantallas de acceso: surcos que crecen como interés compuesto. */
export default function AuthSide() {
  const rows = Array.from({ length: 11 }, (_, i) => i);
  return (
    <section className="auth-side">
      <div>
        <div className="row" style={{ gap: 12 }}>
          <Logo />
          <span className="brand-name" style={{ color: "#fff" }}>Aura Farmers</span>
        </div>
        <small className="auth-credit" style={{ display: "block" }}>Ingeniería de Software I · UIS · Grupo 5</small>
      </div>
      <div style={{ position: "relative", zIndex: 1 }}>
        <h1>Siembra hoy, aprende a cosechar.</h1>
        <p>
          Practica con US$ 100.000 ficticios: compra acciones y ETFs, abre CDT, arma portafolios
          y pon a prueba tus decisiones frente a crisis reales del mercado.
        </p>
      </div>
      <svg className="auth-rows" viewBox="0 0 600 300" preserveAspectRatio="none" aria-hidden="true">
        {rows.map((i) => {
          const x = 30 + i * 54;
          const h = 30 * Math.pow(1.22, i);
          return <rect key={i} x={x} y={300 - h} width="30" height={h} rx="4" fill={i === rows.length - 1 ? "#D99A1E" : "#1E5A43"} opacity={0.35 + i * 0.06} />;
        })}
        <path d={rows.map((i) => `${i ? "L" : "M"}${45 + i * 54},${300 - 30 * Math.pow(1.22, i) - 10}`).join(" ")}
              stroke="#D99A1E" strokeWidth="3" fill="none" strokeLinecap="round" />
      </svg>
      <span />
    </section>
  );
}
