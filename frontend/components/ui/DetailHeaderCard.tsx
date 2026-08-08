import type { ReactNode } from "react";
import CompanyLogo from "./CompanyLogo";
import PageHeader from "./PageHeader";

/* Shared header card for Job Detail and Company Detail — logo + title/subtitle
   on the left, an optional external action link on the right, an optional
   `meta` block under the subtitle (e.g. badges), and an optional `footer`
   block below the whole row (e.g. a stats row), separated by a divider. */
export default function DetailHeaderCard({
  logoText,
  title,
  subtitle,
  action,
  meta,
  footer,
}: {
  logoText: string;
  title: string;
  subtitle: string;
  action?: { href: string; label: string };
  meta?: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="mt-4 rounded-xl border border-line bg-surface p-6 shadow-sm">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-4">
          <CompanyLogo text={logoText} size="h-14 w-14" />
          <div>
            <PageHeader title={title} subtitle={subtitle} />
            {meta && <div className="mt-3">{meta}</div>}
          </div>
        </div>

        {action && (
          <a
            href={action.href}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex shrink-0 items-center justify-center rounded-lg bg-primary px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
          >
            {action.label} ↗
          </a>
        )}
      </div>

      {footer && (
        <div className="mt-6 border-t border-line pt-6">{footer}</div>
      )}
    </div>
  );
}