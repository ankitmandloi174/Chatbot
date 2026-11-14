import { ChatIcon, SidebarIcon } from "./Icons";

interface TopBarProps {
  sidebarOpen: boolean;
  /** Title of the open conversation; null for a new one. */
  title: string | null;
  onOpenSidebar: () => void;
}

export function TopBar({ sidebarOpen, title, onOpenSidebar }: TopBarProps) {
  return (
    <header className="topbar">
      {!sidebarOpen && (
        <button className="icon-button" onClick={onOpenSidebar} aria-label="Open sidebar">
          <SidebarIcon />
        </button>
      )}
      <span className="topbar__mark" aria-hidden="true">
        <ChatIcon width={15} height={15} />
      </span>
      <h1 className="topbar__title" title={title ?? undefined}>
        {title ?? "New analysis"}
      </h1>
    </header>
  );
}
