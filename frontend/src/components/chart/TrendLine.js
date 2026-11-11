/**
 * Primitiva de dibujo: línea de tendencia entre dos puntos (tiempo, precio),
 * opcionalmente extendida hacia la derecha. Se dibuja sobre el lienzo del gráfico.
 */

class TrendLineRenderer {
  constructor(p1, p2, options) {
    this._p1 = p1;
    this._p2 = p2;
    this._o = options;
  }

  draw(target) {
    target.useBitmapCoordinateSpace((scope) => {
      const { _p1: p1, _p2: p2, _o: o } = this;
      if (p1.x === null || p1.y === null || p2.x === null || p2.y === null) return;
      const ctx = scope.context;
      const hr = scope.horizontalPixelRatio;
      const vr = scope.verticalPixelRatio;
      let x2 = p2.x, y2 = p2.y;
      if (o.extend && p2.x !== p1.x) {
        const slope = (p2.y - p1.y) / (p2.x - p1.x);
        const right = scope.mediaSize.width;
        if (p2.x > p1.x) {
          x2 = right;
          y2 = p1.y + slope * (right - p1.x);
        }
      }
      ctx.lineWidth = o.width * hr;
      ctx.strokeStyle = o.color;
      ctx.beginPath();
      ctx.moveTo(p1.x * hr, p1.y * vr);
      ctx.lineTo(x2 * hr, y2 * vr);
      ctx.stroke();
      ctx.fillStyle = o.color;
      for (const p of [p1, p2]) {
        ctx.beginPath();
        ctx.arc(p.x * hr, p.y * vr, 3.5 * hr, 0, Math.PI * 2);
        ctx.fill();
      }
    });
  }
}

class TrendLinePaneView {
  constructor(source) {
    this._source = source;
    this._p1 = { x: null, y: null };
    this._p2 = { x: null, y: null };
  }

  update() {
    const s = this._source;
    if (!s._chart || !s._series) return;
    const ts = s._chart.timeScale();
    this._p1 = { x: ts.timeToCoordinate(s._a.time), y: s._series.priceToCoordinate(s._a.price) };
    this._p2 = { x: ts.timeToCoordinate(s._b.time), y: s._series.priceToCoordinate(s._b.price) };
  }

  renderer() {
    return new TrendLineRenderer(this._p1, this._p2, this._source._options);
  }
}

export class TrendLine {
  constructor(a, b, options = {}) {
    this._a = a;
    this._b = b;
    this._options = { color: "#d99a1e", width: 2, extend: true, ...options };
    this._paneViews = [new TrendLinePaneView(this)];
  }

  attached({ chart, series, requestUpdate }) {
    this._chart = chart;
    this._series = series;
    this._requestUpdate = requestUpdate;
    this.updateAllViews();
  }

  detached() {
    this._chart = null;
    this._series = null;
  }

  updateAllViews() {
    this._paneViews.forEach((v) => v.update());
  }

  paneViews() {
    return this._paneViews;
  }
}
