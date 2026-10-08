import { useState, type HTMLInputTypeAttribute } from "react";
import EyeIcon from "@/components/ui/EyeIcon";

export default function TextField({
  id,
  label,
  value,
  onChange,
  error,
  hint,
  type = "text",
  autoComplete,
  required = false,
  disabled = false,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  hint?: string;
  type?: HTMLInputTypeAttribute;
  autoComplete?: string;
  required?: boolean;
  disabled?: boolean;
}) {
  const [revealed, setRevealed] = useState(false);
  const isPassword = type === "password";
  const describedBy =
    [hint ? `${id}-hint` : null, error ? `${id}-error` : null]
      .filter(Boolean)
      .join(" ") || undefined;

  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-ink">
        {label}
        {required && (
          <span aria-hidden="true" className="text-amber-800">
            {" "}
            *
          </span>
        )}
      </label>
      <div className="relative">
        <input
          id={id}
          name={id}
          type={isPassword && revealed ? "text" : type}
          value={value}
          required={required}
          disabled={disabled}
          autoComplete={autoComplete}
          onChange={(event) => onChange(event.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={`w-full rounded-lg border border-line bg-surface py-2.5 text-sm text-ink outline-none placeholder:text-ink-muted focus:border-primary disabled:opacity-60 ${
            isPassword ? "pl-4 pr-11" : "px-4"
          }`}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setRevealed((value) => !value)}
            aria-label={`${revealed ? "Hide" : "Show"} ${label.toLowerCase()}`}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-muted hover:text-ink"
          >
            <EyeIcon open={revealed} />
          </button>
        )}
      </div>
      {hint && (
        <p id={`${id}-hint`} className="mt-1.5 text-xs text-ink-secondary">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="mt-1.5 text-sm text-amber-800">
          {error}
        </p>
      )}
    </div>
  );
}
