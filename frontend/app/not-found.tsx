import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-[1200px] flex-col items-center px-6 py-24 text-center">
      <h1 className="text-3xl font-bold text-ink">Page not found</h1>
      <p className="mt-3 text-ink-secondary">
        We couldn&apos;t find what you were looking for.
      </p>
      <div className="mt-8 flex gap-3">
        <Link
          href="/search"
          className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
        >
          Browse Jobs
        </Link>
        <Link
          href="/companies"
          className="rounded-lg border border-primary bg-surface px-5 py-2.5 text-sm font-medium text-primary transition-colors hover:bg-primary-light"
        >
          View Companies
        </Link>
      </div>
    </div>
  );
}
