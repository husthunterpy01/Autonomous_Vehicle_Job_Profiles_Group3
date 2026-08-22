import type { Job } from "@/lib/mock-data";

export function formatSalary(job: Job): string {
  return `$${job.salaryMin}k – $${job.salaryMax}k`;
}

export default function Salary({ job }: { job: Job }) {
  return (
    <p className="text-sm font-semibold text-primary">
      {formatSalary(job)}
    </p>
  );
}
