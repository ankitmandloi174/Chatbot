import type { ReactNode, SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

/** Builds a 24px stroke icon component from the given SVG children. */
function createIcon(children: ReactNode) {
  return function Icon(props: IconProps) {
    return (
      <svg
        width={16}
        height={16}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.75}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        {...props}
      >
        {children}
      </svg>
    );
  };
}

export const PlusIcon = createIcon(<path d="M12 5v14M5 12h14" />);
export const CloseIcon = createIcon(<path d="M6 6l12 12M18 6L6 18" />);
export const CheckIcon = createIcon(<path d="M5 12.5l4.5 4.5L19 7.5" />);
export const ChevronIcon = createIcon(<path d="M9 6l6 6-6 6" />);
export const SortIcon = createIcon(<path d="M12 5v14M7 14l5 5 5-5" />);
export const SendIcon = createIcon(<path d="M12 19V5M6 11l6-6 6 6" />);

export const SidebarIcon = createIcon(
  <>
    <rect x="3" y="4" width="18" height="16" rx="3" />
    <path d="M9 4v16" />
  </>,
);

export const TrashIcon = createIcon(
  <path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 002 2h6a2 2 0 002-2l1-12M9 7V4h6v3" />,
);

export const UploadIcon = createIcon(
  <path d="M12 16V4M7 9l5-5 5 5M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" />,
);

export const FileIcon = createIcon(
  <>
    <path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z" />
    <path d="M14 3v5h5M9 13h6M9 17h6" />
  </>,
);

export const ChatIcon = createIcon(
  <path d="M20 12a8 8 0 01-11.6 7.1L4 20l1-4A8 8 0 1120 12z" />,
);

export const SparkIcon = createIcon(
  <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z" />,
);

export const CopyIcon = createIcon(
  <>
    <rect x="9" y="9" width="11" height="11" rx="2" />
    <path d="M5 15V6a2 2 0 012-2h9" />
  </>,
);

export const PaperclipIcon = createIcon(
  <path d="M21 11l-8.6 8.6a5 5 0 01-7-7L14 4a3.3 3.3 0 014.7 4.7l-8.6 8.6a1.7 1.7 0 01-2.4-2.4L15 8" />,
);

export const SearchIcon = createIcon(
  <>
    <circle cx="11" cy="11" r="6.5" />
    <path d="M20 20l-4-4" />
  </>,
);

export const LinkIcon = createIcon(
  <path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1M14 10a4 4 0 00-5.7 0l-3 3A4 4 0 0011 18.7l1-1" />,
);

export const ListIcon = createIcon(<path d="M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01" />);

export const CodeIcon = createIcon(<path d="M8 8l-4 4 4 4M16 8l4 4-4 4M13.5 5l-3 14" />);

export const ShieldIcon = createIcon(
  <>
    <path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z" />
    <path d="M9 12l2 2 4-4" />
  </>,
);

export const PlayIcon = createIcon(<path d="M7 5l12 7-12 7z" />);

export const TableIcon = createIcon(
  <>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <path d="M3 10h18M9 4v16" />
  </>,
);

export const ChartIcon = createIcon(<path d="M4 20V4M4 20h16M8 16v-4M12 16V8M16 16v-6" />);

export const TrendIcon = createIcon(<path d="M3 17l6-6 4 4 8-8M15 7h6v6" />);

export const DatabaseIcon = createIcon(
  <>
    <ellipse cx="12" cy="6" rx="7" ry="3" />
    <path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" />
  </>,
);

export const ArrowUpRightIcon = createIcon(<path d="M7 17L17 7M8 7h9v9" />);
