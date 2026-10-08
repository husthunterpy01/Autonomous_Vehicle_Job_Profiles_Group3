/* Eye (password visible) and crossed-out eye (password hidden). Decorative:
   the button that holds it carries the accessible name. */
export default function EyeIcon({ open }: { open: boolean }) {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.8}
      stroke="currentColor"
      aria-hidden="true"
    >
      {open ? (
        <>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M2.25 12s3.75-7.5 9.75-7.5 9.75 7.5 9.75 7.5-3.75 7.5-9.75 7.5S2.25 12 2.25 12z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z"
          />
        </>
      ) : (
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3 3l18 18M10.58 10.58a3 3 0 0 0 4.24 4.24M6.53 6.53C4.34 8 2.25 12 2.25 12s3.75 7.5 9.75 7.5c1.98 0 3.68-.53 5.09-1.35M9.88 4.83A9.7 9.7 0 0 1 12 4.5c6 0 9.75 7.5 9.75 7.5a17.4 17.4 0 0 1-2.7 3.85"
        />
      )}
    </svg>
  );
}
