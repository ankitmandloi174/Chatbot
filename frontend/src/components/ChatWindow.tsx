import { useEffect, useRef } from "react";

import type { ChatMessage, Dataset, Relationship } from "../types/api";
import { Composer } from "./Composer";
import { SparkIcon } from "./Icons";
import { MessageBubble } from "./MessageBubble";
import { WelcomeScreen } from "./WelcomeScreen";

interface ChatWindowProps {
  messages: ChatMessage[];
  sending: boolean;
  error: string | null;
  /** Datasets currently selected for analysis. */
  selectedDatasets: Dataset[];
  relationships: Relationship[];
  uploading: boolean;
  onSend: (question: string) => void;
  onUpload: (files: File[]) => void;
}

export function ChatWindow({
  messages,
  sending,
  error,
  selectedDatasets,
  relationships,
  uploading,
  onSend,
  onUpload,
}: ChatWindowProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const lastMessage = messages[messages.length - 1];

  // Show the start of a new answer (not its end) so long results are read top-down.
  useEffect(() => {
    if (!lastMessage && !sending) return;
    if (sending || lastMessage?.role === "user") {
      endRef.current?.scrollIntoView({ behavior: "smooth" });
      return;
    }
    const answers = scrollRef.current?.querySelectorAll(".bubble-row.assistant");
    answers?.[answers.length - 1]?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [messages.length, sending, lastMessage]);

  return (
    <section className="chat">
      <div className="messages" ref={scrollRef}>
        <div className="messages__inner">
          {messages.length === 0 && !sending && (
            <WelcomeScreen
              datasets={selectedDatasets}
              relationships={relationships}
              uploading={uploading}
              onAsk={onSend}
              onUpload={onUpload}
            />
          )}
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              showFollowUps={!sending && message === lastMessage}
              onFollowUp={onSend}
            />
          ))}
          {sending && (
            <div className="bubble-row assistant">
              <span className="avatar" aria-hidden="true">
                <SparkIcon width={14} height={14} />
              </span>
              <div className="thinking" role="status">
                <span className="dots" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </span>
                Retrieving data, writing and running the analysis…
              </div>
            </div>
          )}
          {error && <p className="error-text alert">{error}</p>}
          <div ref={endRef} />
        </div>
      </div>

      <Composer
        sending={sending}
        attaching={uploading}
        selectedDatasets={selectedDatasets}
        onSend={onSend}
        onAttach={onUpload}
      />
    </section>
  );
}
