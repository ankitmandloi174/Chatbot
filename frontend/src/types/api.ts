export interface ColumnMeta {
  name: string;
  dtype: string;
  kind: string;
  null_count: number;
  unique_count: number;
  min: number | string | null;
  max: number | string | null;
  mean: number | null;
  samples: string[];
}

export interface CleaningReport {
  rows_before: number;
  rows_after: number;
  duplicates_removed: number;
  empty_rows_removed: number;
  dropped_columns: string[];
  renamed_columns: Record<string, string>;
  type_conversions: Record<string, string>;
  missing_filled: Record<string, string>;
  missing_left: Record<string, number>;
  outliers_flagged: Record<string, number>;
}

export interface Dataset {
  id: string;
  name: string;
  table_name: string;
  row_count: number;
  column_count: number;
  columns: ColumnMeta[];
  cleaning_report: CleaningReport;
  created_at: string;
}

export interface Relationship {
  left_dataset_id: string;
  left_column: string;
  right_dataset_id: string;
  right_column: string;
  overlap: number;
}

export interface UploadFailure {
  filename: string;
  error: string;
}

export interface UploadResponse {
  datasets: Dataset[];
  failures: UploadFailure[];
  relationships: Relationship[];
}

export interface TablePayload {
  columns: string[];
  rows: unknown[][];
  total_rows: number;
  truncated: boolean;
}

/** A Plotly figure as serialised by `fig.to_json()`. */
export interface PlotlyFigure {
  data: Record<string, unknown>[];
  layout?: Record<string, unknown>;
}

export interface Kpi {
  label: string;
  value: number;
}

/** A dataset the generated code used, and the columns it referenced. */
export interface Source {
  table_name: string;
  file_name: string;
  columns: string[];
}

export type StepStatus = "passed" | "failed" | "skipped";

export interface AttemptTrace {
  attempt: number;
  code: string;
  validation: StepStatus;
  execution: StepStatus;
  error: string | null;
  duration_ms: number;
}

export interface ExecutionTrace {
  retrieval_method: string;
  /** `table.column` entries reused from the previous answer. */
  carried_over: string[];
  retrieved: { table_name: string; file_name: string; columns: string[]; total_columns: number }[];
  relationships: { left: string; right: string; overlap: number }[];
  attempts: AttemptTrace[];
  retrieval_ms: number;
  planning_ms: number;
  explain_ms: number;
}

/** The structured plan produced by the analysis planner. */
export interface AnalysisPlan {
  output_type: string;
  datasets: string[];
  steps: string[];
  assumptions: string[];
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  tables: TablePayload[];
  charts: PlotlyFigure[];
  code: string | null;
  plan: AnalysisPlan | null;
  attempts: number;
  error: string | null;
  kpis: Kpi[];
  sources: Source[];
  trace: ExecutionTrace | null;
  followups: string[];
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
}
