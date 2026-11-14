import { Suspense, lazy } from "react";

import type { ChatMessage } from "../types/api";
import { pluralize } from "../utils/format";
import { DataTable } from "./DataTable";
import { Disclosure } from "./Disclosure";
import { ExecutionDetails } from "./ExecutionDetails";
import { FollowUps } from "./FollowUps";
import { SparkIcon, TableIcon } from "./Icons";
import { Markdown } from "./Markdown";
import { MetricCards } from "./MetricCards";
import { SourcesBar } from "./SourcesBar";

// Plotly is large; load it only when a chart is first rendered.
const PlotlyChart = lazy(() =>
  import("./PlotlyChart").then((module) => ({ default: module.PlotlyChart })),
);

interface AssistantMessageProps {
  message: ChatMessage;
  /** Follow-up suggestions are only offered on the latest answer. */
  showFollowUps: boolean;
  onFollowUp: (question: string) => void;
}

export function AssistantMessage({ message, showFollowUps, onFollowUp }: AssistantMessageProps) {
  const failed = message.error !== null;
  const hasHeadline = message.kpis.length > 0 || message.charts.length > 0;

  return (
    <div className="bubble-row assistant">
      <span className="avatar" aria-hidden="true">
        <SparkIcon width={14} height={14} />
      </span>
      <div className="answer">
        {message.kpis.length > 0 && <MetricCards kpis={message.kpis} />}

        <div className={`card answer__text ${failed ? "is-error" : ""}`}>
          <Markdown>{message.content}</Markdown>
        </div>

        {message.charts.map((figure, index) => (
          <Suspense key={index} fallback={<div className="chart-skeleton" aria-label="Loading chart" />}>
            <PlotlyChart figure={figure} />
          </Suspense>
        ))}

        {message.tables.map((table, index) => (
          <Disclosure
            key={index}
            icon={<TableIcon width={14} height={14} />}
            title="Data table"
            meta={`${pluralize(table.total_rows, "row")} × ${pluralize(table.columns.length, "column")}`}
            defaultOpen={!hasHeadline}
          >
            <DataTable table={table} />
          </Disclosure>
        ))}

        {message.sources.length > 0 && <SourcesBar sources={message.sources} />}
        <ExecutionDetails message={message} />

        {showFollowUps && message.followups.length > 0 && (
          <FollowUps questions={message.followups} onSelect={onFollowUp} />
        )}
      </div>
    </div>
  );
}
