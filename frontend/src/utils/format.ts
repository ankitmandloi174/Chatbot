const NUMBER = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 });
const COMPACT = new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 2 });
const COMPACT_THRESHOLD = 1e7;

/** `total_revenue` -> `Total revenue`. */
export function humanize(name: string): string {
  const text = name.replace(/_+/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Full-precision value for tooltips/tables; compact for headline metrics. */
export function formatNumber(value: number, compact = false): string {
  return compact && Math.abs(value) >= COMPACT_THRESHOLD ? COMPACT.format(value) : NUMBER.format(value);
}

export function formatDuration(ms: number): string {
  if (ms < 1) return "<1 ms";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(ms < 10_000 ? 1 : 0)} s`;
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count.toLocaleString()} ${count === 1 ? singular : plural}`;
}
