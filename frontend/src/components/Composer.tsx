import { ChangeEvent, FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";

import type { Dataset } from "../types/api";
import { PaperclipIcon, SendIcon } from "./Icons";

/** Mirrors the backend's `ChatRequest.question` limit. */
const MAX_LENGTH = 2000;
const COUNTER_FROM = 1600;
const MAX_HEIGHT = 200;

interface ComposerProps {
  sending: boolean;
  attaching: boolean;
  /** Datasets the next question will run against. */
  selectedDatasets: Dataset[];
  onSend: (question: string) => void;
  onAttach: (files: File[]) => void;
}

export function Composer({ sending, attaching, selectedDatasets, onSend, onAttach }: ComposerProps) {
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const canSend = selectedDatasets.length > 0;

  // Grow with content, up to a cap.
  useEffect(() => {
    const input = inputRef.current;
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, MAX_HEIGHT)}px`;
  }, [draft]);

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    const question = draft.trim();
    if (!question || sending || !canSend) return;
    onSend(question);
    setDraft("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  };

  const onFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length) onAttach(files);
    event.target.value = "";
  };

  const placeholder = canSend ? "Ask a question about your data…" : "Upload or select a dataset to start";

  return (
    <form className="composer" onSubmit={submit}>
      <div className="composer__box">
        <textarea
          ref={inputRef}
          rows={1}
          value={draft}
          maxLength={MAX_LENGTH}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          aria-label="Question"
        />
        <div className="composer__toolbar">
          <input ref={fileRef} type="file" accept=".csv" multiple hidden onChange={onFiles} />
          <button
            type="button"
            className="composer__attach"
            onClick={() => fileRef.current?.click()}
            disabled={attaching}
            aria-label="Attach CSV files"
            title="Attach CSV files"
          >
            <PaperclipIcon width={16} height={16} />
            <span>{attaching ? "Uploading…" : "Attach CSV"}</span>
          </button>
          <span className="composer__spacer" />
          {draft.length >= COUNTER_FROM && (
            <span className="composer__count">
              {draft.length}/{MAX_LENGTH}
            </span>
          )}
          <button
            type="submit"
            className={`send-button ${sending ? "is-busy" : ""}`}
            disabled={!draft.trim() || sending || !canSend}
            aria-label={sending ? "Analysing" : "Send"}
          >
            {sending ? <span className="spinner" aria-hidden="true" /> : <SendIcon width={16} height={16} strokeWidth={2.25} />}
          </button>
        </div>
      </div>
      <p className="composer__hint">Enter to send · Shift + Enter for a new line</p>
    </form>
  );
}
