export type ViewMode = "table" | "cards";

export default function ViewToggle({
  view,
  onChange,
}: {
  view: ViewMode;
  onChange: (view: ViewMode) => void;
}) {
  return (
    <div className="inline-flex w-full rounded-xl border border-line bg-surface p-1 shadow-sm lg:w-auto">
      <button
        type="button"
        aria-pressed={view === "table"}
        onClick={() => onChange("table")}
        className={`inline-flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors lg:flex-none ${
          view === "table"
            ? "bg-primary-light text-primary shadow-sm"
            : "text-ink-secondary hover:bg-section hover:text-ink"
        }`}
      >
        <svg
          aria-hidden="true"
          className="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" d="M4 4h16v16H4zM4 10h16M10 4v16" />
        </svg>
        Table
      </button>
      <button
        type="button"
        aria-pressed={view === "cards"}
        onClick={() => onChange("cards")}
        className={`inline-flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors lg:flex-none ${
          view === "cards"
            ? "bg-primary-light text-primary shadow-sm"
            : "text-ink-secondary hover:bg-section hover:text-ink"
        }`}
      >
        <svg
          aria-hidden="true"
          className="h-4 w-4"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <rect x="4" y="4" width="6" height="6" rx="1" />
          <rect x="14" y="4" width="6" height="6" rx="1" />
          <rect x="4" y="14" width="6" height="6" rx="1" />
          <rect x="14" y="14" width="6" height="6" rx="1" />
        </svg>
        Cards
      </button>
    </div>
  );
}
