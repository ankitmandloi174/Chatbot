import type { ReactNode } from "react";

import type { StepStatus } from "../types/api";
import { CheckIcon, CloseIcon } from "./Icons";

interface ExecutionStepProps {
  icon: ReactNode;
  title: string;
  status: StepStatus;
  /** One-line summary shown under the title. */
  summary?: string;
  /** Right-aligned timing, e.g. "120 ms". */
  duration?: string;
  children?: ReactNode;
}

const STATUS_LABEL: Record<StepStatus, string> = {
  passed: "Completed",
  failed: "Failed",
  skipped: "Skipped",
};

/** One row of the execution timeline. */
export function ExecutionStep({ icon, title, status, summary, duration, children }: ExecutionStepProps) {
  return (
    <li className={`exec-step is-${status}`}>
      <span className="exec-step__marker" role="img" aria-label={STATUS_LABEL[status]}>
        {status === "passed" && <CheckIcon width={11} height={11} strokeWidth={2.5} />}
        {status === "failed" && <CloseIcon width={11} height={11} strokeWidth={2.5} />}
      </span>
      <div className="exec-step__content">
        <div className="exec-step__head">
          <span className="exec-step__icon">{icon}</span>
          <span className="exec-step__title">{title}</span>
          {duration && <span className="exec-step__duration">{duration}</span>}
        </div>
        {summary && <p className="exec-step__summary">{summary}</p>}
        {children}
      </div>
    </li>
  );
}
