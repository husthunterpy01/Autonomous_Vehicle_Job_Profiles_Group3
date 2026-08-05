import Link from "next/link";

export default function Footer() {
  const columns: { title: string; links: { label: string; href: string }[] }[] =
    [
      {
        title: "Product",
        links: [
          { label: "Find Jobs", href: "/search" },
          { label: "Companies", href: "/companies" },
          { label: "Categories", href: "/search" },
        ],
      },
      {
        title: "Company",
        links: [
          { label: "About", href: "#" },
          { label: "Contact", href: "#" },
          { label: "Careers", href: "#" },
        ],
      },
      {
        title: "Resources",
        links: [
          { label: "Help Center", href: "#" },
          { label: "Privacy", href: "#" },
          { label: "Terms", href: "#" },
        ],
      },
    ];

  return (
    <footer className="bg-ink text-white">
      <div className="mx-auto max-w-[1200px] px-6 py-14">
        <div className="grid grid-cols-1 gap-10 md:grid-cols-5">
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 font-bold">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-sm font-bold text-white">
                AV
              </span>
              AV Job Finder
            </div>
            <p className="mt-4 max-w-xs text-sm text-white/60">
              Find your next AV opportunity and build your career.
            </p>
          </div>

          {columns.map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold">{col.title}</h4>
              <ul className="mt-4 space-y-3">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-white/60 transition-colors hover:text-white"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 border-t border-white/10 pt-6 text-sm text-white/50">
          © 2026 AV Job Finder. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
