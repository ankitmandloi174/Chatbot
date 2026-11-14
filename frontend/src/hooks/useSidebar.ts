import { useCallback, useState } from "react";

const STORAGE_KEY = "sidebar-open";
const MOBILE_BREAKPOINT = 800;

interface UseSidebar {
  open: boolean;
  toggle: () => void;
  close: () => void;
}

function readInitialState(): boolean {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored !== null) return stored === "true";
  } catch {
    // Storage can be unavailable (private mode); fall back to the viewport default.
  }
  return window.innerWidth > MOBILE_BREAKPOINT;
}

function persist(open: boolean): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, String(open));
  } catch {
    // Ignore: persisting the preference is best-effort.
  }
}

/** Collapsible sidebar state, remembered across reloads. */
export function useSidebar(): UseSidebar {
  const [open, setOpen] = useState(readInitialState);

  const update = useCallback((next: boolean) => {
    setOpen(next);
    persist(next);
  }, []);

  const toggle = useCallback(() => update(!open), [open, update]);
  const close = useCallback(() => update(false), [update]);

  return { open, toggle, close };
}
