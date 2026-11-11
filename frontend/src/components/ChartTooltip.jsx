/** Tooltip genérico para Recharts. `rows`: [{ key, label, format, color }] */
export default function ChartTooltip({ active, payload, label, rows, labelFormat }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div className="t">{labelFormat ? labelFormat(label, p) : label}</div>
      {rows.map((r) =>
        p[r.key] === undefined || p[r.key] === null ? null : (
          <div key={r.key}>
            {r.color && <span className="dot" style={{ background: r.color, width: 8, height: 8, marginRight: 6 }} />}
            {r.label}: <strong>{r.format ? r.format(p[r.key], p) : p[r.key]}</strong>
          </div>
        )
      )}
    </div>
  );
}
