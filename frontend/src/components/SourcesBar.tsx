import { useState } from "react";

import type { Source } from "../types/api";
import { pluralize } from "../utils/format";
import { ChevronIcon, DatabaseIcon, FileIcon } from "./Icons";

const COLLAPSED_COLUMNS = 4;
const COLLAPSED_DATASETS = 3;

/** Datasets and columns the generated code actually referenced, grouped per CSV. */
export function SourcesBar({ sources }: { sources: Source[] }) {
  const [expanded, setExpanded] = useState(false);
  const hiddenDatasets = Math.max(0, sources.length - COLLAPSED_DATASETS);
  const hasOverflow = hiddenDatasets > 0 || sources.some((s) => s.columns.length > COLLAPSED_COLUMNS);
  const visible = expanded ? sources : sources.slice(0, COLLAPSED_DATASETS);

  return (
    <section className="sources" aria-label="Data used">
      <header className="sources__header">
        <DatabaseIcon width={14} height={14} />
        <span className="sources__title">Data used</span>
        <span className="sources__count">{pluralize(sources.length, "dataset")}</span>
        {hasOverflow && (
          <button className="sources__toggle" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}>
            {expanded ? "Show less" : "Show all columns"}
            <ChevronIcon width={12} height={12} className={expanded ? "is-open" : ""} />
          </button>
        )}
      </header>
      <ul className="sources__list">
        {visible.map((source) => {
          const shown = expanded ? source.columns : source.columns.slice(0, COLLAPSED_COLUMNS);
          const extra = source.columns.length - shown.length;
          return (
            <li key={source.table_name} className="source">
              <span className="source__file" title={source.file_name}>
                <FileIcon width={14} height={14} />
                <span className="source__name">{source.file_name}</span>
              </span>
              <span className="source__columns">
                {shown.map((column) => (
                  <code key={column} className="source__column">
                    {column}
                  </code>
                ))}
                {extra > 0 && <span className="source__more">+{extra} more</span>}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
