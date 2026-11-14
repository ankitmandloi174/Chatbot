import { useState } from "react";

import type { Dataset } from "../types/api";
import { ChevronIcon, FileIcon, TrashIcon } from "./Icons";

interface DatasetCardProps {
  dataset: Dataset;
  onRemove: (id: string) => void;
}

function cleaningSummary(dataset: Dataset): string {
  const report = dataset.cleaning_report;
  const parts: string[] = [];
  if (report.duplicates_removed) parts.push(`${report.duplicates_removed} duplicates removed`);
  const filled = Object.keys(report.missing_filled).length;
  if (filled) parts.push(`${filled} columns with missing values filled`);
  const outliers = Object.keys(report.outliers_flagged).length;
  if (outliers) parts.push(`${outliers} columns with outliers flagged`);
  return parts.join(" · ");
}

export function DatasetCard({ dataset, onRemove }: DatasetCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <li className="dataset-card">
      <div className="dataset-card__row">
        <div className="dataset-card__select">
          <span className="dataset-card__text">
            <span className="dataset-card__name" title={dataset.name}>
              {dataset.name}
            </span>
            <span className="dataset-card__meta">
              <FileIcon width={12} height={12} />
              {dataset.row_count.toLocaleString()} rows · {dataset.column_count} columns
            </span>
          </span>
        </div>
        <div className="dataset-card__actions">
          <button
            className="icon-button"
            onClick={() => onRemove(dataset.id)}
            aria-label={`Delete ${dataset.name}`}
          >
            <TrashIcon />
          </button>
          <button
            className={`icon-button chevron ${expanded ? "is-open" : ""}`}
            onClick={() => setExpanded((value) => !value)}
            aria-expanded={expanded}
            aria-label={`${expanded ? "Hide" : "Show"} details for ${dataset.name}`}
          >
            <ChevronIcon />
          </button>
        </div>
      </div>
      <div className={`collapsible ${expanded ? "is-open" : ""}`}>
        <div className="collapsible__inner">
          <p className="dataset-card__cleaning">{cleaningSummary(dataset) || "No cleaning needed"}</p>
          <ul className="column-list">
            {dataset.columns.map((column) => (
              <li key={column.name}>
                <code>{column.name}</code>
                <span className="kind-tag">{column.kind}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </li>
  );
}
