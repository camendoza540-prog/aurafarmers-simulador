const COLORS = ["#1e5a43", "#d99a1e", "#3c7aa6", "#b5603f", "#7a4d7e", "#6f8a3c"];

/** Foto de perfil o, si no hay, las iniciales sobre un color estable por usuario. */
export default function Avatar({ name = "", url, size = 36 }) {
  const initials = name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";
  const color = COLORS[[...name].reduce((a, c) => a + c.charCodeAt(0), 0) % COLORS.length];
  const style = { width: size, height: size, fontSize: Math.round(size * 0.4) };
  return url
    ? <img className="avatar" src={url} alt="" style={style} />
    : <span className="avatar" style={{ ...style, background: color }} aria-hidden="true">{initials}</span>;
}
