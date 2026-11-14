import { ChangeEvent, DragEvent, KeyboardEvent, useRef, useState } from "react";

import type { UploadFailure } from "../types/api";
import { UploadIcon } from "./Icons";

interface UploadPanelProps {
  uploading: boolean;
  error: string | null;
  failures: UploadFailure[];
  onUpload: (files: File[]) => void;
}

export function UploadPanel({ uploading, error, failures, onUpload }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleFiles = (list: FileList | null) => {
    const files = Array.from(list ?? []);
    if (files.length) onUpload(files);
  };

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    handleFiles(event.dataTransfer.files);
  };

  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    handleFiles(event.target.files);
    event.target.value = "";
  };

  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      inputRef.current?.click();
    }
  };

  const classes = ["dropzone", dragging && "is-dragging", uploading && "is-uploading"]
    .filter(Boolean)
    .join(" ");

  return (
    <div>
      <div
        className={classes}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        onKeyDown={onKeyDown}
        role="button"
        tabIndex={0}
        aria-busy={uploading}
      >
        <input ref={inputRef} type="file" accept=".csv" multiple hidden onChange={onChange} />
        <span className="dropzone__icon">
          <UploadIcon width={18} height={18} />
        </span>
        <span className="dropzone__title">
          {uploading ? "Uploading & cleaning…" : dragging ? "Drop to upload" : "Upload CSV files"}
        </span>
        <span className="dropzone__hint">Drag & drop or click to browse</span>
        {uploading && <span className="dropzone__progress" />}
      </div>
      {error && <p className="error-text">{error}</p>}
      {failures.map((failure) => (
        <p key={failure.filename} className="error-text">
          {failure.filename}: {failure.error}
        </p>
      ))}
    </div>
  );
}
