import type { UseChat } from "../hooks/useChat";
import type { UseDatasets } from "../hooks/useDatasets";
import { ConversationList } from "./ConversationList";
import { DatasetList } from "./DatasetList";
import { PlusIcon, SidebarIcon, SparkIcon } from "./Icons";
import { UploadPanel } from "./UploadPanel";

/** Static profile shown in the sidebar footer (there is no authentication yet). */
const CURRENT_USER = { name: "Ankit Mandloi", initials: "AM" };

interface SidebarProps {
  datasets: UseDatasets;
  chat: UseChat;
  onCollapse: () => void;
  /** Called after the user picks a conversation so mobile can dismiss the drawer. */
  onNavigate: () => void;
}

export function Sidebar({ datasets, chat, onCollapse, onNavigate }: SidebarProps) {
  const startNewChat = () => {
    void chat.select(null);
    onNavigate();
  };

  const openConversation = (id: string | null) => {
    void chat.select(id);
    onNavigate();
  };

  return (
    <aside className="sidebar" aria-label="Sidebar">
      <div className="sidebar__inner">
        <header className="sidebar__header">
          <div className="brand">
            <span className="brand__mark">
              <SparkIcon width={14} height={14} />
            </span>
            <span className="brand__name">CSV Chat Analyst</span>
          </div>
          <button className="icon-button" onClick={onCollapse} aria-label="Collapse sidebar">
            <SidebarIcon />
          </button>
        </header>

        <button className="button button--primary button--block" onClick={startNewChat}>
          <PlusIcon /> New chat
        </button>

        <div className="sidebar__sections">
          <section className="section section--datasets">
            <h2 className="section__title">
              Datasets
              {datasets.datasets.length > 0 && <span className="count">{datasets.datasets.length}</span>}
            </h2>
            <UploadPanel
              uploading={datasets.uploading}
              error={datasets.error}
              failures={datasets.failures}
              onUpload={datasets.upload}
            />
            <div className="section__scroll">
              <DatasetList
                datasets={datasets.datasets}
                onRemove={datasets.remove}
              />
            </div>
          </section>

          <section className="section section--conversations">
            <h2 className="section__title">
              Conversations
              {chat.conversations.length > 0 && <span className="count">{chat.conversations.length}</span>}
            </h2>
            <div className="section__scroll">
              <ConversationList
                conversations={chat.conversations}
                activeId={chat.activeId}
                onSelect={openConversation}
                onRemove={chat.remove}
              />
            </div>
          </section>
        </div>

        <footer className="user-card">
          <span className="user-card__avatar" aria-hidden="true">
            {CURRENT_USER.initials}
          </span>
          <span className="user-card__name">{CURRENT_USER.name}</span>
        </footer>
      </div>
    </aside>
  );
}
