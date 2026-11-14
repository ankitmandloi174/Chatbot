import { ChatWindow } from "./components/ChatWindow";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { useChat } from "./hooks/useChat";
import { useDatasets } from "./hooks/useDatasets";
import { useSidebar } from "./hooks/useSidebar";

const MOBILE_QUERY = "(max-width: 800px)";

export default function App() {
  const datasets = useDatasets();
  const chat = useChat();
  const sidebar = useSidebar();

  // On small screens the sidebar is an overlay drawer, so close it after navigating.
  const dismissOnMobile = () => {
    if (window.matchMedia(MOBILE_QUERY).matches) sidebar.close();
  };

  return (
    <div className="app" data-sidebar={sidebar.open ? "open" : "closed"}>
      <Sidebar datasets={datasets} chat={chat} onCollapse={sidebar.close} onNavigate={dismissOnMobile} />
      <div className="backdrop" onClick={sidebar.close} aria-hidden="true" />
      <main className="main">
        <TopBar
          sidebarOpen={sidebar.open}
          title={chat.conversations.find((c) => c.id === chat.activeId)?.title ?? null}
          onOpenSidebar={sidebar.toggle}
        />
        <ChatWindow
          messages={chat.messages}
          sending={chat.sending}
          error={chat.error}
          selectedDatasets={datasets.datasets}
          relationships={datasets.relationships}
          uploading={datasets.uploading}
          onSend={(question) => chat.send(question, datasets.datasets.map((d) => d.id))}
          onUpload={datasets.upload}
        />
      </main>
    </div>
  );
}
