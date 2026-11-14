import type { Kpi } from "../types/api";
import { formatNumber, humanize } from "../utils/format";

/** Headline numbers taken directly from the computed result. */
export function MetricCards({ kpis }: { kpis: Kpi[] }) {
  return (
    <div className="metrics">
      {kpis.map((kpi) => (
        <div key={kpi.label} className="metric" title={String(kpi.value)}>
          <span className="metric__label">{humanize(kpi.label)}</span>
          <span className="metric__value">{formatNumber(kpi.value, true)}</span>
        </div>
      ))}
    </div>
  );
}
