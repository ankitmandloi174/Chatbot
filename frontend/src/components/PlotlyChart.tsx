import Plotly from "plotly.js-dist-min";
import createPlotlyComponent from "react-plotly.js/factory";

import { useColorScheme } from "../hooks/useColorScheme";
import { applyPlotlyTheme } from "../theme/plotlyTheme";
import type { PlotlyFigure } from "../types/api";

// Vite may wrap the CJS factory in a `default` export.
const factory = (createPlotlyComponent as { default?: unknown }).default ?? createPlotlyComponent;
const Plot = (factory as (p: unknown) => React.ComponentType<Record<string, unknown>>)(Plotly);

interface PlotlyChartProps {
  figure: PlotlyFigure;
}

export function PlotlyChart({ figure }: PlotlyChartProps) {
  const scheme = useColorScheme();
  return (
    <div className="chart">
      <Plot
        data={figure.data}
        layout={applyPlotlyTheme(figure.layout, scheme)}
        config={{ responsive: true, displaylogo: false }}
        useResizeHandler
        style={{ width: "100%" }}
      />
    </div>
  );
}
