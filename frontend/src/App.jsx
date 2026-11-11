import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Register from "./pages/Register";
import { useAuth } from "./context/AuthContext";
// Carga diferida: cada pantalla se descarga solo cuando se visita (gráficos y Markdown pesan)
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Community = lazy(() => import("./pages/Community"));
const Learn = lazy(() => import("./pages/Learn"));
const Legal = lazy(() => import("./pages/Legal"));
const LessonDetail = lazy(() => import("./pages/LessonDetail"));
const Market = lazy(() => import("./pages/Market"));
const NotFound = lazy(() => import("./pages/NotFound"));
const PortfolioDetail = lazy(() => import("./pages/PortfolioDetail"));
const Portfolios = lazy(() => import("./pages/Portfolios"));
const Profile = lazy(() => import("./pages/Profile"));
const Ranking = lazy(() => import("./pages/Ranking"));
const Savings = lazy(() => import("./pages/Savings"));
const Scenarios = lazy(() => import("./pages/Scenarios"));
const Support = lazy(() => import("./pages/Support"));
const Terminal = lazy(() => import("./pages/Terminal"));


function PublicOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user ? <Navigate to="/" replace /> : children;
}

export default function App() {
  return (
    <Suspense fallback={<div className="page-loading" role="status">Cargando…</div>}>
    <Routes>
      <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
      <Route path="/registro" element={<PublicOnly><Register /></PublicOnly>} />
      <Route path="/legal" element={<Legal />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="mercado" element={<Market />} />
        <Route path="mercado/:symbol" element={<Terminal />} />
        <Route path="portafolios" element={<Portfolios />} />
        <Route path="portafolios/:id" element={<PortfolioDetail />} />
        <Route path="ahorro" element={<Savings />} />
        <Route path="escenarios" element={<Scenarios />} />
        <Route path="aprende" element={<Learn />} />
        <Route path="aprende/:slug" element={<LessonDetail />} />
        <Route path="perfil" element={<Profile />} />
        <Route path="ranking" element={<Ranking />} />
        <Route path="comunidad" element={<Community />} />
        <Route path="soporte" element={<Support />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
    </Suspense>
  );
}
