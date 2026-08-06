import type { Job } from "@/lib/mock-data";

export default function Salary({ job }: { job: Job }) {
  return (
    <p className="text-sm font-semibold text-primary">
      ${job.salaryMin}k – ${job.salaryMax}k
    </p>
  );
}
