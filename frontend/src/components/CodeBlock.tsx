import { useState } from "react";

import { CheckIcon, CopyIcon } from "./Icons";

const COPIED_MS = 1600;

export function CodeBlock({ code, language = "python" }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), COPIED_MS);
    } catch {
      // Clipboard can be unavailable (insecure context); the code stays selectable.
    }
  };

  return (
    <div className="code-block">
      <div className="code-block__bar">
        <span>{language}</span>
        <button className="code-block__copy" onClick={copy} aria-label="Copy code">
          {copied ? <CheckIcon width={13} height={13} /> : <CopyIcon width={13} height={13} />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre>
        <code>{code}</code>
      </pre>
    </div>
  );
}
