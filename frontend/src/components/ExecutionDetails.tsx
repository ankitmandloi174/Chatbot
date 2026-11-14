import type { AttemptTrace, ChatMessage, ExecutionTrace, StepStatus } from "../types/api";
import { formatDuration, pluralize } from "../utils/format";
import { CodeBlock } from "./CodeBlock";
import { Disclosure } from "./Disclosure";
import { ExecutionStep } from "./ExecutionStep";
import { CodeIcon, LinkIcon, ListIcon, PlayIcon, SearchIcon, ShieldIcon } from "./Icons";

const MAX_CHIPS = 12;

function totalMs(trace: ExecutionTrace): number {
  const attempts = trace.attempts.reduce((sum, a) => sum + a.duration_ms, 0);
  return trace.retrieval_ms + trace.planning_ms + attempts + trace.explain_ms;
}

function RetrievalStep({ trace }: { trace: ExecutionTrace }) {
  return (
    <ExecutionStep
      icon={<SearchIcon width={13} height={13} />}
      title="Dataset retrieval"
      status="passed"
      summary={`${trace.retrieval_method} · ${pluralize(trace.retrieved.length, "dataset")} selected`}
      duration={formatDuration(trace.retrieval_ms)}
    >
      {(trace.carried_over ?? []).length > 0 && (
        <p className="exec-note">
          Carried over from the previous answer: {trace.carried_over.join(", ")}
        </p>
      )}
      <ul className="exec-list">
        {trace.retrieved.map((dataset) => (
          <li key={dataset.table_name}>
            <span className="exec-list__name">{dataset.file_name}</span>
            <span className="muted">
              {dataset.columns.length} of {pluralize(dataset.total_columns, "column")}
            </span>
            <div className="chips">
              {dataset.columns.slice(0, MAX_CHIPS).map((column) => (
                <code key={column} className="chip">
                  {column}
                </code>
              ))}
              {dataset.columns.length > MAX_CHIPS && (
                <span className="muted">+{dataset.columns.length - MAX_CHIPS} more</span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </ExecutionStep>
  );
}

function RelationshipStep({ trace }: { trace: ExecutionTrace }) {
  const found = trace.relationships.length > 0;
  return (
    <ExecutionStep
      icon={<LinkIcon width={13} height={13} />}
      title="Relationship detection"
      status="passed"
      summary={
        found
          ? `${pluralize(trace.relationships.length, "join key")} detected between the selected datasets`
          : "No join keys between the selected datasets"
      }
    >
      {found && (
        <ul className="exec-list">
          {trace.relationships.map((rel) => (
            <li key={`${rel.left}-${rel.right}`}>
              <code>{rel.left}</code> <span className="muted">↔</span> <code>{rel.right}</code>
              <span className="muted"> · {Math.round(rel.overlap * 100)}% value overlap</span>
            </li>
          ))}
        </ul>
      )}
    </ExecutionStep>
  );
}

function PlanStep({ message, planningMs }: { message: ChatMessage; planningMs: number }) {
  const plan = message.plan;
  if (!plan) return null;
  return (
    <ExecutionStep
      icon={<ListIcon width={13} height={13} />}
      title="Analysis plan"
      status="passed"
      summary={`Output: ${plan.output_type}`}
      duration={formatDuration(planningMs)}
    >
      {plan.steps.length > 0 && (
        <ol className="exec-steps-list">
          {plan.steps.map((step, index) => (
            <li key={index}>{step}</li>
          ))}
        </ol>
      )}
      {plan.assumptions.length > 0 && (
        <p className="exec-note">Assumptions: {plan.assumptions.join(" · ")}</p>
      )}
    </ExecutionStep>
  );
}

function CodeStep({ message, attempts }: { message: ChatMessage; attempts: AttemptTrace[] }) {
  const earlier = attempts.slice(0, -1);
  return (
    <ExecutionStep
      icon={<CodeIcon width={13} height={13} />}
      title="Code generation"
      status="passed"
      summary={attempts.length > 1 ? `Needed ${attempts.length} attempts` : "Generated on the first attempt"}
    >
      {earlier.map((attempt) => (
        <details key={attempt.attempt} className="exec-attempt">
          <summary>Attempt {attempt.attempt} (not used)</summary>
          <CodeBlock code={attempt.code} />
        </details>
      ))}
      {message.code && <CodeBlock code={message.code} />}
    </ExecutionStep>
  );
}

/** Validation and execution share the same per-attempt layout. */
function AttemptStep({
  attempts,
  kind,
}: {
  attempts: AttemptTrace[];
  kind: "validation" | "execution";
}) {
  const last = attempts[attempts.length - 1];
  const status: StepStatus = last[kind];
  const isValidation = kind === "validation";
  const failedCount = attempts.filter((a) => a[kind] === "failed").length;

  let summary: string;
  if (status === "passed") {
    summary = isValidation ? "Code passed the safety checks" : "Ran in an isolated sandbox";
  } else {
    summary = status === "skipped" ? "Not run" : "Did not succeed after the last attempt";
  }
  if (failedCount > 0 && status === "passed") summary += ` · ${pluralize(failedCount, "retry", "retries")} needed`;

  return (
    <ExecutionStep
      icon={isValidation ? <ShieldIcon width={13} height={13} /> : <PlayIcon width={13} height={13} />}
      title={isValidation ? "Validation" : "Execution"}
      status={status}
      summary={summary}
      duration={isValidation ? undefined : formatDuration(attempts.reduce((s, a) => s + a.duration_ms, 0))}
    >
      {attempts
        .filter((a) => a[kind] === "failed")
        .map((attempt) => (
          <p key={attempt.attempt} className="exec-error">
            <strong>Attempt {attempt.attempt}:</strong> {attempt.error}
          </p>
        ))}
    </ExecutionStep>
  );
}

export function ExecutionDetails({ message }: { message: ChatMessage }) {
  const trace = message.trace;
  const failed = message.error !== null;

  if (!trace) {
    // Messages saved before tracing existed: show what we do have.
    return message.code ? (
      <Disclosure icon={<CodeIcon width={14} height={14} />} title="Generated code">
        <CodeBlock code={message.code} />
      </Disclosure>
    ) : null;
  }

  const meta = `${pluralize(trace.attempts.length, "attempt")} · ${formatDuration(totalMs(trace))}`;
  return (
    <Disclosure
      icon={<ListIcon width={14} height={14} />}
      title="Execution details"
      meta={meta}
      defaultOpen={failed}
    >
      <ol className="exec-timeline">
        <RetrievalStep trace={trace} />
        <RelationshipStep trace={trace} />
        <PlanStep message={message} planningMs={trace.planning_ms} />
        {trace.attempts.length > 0 && (
          <>
            <CodeStep message={message} attempts={trace.attempts} />
            <AttemptStep attempts={trace.attempts} kind="validation" />
            <AttemptStep attempts={trace.attempts} kind="execution" />
          </>
        )}
      </ol>
    </Disclosure>
  );
}
