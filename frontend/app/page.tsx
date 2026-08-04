import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-20">
      <section className="rounded-xl border border-slate-200 bg-white p-8">
        <p className="text-sm font-medium text-blue-700">
          Autonomous Vehicle Job Profiles
        </p>

        <h1 className="mt-3 text-4xl font-bold tracking-tight">
          Frontend application
        </h1>

        <p className="mt-4 max-w-2xl text-slate-600">
          The frontend project structure is ready. The final landing page and
          job search interface will be implemented in separate issues.
        </p>

        <Link
          href="/search"
          className="mt-8 inline-block rounded-lg bg-blue-700 px-5 py-3 font-medium text-white hover:bg-blue-800"
        >
          View search placeholder
        </Link>
      </section>
    </main>
  );
}
