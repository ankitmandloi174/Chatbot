import { useRef } from "react";
import type { ChangeEvent, ReactNode } from "react";

import type { Dataset, Relationship } from "../types/api";
import { buildSuggestions } from "../utils/suggestions";
import type { SuggestionCategory } from "../utils/suggestions";
import {
  ChartIcon,
  LinkIcon,
  ListIcon,
  SparkIcon,
  TrendIcon,
  UploadIcon,
} from "./Icons";

const CATEGORY_ICON: Record<SuggestionCategory, ReactNode> = {
  Overview: <ListIcon width={15} height={15} />,
  Trend: <TrendIcon width={15} height={15} />,
  Compare: <ChartIcon width={15} height={15} />,
  "Cross-file": <LinkIcon width={15} height={15} />,
  Distribution: <ChartIcon width={15} height={15} />,
  Ranking: <TrendIcon width={15} height={15} />,
};

interface WelcomeScreenProps {
  datasets: Dataset[];
  relationships: Relationship[];
  uploading: boolean;
  onAsk: (question: string) => void;
  onUpload: (files: File[]) => void;
}

export function WelcomeScreen({ datasets, relationships, uploading, onAsk, onUpload }: WelcomeScreenProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const suggestions = buildSuggestions(datasets, relationships);

  const onFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length) onUpload(files);
    event.target.value = "";
  };

  return (
    <div className="welcome">
      <span className="welcome__mark">
        <SparkIcon width={22} height={22} />
      </span>
      <h2>What would you like to learn from your data?</h2>

      {datasets.length === 0 ? (
        <>
          <p className="muted welcome__lead">
            Upload one or more CSV files, then ask questions in plain English. Answers are computed from your
            data, with charts and the full analysis steps shown.
          </p>
          <input ref={fileRef} type="file" accept=".csv" multiple hidden onChange={onFiles} />
          <button className="button button--primary" onClick={() => fileRef.current?.click()} disabled={uploading}>
            <UploadIcon width={15} height={15} />
            {uploading ? "Uploading & cleaning…" : "Upload CSV files"}
          </button>
        </>
      ) : (
        <>
          <p className="muted welcome__lead">
            Pick a suggestion built from your columns, or write your own question below.
          </p>
          <div className="suggestions">
            {suggestions.map((suggestion) => (
              <button key={suggestion.question} className="suggestion" onClick={() => onAsk(suggestion.question)}>
                <span className="suggestion__category">
                  {CATEGORY_ICON[suggestion.category]}
                  {suggestion.category}
                </span>
                <span className="suggestion__text">{suggestion.question}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
