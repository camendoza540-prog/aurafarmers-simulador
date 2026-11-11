import { Link } from "react-router-dom";
import { Empty } from "../components/Feedback";

export default function NotFound() {
  return (
    <Empty title="Esta página no existe" action={<Link className="btn btn-primary" to="/">Volver al resumen</Link>}>
      Revisa la dirección o usa el menú de la izquierda.
    </Empty>
  );
}
