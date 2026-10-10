import React from "react";
const paths: Record<string, React.ReactNode> = {
  search: (
    <>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m16 16 4 4" />
    </>
  ),
  bag: (
    <>
      <path d="M5 8h14l1 13H4L5 8Z" />
      <path d="M8 8V6a4 4 0 0 1 8 0v2" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 22v-3a8 8 0 0 1 16 0v3" />
    </>
  ),
  arrow: (
    <>
      <path d="M4 12h16m-6-6 6 6-6 6" />
    </>
  ),
  heart: (
    <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 1 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z" />
  ),
  box: (
    <>
      <path d="m12 2 10 5v10l-10 5-10-5V7l10-5Zm0 10v10M2 7l10 5 10-5M7 4.5l10 5V15" />
    </>
  ),
  grid: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </>
  ),
  truck: (
    <>
      <path d="M1 4h13v13H1V4Zm13 5h4l4 4v4h-8" />
      <circle cx="5" cy="19" r="2" />
      <circle cx="18" cy="19" r="2" />
    </>
  ),
  check: <path d="m5 12 4 4L20 5" />,
  close: <path d="m6 6 12 12M6 18 18 6" />,
  plus: <path d="M12 5v14M5 12h14" />,
  settings: (
    <>
      <path d="M12 3v3m0 12v3M3 12h3m12 0h3M5.6 5.6l2.1 2.1m8.6 8.6 2.1 2.1M5.6 18.4l2.1-2.1m8.6-8.6 2.1-2.1" />
      <circle cx="12" cy="12" r="5" />
    </>
  ),
  chart: (
    <>
      <path d="M3 3v18h18M7 16v-4m5 4V7m5 9v-7" />
    </>
  ),
  file: (
    <>
      <path d="M5 2h9l5 5v15H5V2Zm9 0v6h5M8 12h8m-8 4h8" />
    </>
  ),
  shield: (
    <>
      <path d="M12 2 3 6v6c0 5 9 10 9 10s9-5 9-10V6l-9-4Z" />
      <path d="m8 12 3 3 5-6" />
    </>
  ),
  tag: (
    <>
      <path d="M2 3h9l11 11-8 8L2 10V3Z" />
      <circle cx="7" cy="7" r="1" />
    </>
  ),
  upload: (
    <>
      <path d="M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6" />
    </>
  ),
  logout: (
    <>
      <path d="M9 3H3v18h6m6-15 6 6-6 6m-7-6h13" />
    </>
  ),
};
export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name] || paths.box}
    </svg>
  );
}
