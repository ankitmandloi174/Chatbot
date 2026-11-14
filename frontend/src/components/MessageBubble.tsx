import type { ChatMessage } from "../types/api";
import { AssistantMessage } from "./AssistantMessage";

interface MessageBubbleProps {
  message: ChatMessage;
  showFollowUps: boolean;
  onFollowUp: (question: string) => void;
}

export function MessageBubble({ message, showFollowUps, onFollowUp }: MessageBubbleProps) {
  if (message.role === "assistant") {
    return <AssistantMessage message={message} showFollowUps={showFollowUps} onFollowUp={onFollowUp} />;
  }
  return (
    <div className="bubble-row user">
      <div className="bubble">
        <p className="bubble-text">{message.content}</p>
      </div>
    </div>
  );
}
