import type { Job } from "@/lib/mock-data";

export default function StatusBadge({ status }: { status: Job["status"] }) {
  const open = status === "Open";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium ${
        open ? "bg-success/10 text-success" : "bg-section text-ink-muted"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${open ? "bg-success" : "bg-ink-muted"}`}
      />
      {status}
    </span>
  );
}
