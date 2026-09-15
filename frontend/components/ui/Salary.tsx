import { formatSalary, type SalaryInput } from "@/lib/salary";

type SalaryProps = SalaryInput & {
  className?: string;
  /** Shown when the job has no salary, e.g. "—" to keep a table cell
   *  aligned. Defaults to rendering nothing. */
  fallback?: string;
};

/* Shows pay as posted: a range when the source gives one, a single figure
   otherwise, followed by the pay period. levels.fyi estimates carry a "~"
   prefix so they are not mistaken for posted pay (FE-14). Renders nothing
   when the job has no usable salary data. */
export default function Salary({
  className,
  fallback,
  ...salary
}: SalaryProps) {
  const display = formatSalary(salary);
  if (!display) {
    return fallback ? (
      <span className="text-sm text-ink-muted">{fallback}</span>
    ) : null;
  }
  return (
    <p className={["text-sm", className].filter(Boolean).join(" ")}>
      <span className="font-semibold text-primary">{display.amount}</span>
      {display.period && (
        <span className="ml-1 text-ink-secondary">{display.period}</span>
      )}
    </p>
  );
}
