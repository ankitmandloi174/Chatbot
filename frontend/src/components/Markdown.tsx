import type { ComponentProps } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const components: ComponentProps<typeof ReactMarkdown>["components"] = {
  a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />,
  // Wide tables scroll inside the message instead of stretching the layout.
  table: ({ node: _node, ...props }) => (
    <div className="markdown__table">
      <table {...props} />
    </div>
  ),
};

/** Renders LLM output as Markdown. Raw HTML is not rendered (react-markdown default). */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
