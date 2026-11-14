import type { ColumnMeta, Dataset, Relationship } from "../types/api";
import { humanize } from "./format";

export type SuggestionCategory = "Overview" | "Trend" | "Compare" | "Cross-file" | "Distribution" | "Ranking";

export interface Suggestion {
  category: SuggestionCategory;
  question: string;
}

const MAX_SUGGESTIONS = 6;
const MAX_GROUPS = 12; // a category with more distinct values is not a useful breakdown
const ID_LIKE = /(^|_)id$/;

const words = (column: string) => humanize(column).toLowerCase();

// A fully-unique integer column is an identifier, not something to aggregate.
const isMeasure = (c: ColumnMeta, rows: number) =>
  !ID_LIKE.test(c.name) && (c.kind === "numeric" || (c.kind === "integer" && c.unique_count < rows));

const isDimension = (c: ColumnMeta) =>
  c.kind === "categorical" && c.unique_count >= 2 && c.unique_count <= MAX_GROUPS;

interface Profile {
  dataset: Dataset;
  label: string;
  measure?: ColumnMeta;
  dimension?: ColumnMeta;
  date?: ColumnMeta;
}

function profile(dataset: Dataset): Profile {
  const { columns, row_count } = dataset;
  return {
    dataset,
    label: dataset.table_name.replace(/_/g, " "),
    measure: columns.find((c) => isMeasure(c, row_count)),
    dimension: columns.find(isDimension),
    date: columns.find((c) => c.kind === "datetime"),
  };
}

function singleDataset({ label, measure, dimension, date }: Profile, scoped: boolean): Suggestion[] {
  const where = scoped ? ` in ${label}` : "";
  const out: Suggestion[] = [];
  if (measure && date) {
    out.push({ category: "Trend", question: `Show the monthly trend of ${words(measure.name)}${where}` });
  }
  if (measure && dimension) {
    out.push({
      category: "Compare",
      question: `Compare total ${words(measure.name)} by ${words(dimension.name)}${where}`,
    });
    out.push({
      category: "Ranking",
      question: `Which ${words(dimension.name)} has the highest ${words(measure.name)}${where}?`,
    });
  }
  if (measure) {
    out.push({ category: "Distribution", question: `What is the distribution of ${words(measure.name)}${where}?` });
  }
  return out;
}

function crossFile(profiles: Profile[], relationships: Relationship[]): Suggestion | null {
  const byId = new Map(profiles.map((p) => [p.dataset.id, p]));
  for (const rel of relationships) {
    const left = byId.get(rel.left_dataset_id);
    const right = byId.get(rel.right_dataset_id);
    if (!left || !right) continue;
    const measures = [left.measure, right.measure].filter((m): m is ColumnMeta => m !== undefined);
    const detail = measures.length ? ` ${measures.map((m) => words(m.name)).join(" and ")}` : "";
    return {
      category: "Cross-file",
      question: `Combine ${left.label} and ${right.label} on ${words(rel.left_column)} and compare${detail}`,
    };
  }
  return null;
}

/**
 * Builds starter questions from the selected datasets' real columns, so every
 * suggestion refers to data that exists. Returns at most six, varied by category.
 */
export function buildSuggestions(datasets: Dataset[], relationships: Relationship[]): Suggestion[] {
  if (datasets.length === 0) return [];
  const profiles = datasets.map(profile);
  const scoped = datasets.length > 1;

  const suggestions: Suggestion[] = [
    {
      category: "Overview",
      question: scoped
        ? "Give me an overview of the key insights across my datasets"
        : `Summarize the key insights in ${profiles[0].label}`,
    },
  ];
  const cross = crossFile(profiles, relationships);
  if (cross) suggestions.push(cross);

  // Round-robin across datasets so one file does not crowd out the rest.
  const perDataset = profiles.map((p) => singleDataset(p, scoped));
  for (let i = 0; perDataset.some((list) => i < list.length); i++) {
    for (const list of perDataset) if (i < list.length) suggestions.push(list[i]);
  }

  const seen = new Set<string>();
  return suggestions.filter((s) => !seen.has(s.question) && seen.add(s.question)).slice(0, MAX_SUGGESTIONS);
}
