import type { ColorScheme } from "../hooks/useColorScheme";

interface Palette {
  text: string;
  muted: string;
  grid: string;
  tooltipBg: string;
  tooltipBorder: string;
}

const PALETTES: Record<ColorScheme, Palette> = {
  dark: {
    text: "#ededef",
    muted: "#8b8b96",
    grid: "rgba(255,255,255,0.07)",
    tooltipBg: "#1b1b21",
    tooltipBorder: "rgba(255,255,255,0.12)",
  },
  light: {
    text: "#18181b",
    muted: "#6b6b76",
    grid: "rgba(0,0,0,0.07)",
    tooltipBg: "#ffffff",
    tooltipBorder: "rgba(0,0,0,0.12)",
  },
};

const COLORWAY = ["#6d5dfc", "#a78bfa", "#38bdf8", "#34d399", "#fbbf24", "#f472b6", "#fb923c", "#22d3ee"];

type Layout = Record<string, unknown>;

function themedAxis(axis: unknown, palette: Palette): Layout {
  return {
    ...(axis as Layout | undefined),
    gridcolor: palette.grid,
    zerolinecolor: palette.grid,
    linecolor: palette.grid,
    tickfont: { color: palette.muted, size: 11 },
    automargin: true,
    zeroline: false,
  };
}

/**
 * Applies the app's visual language to a backend-generated Plotly layout.
 * Content (titles, axis labels, ranges) is preserved; only styling is overridden.
 */
export function applyPlotlyTheme(layout: Layout | undefined, scheme: ColorScheme): Layout {
  const palette = PALETTES[scheme];
  return {
    ...layout,
    template: undefined,
    autosize: true,
    height: 420,
    margin: { t: 56, r: 20, b: 72, l: 64 },
    title: layout?.title ? { x: 0.01, xanchor: "left", ...(layout.title as Layout) } : undefined,
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    colorway: COLORWAY,
    font: {
      family: "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif",
      color: palette.text,
      size: 12,
    },
    xaxis: themedAxis(layout?.xaxis, palette),
    yaxis: themedAxis(layout?.yaxis, palette),
    legend: {
      orientation: "h",
      x: 0.5,
      xanchor: "center",
      y: -0.22,
      yanchor: "top",
      ...(layout?.legend as Layout | undefined),
      font: { color: palette.muted },
    },
    hovermode: "closest",
    hoverlabel: {
      bgcolor: palette.tooltipBg,
      bordercolor: palette.tooltipBorder,
      font: { color: palette.text },
    },
  };
}
