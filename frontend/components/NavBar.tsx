import Link from "next/link";

export default function NavBar() {
  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-4">
        <Link href="/" className="font-semibold text-slate-900">
          AV Job Finder
        </Link>

        <Link href="/" className="text-slate-600 hover:text-slate-900">
          Home
        </Link>

        <Link href="/search" className="text-slate-600 hover:text-slate-900">
          Search
        </Link>
      </div>
    </nav>
  );
}
