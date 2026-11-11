import { Suspense, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  BookOpen, Briefcase, CandlestickChart, Headphones, Home, LogOut, Menu, MessagesSquare, PiggyBank, Sprout, Trophy, User,
} from "lucide-react";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";
import { money } from "../utils/format";
import Avatar from "./Avatar";
import Logo from "./Logo";
import TermsGate from "./TermsGate";

const NAV = [
  { to: "/", label: "Resumen", icon: Home, end: true },
  { to: "/mercado", label: "Mercado y trading", icon: CandlestickChart },
  { to: "/portafolios", label: "Portafolios", icon: Briefcase },
  { to: "/ahorro", label: "Ahorro y CDT", icon: PiggyBank },
  { to: "/escenarios", label: "Escenarios", icon: Sprout },
  { to: "/ranking", label: "Ranking", icon: Trophy },
  { to: "/comunidad", label: "Comunidad", icon: MessagesSquare, badge: "social" },
  { to: "/aprende", label: "Aprende", icon: BookOpen },
  { to: "/soporte", label: "Soporte", icon: Headphones, badge: "support" },
  { to: "/perfil", label: "Mi perfil", icon: User },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [counts, setCounts] = useState({});
  const location = useLocation();
  const current = NAV.find((n) => (n.end ? location.pathname === n.to : location.pathname.startsWith(n.to)));
  const terminal = /^\/mercado\/.+/.test(location.pathname);

  useEffect(() => {
    let alive = true;
    const load = () => api.get("/social/summary/").then(({ data }) => alive && setCounts(data)).catch(() => {});
    load();
    const id = setInterval(() => document.visibilityState === "visible" && load(), 10000);
    return () => { alive = false; clearInterval(id); };
  }, [location.pathname]);

  const badge = (kind) => {
    if (kind === "social") return (counts.unread_messages || 0) + (counts.pending_requests || 0);
    if (kind === "support") return user?.is_staff ? counts.support_open || 0 : counts.support_unread || 0;
    return 0;
  };
  const name = `${user?.first_name || ""} ${user?.last_name || ""}`.trim() || user?.username;

  return (
    <div className="app">
      <aside className={`sidebar ${open ? "open" : ""}`} onClick={() => setOpen(false)}>
        <NavLink to="/" className="brand">
          <Logo />
          <span className="brand-name">Aura Farmers<span className="brand-sub">Simulador de inversión</span></span>
        </NavLink>
        <nav className="nav">
          {NAV.map(({ to, label, icon: Icon, end, badge: b }) => (
            <NavLink key={to} to={to} end={end} className="nav-link">
              <Icon size={18} aria-hidden /> <span>{label}</span>
              {b && badge(b) > 0 && <span className="nav-badge">{badge(b)}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <NavLink to="/perfil" className="who-row">
            <Avatar name={name} url={user?.profile?.avatar_url} size={36} />
            <div style={{ minWidth: 0 }}>
              <div className="who ellipsis">{name}</div>
              <div className="ellipsis" style={{ color: "var(--sage)" }}>@{user?.username}{user?.is_staff ? " · Soporte" : ""}</div>
            </div>
          </NavLink>
          <button className="btn btn-ghost btn-sm" onClick={logout}><LogOut size={15} /> Cerrar sesión</button>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="row">
            <button className="icon-btn mobile-nav-toggle" onClick={() => setOpen(true)} aria-label="Abrir menú"><Menu /></button>
            <strong style={{ fontSize: 15 }}>{current?.label || "Aura Farmers"}</strong>
          </div>
          <div className="topbar-meta">
            <span className="market-clock" title="El mercado simulado avanza 6 veces más rápido que el reloj real para que veas la variación en segundos.">
              <span className="pulse" /> Mercado simulado en vivo
            </span>
            <span className="cash-pill">Efectivo <strong>{money(user?.profile?.cash_balance)}</strong></span>
          </div>
        </header>
        <main className={`content ${terminal ? "content-wide" : ""}`}>
          <Suspense fallback={<div className="page-loading" role="status">Cargando…</div>}>
            <Outlet />
          </Suspense>
        </main>
        <TermsGate />
      </div>
    </div>
  );
}
