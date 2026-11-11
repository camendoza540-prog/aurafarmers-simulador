/**
 * Indicadores técnicos calculados en el navegador a partir de velas {time, open, high, low, close, volume}.
 * Devuelven arreglos {time, value} listos para la librería de gráficos.
 */

export function sma(candles, period) {
  const out = [];
  let sum = 0;
  for (let i = 0; i < candles.length; i++) {
    sum += candles[i].close;
    if (i >= period) sum -= candles[i - period].close;
    if (i >= period - 1) out.push({ time: candles[i].time, value: sum / period });
  }
  return out;
}

export function ema(candles, period, key = "close") {
  const out = [];
  const k = 2 / (period + 1);
  let prev;
  for (let i = 0; i < candles.length; i++) {
    const v = candles[i][key];
    if (i < period - 1) continue;
    if (prev === undefined) {
      let s = 0;
      for (let j = i - period + 1; j <= i; j++) s += candles[j][key];
      prev = s / period;
    } else {
      prev = v * k + prev * (1 - k);
    }
    out.push({ time: candles[i].time, value: prev });
  }
  return out;
}

export function bollinger(candles, period = 20, mult = 2) {
  const upper = [], lower = [], middle = [];
  for (let i = period - 1; i < candles.length; i++) {
    let s = 0;
    for (let j = i - period + 1; j <= i; j++) s += candles[j].close;
    const mean = s / period;
    let v = 0;
    for (let j = i - period + 1; j <= i; j++) v += (candles[j].close - mean) ** 2;
    const sd = Math.sqrt(v / period);
    const t = candles[i].time;
    middle.push({ time: t, value: mean });
    upper.push({ time: t, value: mean + mult * sd });
    lower.push({ time: t, value: mean - mult * sd });
  }
  return { upper, middle, lower };
}

export function rsi(candles, period = 14) {
  const out = [];
  if (candles.length <= period) return out;
  let gain = 0, loss = 0;
  for (let i = 1; i <= period; i++) {
    const d = candles[i].close - candles[i - 1].close;
    if (d >= 0) gain += d; else loss -= d;
  }
  gain /= period;
  loss /= period;
  out.push({ time: candles[period].time, value: loss === 0 ? 100 : 100 - 100 / (1 + gain / loss) });
  for (let i = period + 1; i < candles.length; i++) {
    const d = candles[i].close - candles[i - 1].close;
    gain = (gain * (period - 1) + Math.max(d, 0)) / period;
    loss = (loss * (period - 1) + Math.max(-d, 0)) / period;
    out.push({ time: candles[i].time, value: loss === 0 ? 100 : 100 - 100 / (1 + gain / loss) });
  }
  return out;
}

export function macd(candles, fast = 12, slow = 26, signal = 9) {
  const ef = ema(candles, fast);
  const es = ema(candles, slow);
  const fastByTime = new Map(ef.map((p) => [p.time, p.value]));
  const line = es.map((p) => ({ time: p.time, close: fastByTime.get(p.time) - p.value }));
  const sig = ema(line, signal);
  const sigByTime = new Map(sig.map((p) => [p.time, p.value]));
  const hist = [];
  for (const p of line) {
    const s = sigByTime.get(p.time);
    if (s === undefined) continue;
    const h = p.close - s;
    hist.push({ time: p.time, value: h, color: h >= 0 ? "rgba(35,133,90,0.55)" : "rgba(194,65,45,0.55)" });
  }
  return { line: line.map((p) => ({ time: p.time, value: p.close })), signal: sig, hist };
}

export function heikinAshi(candles) {
  const out = [];
  for (let i = 0; i < candles.length; i++) {
    const c = candles[i];
    const close = (c.open + c.high + c.low + c.close) / 4;
    const open = i === 0 ? (c.open + c.close) / 2 : (out[i - 1].open + out[i - 1].close) / 2;
    out.push({ time: c.time, open, close, high: Math.max(c.high, open, close), low: Math.min(c.low, open, close) });
  }
  return out;
}

export const INDICATORS = [
  { key: "sma20", label: "Media móvil simple 20", short: "SMA 20", color: "#d99a1e" },
  { key: "sma50", label: "Media móvil simple 50", short: "SMA 50", color: "#14261e" },
  { key: "ema20", label: "Media móvil exponencial 20", short: "EMA 20", color: "#7a4d7e" },
  { key: "bb", label: "Bandas de Bollinger (20, 2)", short: "Bollinger", color: "#3c7aa6" },
  { key: "volume", label: "Volumen", short: "Volumen", color: "#9db8a6" },
  { key: "rsi", label: "RSI 14 (panel inferior)", short: "RSI", color: "#7a4d7e" },
  { key: "macd", label: "MACD 12-26-9 (panel inferior)", short: "MACD", color: "#3c7aa6" },
];
