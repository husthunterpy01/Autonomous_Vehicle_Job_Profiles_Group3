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
  onSubmit,
}: {
  keyword: string;
  onKeywordChange: (value: string) => void;
  placeholder: string;
  dropdownValue: string;
  onDropdownChange: (value: string) => void;
  dropdownOptions: DropdownOption[];
  dropdownClassName?: string;
  onSubmit: (e: FormEvent) => void;
}) {
  return (
    <form
      onSubmit={onSubmit}
      className="mt-8 flex flex-col gap-3 rounded-xl border border-line bg-surface p-3 shadow-sm lg:flex-row lg:items-center"
    >
      <input
        type="text"
        value={keyword}
        onChange={(e) => onKeywordChange(e.target.value)}
        placeholder={placeholder}
        className="w-full flex-1 bg-transparent px-2 py-2 text-sm text-ink outline-none placeholder:text-ink-muted"
      />
      <Dropdown
        value={dropdownValue}
        onChange={onDropdownChange}
        options={dropdownOptions}
        className={dropdownClassName}
      />
    </form>
  );
}
