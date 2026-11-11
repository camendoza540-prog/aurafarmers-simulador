const toNum = (v) => (v === null || v === undefined || v === "" ? null : Number(v));

export const money = (v, compact = false) => {
  const x = toNum(v);
  if (x === null || Number.isNaN(x)) return "—";
  const s = Math.abs(x).toLocaleString("es-CO", {
    minimumFractionDigits: compact ? 0 : 2,
    maximumFractionDigits: compact ? 0 : 2,
  });
  return `${x < 0 ? "−" : ""}US$ ${s}`;
};

const CCY_PREFIX = { USD: "US$ ", COP: "COP ", JPY: "¥ ", MXN: "MXN ", BRL: "R$ ", CHF: "CHF ", CAD: "CA$ " };

/** Precio con la moneda en la que cotiza el instrumento (USDCOP en pesos, USDJPY en yenes). */
export const price = (v, ccy = "USD") => {
  const x = toNum(v);
  if (x === null) return "—";
  const digits = x < 10 ? 4 : x < 1000 ? 2 : 2;
  return (CCY_PREFIX[ccy] ?? `${ccy} `) + x.toLocaleString("es-CO", { minimumFractionDigits: digits, maximumFractionDigits: digits });
};

export const pct = (v, signed = true, digits = 2) => {
  const x = toNum(v);
  if (x === null || Number.isNaN(x)) return "—";
  const s = Math.abs(x).toLocaleString("es-CO", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  const sign = x < 0 ? "−" : signed && x > 0 ? "+" : "";
  return `${sign}${s} %`;
};

export const number = (v, digits = 2) => {
  const x = toNum(v);
  if (x === null) return "—";
  return x.toLocaleString("es-CO", { maximumFractionDigits: digits });
};

export const qty = (v) => {
  const x = toNum(v);
  if (x === null) return "—";
  return x.toLocaleString("es-CO", { maximumFractionDigits: x < 1 ? 6 : 4 });
};

export const signed = (v) => {
  const x = toNum(v);
  if (x === null) return "—";
  return `${x > 0 ? "+" : x < 0 ? "−" : ""}${money(Math.abs(x))}`;
};

export const tone = (v) => {
  const x = toNum(v);
  if (!x) return "flat";
  return x > 0 ? "gain" : "loss";
};

const asDate = (iso) => new Date(iso.length === 10 ? `${iso}T12:00:00` : iso);
export const dateShort = (iso) => asDate(iso).toLocaleDateString("es-CO", { day: "numeric", month: "short" });
export const dateLong = (iso) => asDate(iso).toLocaleDateString("es-CO", { day: "numeric", month: "short", year: "numeric" });
export const dateTime = (iso) => asDate(iso).toLocaleString("es-CO", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export const axisMoney = (v) => {
  const x = Math.abs(v);
  if (x >= 1e6) return `${(v / 1e6).toFixed(1)} M`;
  if (x >= 1e3) return `${(v / 1e3).toFixed(x >= 1e4 ? 0 : 1)} k`;
  return `${Math.round(v)}`;
};
