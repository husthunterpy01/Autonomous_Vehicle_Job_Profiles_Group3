export default function Tag({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center justify-center whitespace-nowrap rounded-md bg-section px-2.5 py-1 text-xs font-medium text-ink-secondary">
      {label}
    </span>
  );
}
