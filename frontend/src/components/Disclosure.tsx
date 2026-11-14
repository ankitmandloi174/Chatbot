import { useId, useState } from "react";
import type { ReactNode } from "react";

import { ChevronIcon } from "./Icons";

interface DisclosureProps {
  icon: ReactNode;
  title: string;
  /** Short summary shown on the right of the header. */
  meta?: ReactNode;
  defaultOpen?: boolean;
  children: ReactNode;
}

/** A titled card whose body can be collapsed. */
export function Disclosure({ icon, title, meta, defaultOpen = false, children }: DisclosureProps) {
  const [open, setOpen] = useState(defaultOpen);
  const bodyId = useId();

  return (
    <section className={`disclosure ${open ? "is-open" : ""}`}>
      <button className="disclosure__header" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls={bodyId}>
        <span className="disclosure__icon">{icon}</span>
        <span className="disclosure__title">{title}</span>
        {meta && <span className="disclosure__meta">{meta}</span>}
        <ChevronIcon className="disclosure__chevron" width={14} height={14} />
      </button>
      <div className="disclosure__body" id={bodyId} role="region" aria-label={title}>
        <div className="disclosure__inner">{children}</div>
      </div>
    </section>
  );
}
