import type { Conversation } from "../types/api";
import { ChatIcon, CloseIcon } from "./Icons";

interface ConversationListProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string | null) => void;
  onRemove: (id: string) => void;
}

export function ConversationList({ conversations, activeId, onSelect, onRemove }: ConversationListProps) {
  if (conversations.length === 0) return <p className="empty-note">No conversations yet.</p>;
  return (
    <ul className="nav-list">
      {conversations.map((conversation) => (
        <li key={conversation.id} className={`nav-item ${conversation.id === activeId ? "is-active" : ""}`}>
          <button className="nav-item__label" onClick={() => onSelect(conversation.id)} title={conversation.title}>
            <ChatIcon width={14} height={14} />
            <span>{conversation.title}</span>
          </button>
          <button
            className="icon-button nav-item__remove"
            onClick={() => onRemove(conversation.id)}
            aria-label={`Delete ${conversation.title}`}
          >
            <CloseIcon width={14} height={14} />
          </button>
        </li>
      ))}
    </ul>
  );
}
