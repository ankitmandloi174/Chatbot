import type { ReactNode } from "react";

import { ChartIcon, ListIcon, SearchIcon, SparkIcon, TrendIcon } from "./Icons";

interface FollowUpsProps {
  questions: string[];
  onSelect: (question: string) => void;
}

const ICON_RULES: Array<[RegExp, ReactNode]> = [
  [/trend|month|week|year|over time|daily|quarter/i, <TrendIcon width={14} height={14} />],
  [/top|highest|lowest|rank|best|worst/i, <ListIcon width={14} height={14} />],
  [/break|by |compare|versus|vs\b|distribution|share/i, <ChartIcon width={14} height={14} />],
  [/which|what|who|how many|why/i, <SearchIcon width={14} height={14} />],
];

const iconFor = (question: string): ReactNode =>
  ICON_RULES.find(([pattern]) => pattern.test(question))?.[1] ?? <SparkIcon width={14} height={14} />;

/** Suggested next questions as pill buttons in a horizontally scrollable row. */
export function FollowUps({ questions, onSelect }: FollowUpsProps) {
  return (
    <div className="followups">
      <span className="followups__label">Suggested follow-ups</span>
      <div className="followups__list" role="list">
        {questions.map((question) => (
          <button key={question} role="listitem" className="followup" onClick={() => onSelect(question)}>
            <span className="followup__icon">{iconFor(question)}</span>
            <span className="followup__text">{question}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
