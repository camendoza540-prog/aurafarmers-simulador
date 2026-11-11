import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import {
  AreaSeries, BarSeries, CandlestickSeries, ColorType, CrosshairMode, HistogramSeries, LineSeries, LineStyle,
  createChart,
} from "lightweight-charts";
import api from "../../api/client";
import { bollinger, ema, heikinAshi, macd, rsi, sma } from "./indicators";
import { TrendLine } from "./TrendLine";

const UP = "#23855a";
const DOWN = "#c2412d";
const TF_SECONDS = { "1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600 };
const DAILY = new Set(["1D", "1S", "1M"]);

const fmt = (v) => (v === undefined || v === null ? "—" : v.toLocaleString("es-CO", { minimumFractionDigits: 2, maximumFractionDigits: v < 10 ? 4 : 2 }));
const storageKey = (symbol, tf) => `af_draw_${symbol}_${DAILY.has(tf) ? "d" : "i"}`;

function loadDrawings(symbol, tf) {
  try {
    return JSON.parse(localStorage.getItem(storageKey(symbol, tf))) || { hlines: [], trends: [] };
  } catch {
    return { hlines: [], trends: [] };
  }
}

function saveDrawings(symbol, tf, d) {
  try {
    localStorage.setItem(storageKey(symbol, tf), JSON.stringify(d));
  } catch {
    /* almacenamiento no disponible: los dibujos solo duran la sesión */
  }
}

/**
 * Gráfico interactivo: tipos (velas, barras, Heikin Ashi, línea, área), temporalidades,
 * indicadores (SMA, EMA, Bollinger, volumen, RSI, MACD), dibujos (líneas horizontales y de tendencia),
 * líneas de posición (entrada, TP, SL) y actualización en vivo cada segundo.
 */
const TradingChart = forwardRef(function TradingChart(
  { symbol, tf, chartType, indicators, tool, onToolChange, priceLines = [], quote, onStatus },
  ref,
) {
  const boxRef = useRef(null);
  const chartRef = useRef(null);
  const mainRef = useRef(null);
  const seriesRef = useRef({});
  const dataRef = useRef([]);
  const offsetRef = useRef(-18000);
  const linesRef = useRef([]);
  const drawRef = useRef({ hlines: [], trends: [] });
  const drawObjs = useRef({ hlines: [], trends: [] });
  const pendingRef = useRef(null);
  const toolRef = useRef(tool);
  const rangeRef = useRef(null);
  const [data, setData] = useState(null);
  const [legend, setLegend] = useState(null);
  const [error, setError] = useState(null);

  toolRef.current = tool;

  // ── Carga de velas ────────────────────────────────────────────────────
  useEffect(() => {
    let alive = true;
    setError(null);
    rangeRef.current = null;
    api.get(`/market/instruments/${symbol}/candles/?tf=${tf}&limit=600`)
      .then(({ data: d }) => {
        if (!alive) return;
        offsetRef.current = d.tz_offset;
        dataRef.current = d.candles;
        setData({ key: `${symbol}-${tf}`, candles: d.candles });
      })
      .catch((e) => alive && setError(e));
    return () => { alive = false; };
  }, [symbol, tf]);

  const mainData = useCallback((candles) => {
    if (chartType === "heikin") return heikinAshi(candles);
    if (chartType === "line" || chartType === "area") return candles.map((c) => ({ time: c.time, value: c.close }));
    return candles;
  }, [chartType]);

  const refreshIndicators = useCallback(() => {
    const c = dataRef.current;
    const s = seriesRef.current;
    if (s.sma20) s.sma20.setData(sma(c, 20));
    if (s.sma50) s.sma50.setData(sma(c, 50));
    if (s.ema20) s.ema20.setData(ema(c, 20));
    if (s.bbU) {
      const b = bollinger(c);
      s.bbU.setData(b.upper);
      s.bbM.setData(b.middle);
      s.bbL.setData(b.lower);
    }
    if (s.rsi) s.rsi.setData(rsi(c));
    if (s.macd) {
      const m = macd(c);
      s.macd.setData(m.line);
      s.macdSig.setData(m.signal);
      s.macdHist.setData(m.hist);
    }
  }, []);

  // ── Dibujos ───────────────────────────────────────────────────────────
  const clearDrawingObjects = useCallback(() => {
    const main = mainRef.current;
    if (!main) return;
    drawObjs.current.hlines.forEach((l) => main.removePriceLine(l));
    drawObjs.current.trends.forEach((t) => main.detachPrimitive(t));
    drawObjs.current = { hlines: [], trends: [] };
  }, []);

  const renderDrawings = useCallback(() => {
    const main = mainRef.current;
    if (!main) return;
    clearDrawingObjects();
    for (const price of drawRef.current.hlines) {
      drawObjs.current.hlines.push(main.createPriceLine({
        price, color: "#d99a1e", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "",
      }));
    }
    for (const t of drawRef.current.trends) {
      const prim = new TrendLine(t.a, t.b);
      main.attachPrimitive(prim);
      drawObjs.current.trends.push(prim);
    }
  }, [clearDrawingObjects]);

  useImperativeHandle(ref, () => ({
    clearDrawings() {
      drawRef.current = { hlines: [], trends: [] };
      saveDrawings(symbol, tf, drawRef.current);
      pendingRef.current = null;
      renderDrawings();
    },
    fit() {
      chartRef.current?.timeScale().fitContent();
    },
    drawingsCount() {
      return drawRef.current.hlines.length + drawRef.current.trends.length;
    },
  }), [symbol, tf, renderDrawings]);

  // ── Construcción del gráfico ──────────────────────────────────────────
  useEffect(() => {
    if (!data || !boxRef.current) return undefined;
    const candles = dataRef.current;
    const chart = createChart(boxRef.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#ffffff" },
        textColor: "#3a4d43",
        fontFamily: "'Public Sans', 'Segoe UI', system-ui, sans-serif",
        fontSize: 12,
        panes: { separatorColor: "#d5ddd3", separatorHoverColor: "#e2eee7", enableResize: true },
      },
      grid: { vertLines: { color: "#f0f3ef" }, horzLines: { color: "#f0f3ef" } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#d5ddd3" },
      timeScale: { borderColor: "#d5ddd3", timeVisible: !DAILY.has(tf), secondsVisible: false, rightOffset: 8 },
      localization: { locale: "es-CO" },
    });
    chartRef.current = chart;
    seriesRef.current = {};

    let main;
    if (chartType === "line") {
      main = chart.addSeries(LineSeries, { color: "#1e5a43", lineWidth: 2 });
    } else if (chartType === "area") {
      main = chart.addSeries(AreaSeries, { lineColor: "#1e5a43", topColor: "rgba(30,90,67,0.28)", bottomColor: "rgba(30,90,67,0.02)", lineWidth: 2 });
    } else if (chartType === "bars") {
      main = chart.addSeries(BarSeries, { upColor: UP, downColor: DOWN, thinBars: false });
    } else {
      main = chart.addSeries(CandlestickSeries, {
        upColor: UP, downColor: DOWN, borderUpColor: UP, borderDownColor: DOWN, wickUpColor: UP, wickDownColor: DOWN,
      });
    }
    const lastClose = candles[candles.length - 1]?.close || 100;
    const precision = lastClose < 10 ? 4 : 2;
    main.applyOptions({ priceFormat: { type: "price", precision, minMove: 1 / 10 ** precision } });
    main.setData(mainData(candles));
    mainRef.current = main;
    const s = seriesRef.current;
    const on = new Set(indicators);
    const overlay = (color, width = 1.5, style = LineStyle.Solid) =>
      chart.addSeries(LineSeries, { color, lineWidth: width, lineStyle: style, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });

    if (on.has("volume")) {
      s.volume = chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "vol", priceLineVisible: false, lastValueVisible: false });
      s.volume.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
      s.volume.setData(candles.map((c) => ({ time: c.time, value: c.volume, color: c.close >= c.open ? "rgba(35,133,90,0.35)" : "rgba(194,65,45,0.35)" })));
    }
    if (on.has("sma20")) s.sma20 = overlay("#d99a1e");
    if (on.has("sma50")) s.sma50 = overlay("#14261e", 1.5, LineStyle.Dashed);
    if (on.has("ema20")) s.ema20 = overlay("#7a4d7e");
    if (on.has("bb")) {
      s.bbU = overlay("rgba(60,122,166,0.85)", 1);
      s.bbM = overlay("rgba(60,122,166,0.5)", 1, LineStyle.Dotted);
      s.bbL = overlay("rgba(60,122,166,0.85)", 1);
    }
    let pane = 1;
    if (on.has("rsi")) {
      s.rsi = chart.addSeries(LineSeries, { color: "#7a4d7e", lineWidth: 1.5, priceLineVisible: false }, pane);
      s.rsi.createPriceLine({ price: 70, color: "#c2412d", lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false, title: "70" });
      s.rsi.createPriceLine({ price: 30, color: "#23855a", lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false, title: "30" });
      pane += 1;
    }
    if (on.has("macd")) {
      s.macdHist = chart.addSeries(HistogramSeries, { priceLineVisible: false, lastValueVisible: false }, pane);
      s.macd = chart.addSeries(LineSeries, { color: "#3c7aa6", lineWidth: 1.5, priceLineVisible: false }, pane);
      s.macdSig = chart.addSeries(LineSeries, { color: "#d99a1e", lineWidth: 1.2, priceLineVisible: false }, pane);
    }
    const panes = chart.panes();
    for (let i = 1; i < panes.length; i++) panes[i].setHeight(110);
    refreshIndicators();

    drawRef.current = loadDrawings(symbol, tf);
    drawObjs.current = { hlines: [], trends: [] };
    renderDrawings();

    // Solo se restaura la vista si es del mismo activo y temporalidad (al cambiar de 5m a 15m
    // el rango anterior apunta a velas que ya no existen y el gráfico quedaba vacío).
    if (rangeRef.current && rangeRef.current.key === data.key) chart.timeScale().setVisibleLogicalRange(rangeRef.current.range);
    else {
      const n = candles.length;
      chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, n - 140), to: n + 6 });
    }

    const last = () => {
      const c = dataRef.current[dataRef.current.length - 1];
      const prev = dataRef.current[dataRef.current.length - 2];
      return c ? { ...c, change: prev ? (c.close / prev.close - 1) * 100 : 0 } : null;
    };
    setLegend(last());
    const onMove = (param) => {
      if (!param.time || !param.seriesData) {
        setLegend(last());
        return;
      }
      const idx = dataRef.current.findIndex((c) => c.time === param.time);
      if (idx < 0) return;
      const c = dataRef.current[idx];
      const prev = dataRef.current[idx - 1];
      setLegend({ ...c, change: prev ? (c.close / prev.close - 1) * 100 : 0 });
    };
    // Clics nativos del navegador (la librería agrupa dos clics rápidos como doble clic y descarta el segundo)
    const onClick = (ev) => {
      const t = toolRef.current;
      if (t === "cursor") return;
      const rect = boxRef.current.getBoundingClientRect();
      const x = ev.clientX - rect.left;
      const y = ev.clientY - rect.top;
      const mainPaneHeight = chart.panes()[0]?.getHeight() ?? rect.height;
      if (y > mainPaneHeight || x > chart.timeScale().width()) return;
      const price = main.coordinateToPrice(y);
      if (price === null) return;
      if (t === "hline") {
        drawRef.current.hlines.push(price);
        saveDrawings(symbol, tf, drawRef.current);
        renderDrawings();
        onToolChange?.("cursor");
        return;
      }
      if (t === "trend") {
        const time = chart.timeScale().coordinateToTime(x);
        if (!time) {
          onStatus?.("Haz clic sobre una zona con velas.");
          return;
        }
        if (!pendingRef.current) {
          pendingRef.current = { time, price };
          onStatus?.("Ahora haz clic en el segundo punto de la línea.");
          return;
        }
        const a = pendingRef.current;
        const b = { time, price };
        if (a.time === b.time && Math.abs(a.price - b.price) / a.price < 0.0005) return; // mismo punto
        pendingRef.current = null;
        const [p1, p2] = a.time <= b.time ? [a, b] : [b, a];
        drawRef.current.trends.push({ a: p1, b: p2 });
        saveDrawings(symbol, tf, drawRef.current);
        renderDrawings();
        onStatus?.(null);
        onToolChange?.("cursor");
      }
    };
    const box = boxRef.current;
    chart.subscribeCrosshairMove(onMove);
    box.addEventListener("click", onClick);
    linesRef.current = [];

    return () => {
      rangeRef.current = { key: data.key, range: chart.timeScale().getVisibleLogicalRange() };
      chart.unsubscribeCrosshairMove(onMove);
      box.removeEventListener("click", onClick);
      chart.remove();
      chartRef.current = null;
      mainRef.current = null;
      linesRef.current = [];
    };
  }, [data, chartType, indicators.join(","), mainData, refreshIndicators, renderDrawings, symbol, tf, onToolChange, onStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Líneas de posiciones (entrada, TP, SL) ───────────────────────────
  const linesKey = JSON.stringify(priceLines);
  useEffect(() => {
    const main = mainRef.current;
    if (!main) return;
    linesRef.current.forEach((l) => { try { main.removePriceLine(l); } catch { /* ya no existe */ } });
    linesRef.current = priceLines.map((pl) => main.createPriceLine({
      price: pl.price, color: pl.color, lineWidth: pl.width || 1, axisLabelVisible: true, title: pl.title,
      lineStyle: pl.dashed ? LineStyle.Dashed : LineStyle.Solid,
    }));
  }, [linesKey, data, chartType, indicators.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Actualización en vivo ─────────────────────────────────────────────
  useEffect(() => {
    if (!quote || !mainRef.current || !dataRef.current.length || quote.symbol !== symbol) return;
    const price = Number(quote.current_price);
    const arr = dataRef.current;
    const last = arr[arr.length - 1];
    let bucket = last.time;
    if (!DAILY.has(tf)) {
      const step = TF_SECONDS[tf];
      const epoch = Math.floor(new Date(quote.last_tick_at || Date.now()).getTime() / 1000) + offsetRef.current;
      bucket = epoch - (epoch % step);
    }
    if (bucket > last.time) {
      arr.push({ time: bucket, open: last.close, high: Math.max(last.close, price), low: Math.min(last.close, price), close: price, volume: 0 });
    } else if (bucket === last.time) {
      last.high = Math.max(last.high, price);
      last.low = Math.min(last.low, price);
      last.close = price;
    } else {
      return;
    }
    const bar = arr[arr.length - 1];
    try {
      if (chartType === "heikin") {
        const ha = heikinAshi(arr.slice(-60));
        mainRef.current.update(ha[ha.length - 1]);
      } else if (chartType === "line" || chartType === "area") {
        mainRef.current.update({ time: bar.time, value: bar.close });
      } else {
        mainRef.current.update(bar);
      }
      seriesRef.current.volume?.update({ time: bar.time, value: bar.volume, color: bar.close >= bar.open ? "rgba(35,133,90,0.35)" : "rgba(194,65,45,0.35)" });
      refreshIndicators();
      setLegend((l) => (!l || l.time === bar.time || l.time === arr[arr.length - 2]?.time ? { ...bar, change: arr.length > 1 ? (bar.close / arr[arr.length - 2].close - 1) * 100 : 0 } : l));
    } catch {
      /* el gráfico se está reconstruyendo */
    }
  }, [quote, symbol, tf, chartType, refreshIndicators]);

  return (
    <div className="tchart">
      {legend && (
        <div className="tchart-legend">
          <strong>{symbol}</strong>
          <span>A <b>{fmt(legend.open)}</b></span>
          <span>M <b>{fmt(legend.high)}</b></span>
          <span>m <b>{fmt(legend.low)}</b></span>
          <span>C <b>{fmt(legend.close)}</b></span>
          <span className={legend.change >= 0 ? "gain" : "loss"}>{legend.change >= 0 ? "+" : "−"}{Math.abs(legend.change).toFixed(2).replace(".", ",")} %</span>
        </div>
      )}
      {!data && !error && <div className="tchart-msg"><div className="spinner" /></div>}
      {error && <div className="tchart-msg loss">No se pudieron cargar las velas. Revisa que el backend esté activo.</div>}
      <div ref={boxRef} className={`tchart-canvas ${tool !== "cursor" ? "drawing" : ""}`} />
    </div>
  );
});

export default TradingChart;
