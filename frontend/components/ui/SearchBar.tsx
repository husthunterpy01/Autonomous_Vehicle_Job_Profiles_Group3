import type { FormEvent } from "react";
import Dropdown, { type DropdownOption } from "./Dropdown";

/* Generic search bar: keyword input + dropdown, used by Search and
   Company pages so both share the same look and behaviour. */
export default function SearchBar({
  keyword,
  onKeywordChange,
  placeholder,
  dropdownValue,
  onDropdownChange,
  dropdownOptions,
  dropdownClassName = "",
  className = "",
  onSubmit,
}: {
  keyword: string;
  onKeywordChange: (value: string) => void;
  placeholder: string;
  dropdownValue: string;
  onDropdownChange: (value: string) => void;
  dropdownOptions: DropdownOption[];
  dropdownClassName?: string;
  className?: string;
  onSubmit: (e: FormEvent) => void;
}) {
  return (
    <form
      onSubmit={onSubmit}
      className={`mt-8 flex flex-col gap-3 rounded-xl border border-primary/40 bg-surface p-3 shadow-sm transition-shadow focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20 lg:flex-row lg:items-center ${className}`}
    >
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <svg
          aria-hidden="true"
          className="h-5 w-5 shrink-0 text-primary"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="m21 21-4.35-4.35m1.35-5.65a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z"
          />
        </svg>
        <input
          type="text"
          value={keyword}
          onChange={(e) => onKeywordChange(e.target.value)}
          placeholder={placeholder}
          aria-label={placeholder}
          className="w-full bg-transparent px-1 py-2 text-sm text-ink outline-none placeholder:text-ink-muted"
        />
      </div>
      <Dropdown
        value={dropdownValue}
        onChange={onDropdownChange}
        options={dropdownOptions}
        className={dropdownClassName}
      />
    </form>
  );
}
