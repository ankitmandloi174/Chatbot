import { useMemo, useState } from "react";

import type { TablePayload } from "../types/api";
import { ChevronIcon, SortIcon } from "./Icons";

const PAGE_SIZE = 10;

type Direction = "asc" | "desc";

interface SortState {
  column: number;
  direction: Direction;
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "–";
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(value);
}

/** Orders two cells ascending; empty values always sort last. */
function compareCells(a: unknown, b: unknown): number {
  const aEmpty = a === null || a === undefined;
  const bEmpty = b === null || b === undefined;
  if (aEmpty || bEmpty) return Number(aEmpty) - Number(bEmpty);
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true });
}

function nextSort(current: SortState | null, column: number): SortState | null {
  if (current?.column !== column) return { column, direction: "asc" };
  return current.direction === "asc" ? { column, direction: "desc" } : null;
}

export function DataTable({ table }: { table: TablePayload }) {
  const [sort, setSort] = useState<SortState | null>(null);
  const [page, setPage] = useState(0);

  const rows = useMemo(() => {
    if (!sort) return table.rows;
    const sign = sort.direction === "asc" ? 1 : -1;
    return [...table.rows].sort((a, b) => {
      const aEmpty = a[sort.column] == null;
      const bEmpty = b[sort.column] == null;
      // Keep empty cells last regardless of direction.
      if (aEmpty || bEmpty) return compareCells(a[sort.column], b[sort.column]);
      return sign * compareCells(a[sort.column], b[sort.column]);
    });
  }, [table.rows, sort]);

  const pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const current = Math.min(page, pageCount - 1);
  const pageRows = rows.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE);

  const isNumericColumn = (index: number) => table.rows.some((row) => typeof row[index] === "number");

  return (
    <div className="table-card">
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {table.columns.map((column, index) => {
                const active = sort?.column === index;
                return (
                  <th
                    key={column}
                    className={isNumericColumn(index) ? "is-numeric" : ""}
                    aria-sort={active ? (sort.direction === "asc" ? "ascending" : "descending") : "none"}
                  >
                    <button className="th-button" onClick={() => {
                        setSort(nextSort(sort, index));
                        setPage(0);
                      }}>
                      {column}
                      <SortIcon
                        width={12}
                        height={12}
                        className={`sort-icon ${active ? `is-active is-${sort.direction}` : ""}`}
                      />
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex} className={isNumericColumn(cellIndex) ? "is-numeric" : ""}>
                    {formatCell(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-card__footer">
        <span>
          {table.truncated
            ? `Showing ${table.rows.length} of ${table.total_rows.toLocaleString()} rows`
            : `${table.total_rows.toLocaleString()} ${table.total_rows === 1 ? "row" : "rows"}`}
        </span>
        {pageCount > 1 && (
          <nav className="pager" aria-label="Table pages">
            <span className="pager__range">
              {current * PAGE_SIZE + 1}–{Math.min((current + 1) * PAGE_SIZE, rows.length)} of {rows.length}
            </span>
            <button
              className="pager__button is-prev"
              onClick={() => setPage(current - 1)}
              disabled={current === 0}
              aria-label="Previous page"
            >
              <ChevronIcon width={14} height={14} />
            </button>
            <button
              className="pager__button"
              onClick={() => setPage(current + 1)}
              disabled={current >= pageCount - 1}
              aria-label="Next page"
            >
              <ChevronIcon width={14} height={14} />
            </button>
          </nav>
        )}
      </div>
    </div>
  );
}
