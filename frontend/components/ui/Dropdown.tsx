"use client";

import { useState } from "react";

export type DropdownOption = { value: string; label: string };

/* Generic select-style dropdown used by Search and Company pages. */
export default function Dropdown({
  value,
  onChange,
  options,
  className = "",
  id,
  variant = "default",
  "aria-label": ariaLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  options: DropdownOption[];
  className?: string;
  /* Lets a visible <label htmlFor=...> point at the control. */
  id?: string;
  variant?: "default" | "plain";
  "aria-label"?: string;
}) {
  const [open, setOpen] = useState(false);
  const current = options.find((o) => o.value === value);
  const triggerClass =
    variant === "plain"
      ? "flex w-full items-center justify-between gap-2 bg-transparent px-2 py-2 text-sm font-medium text-ink"
      : "flex w-full items-center justify-between gap-2 rounded-lg border border-line bg-surface px-4 py-2.5 text-sm font-medium text-ink transition-colors hover:border-primary";

  return (
    <div className={`relative ${className}`}>
      <button
        id={id}
        type="button"
        aria-label={ariaLabel}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className={triggerClass}
      >
        {current ? current.label : value}
        <svg
          className={`h-4 w-4 text-ink-muted transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={2}
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {open && (
        <>
          {/* click-away backdrop */}
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-20 mt-2 max-h-72 min-w-full overflow-y-auto rounded-xl border border-line bg-surface p-2 shadow-lg lg:min-w-64">
            {options.map((o) => (
              <button
                key={o.value}
                type="button"
                onClick={() => {
                  onChange(o.value);
                  setOpen(false);
                }}
                className={`block w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                  value === o.value
                    ? "bg-primary-light font-medium text-primary"
                    : "text-ink-secondary hover:bg-section hover:text-ink"
                }`}
              >
                {o.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
