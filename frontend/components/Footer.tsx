import Link from "next/link";

const REPO_URL =
  "https://github.com/husthunterpy01/Autonomous_Vehicle_Job_Profiles_Group3";

type FooterLink = { label: string; href: string; external?: boolean };

export const FOOTER_COLUMNS: { title: string; links: FooterLink[] }[] = [
  {
    title: "Product",
    links: [
      { label: "Find Jobs", href: "/search" },
      { label: "Companies", href: "/companies" },
      { label: "Market Trends", href: "/trends" },
    ],
  },
  {
    title: "Account",
    links: [
      { label: "Favorites", href: "/favorites" },
      { label: "My Account", href: "/account" },
      { label: "Sign in", href: "/login" },
    ],
  },
  {
    title: "Project",
    links: [
      { label: "About", href: "/about" },
      { label: "GitHub", href: REPO_URL, external: true },
      { label: "Contact", href: `${REPO_URL}/issues`, external: true },
    ],
  },
];

export default function Footer() {
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

          {FOOTER_COLUMNS.map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold">{col.title}</h4>
              <ul className="mt-4 space-y-3">
                {col.links.map((link) => {
                  const className =
                    "text-sm text-white/60 transition-colors hover:text-white";
                  return (
                    <li key={link.label}>
                      {link.external ? (
                        <a
                          href={link.href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={className}
                        >
                          {link.label}
                        </a>
                      ) : (
                        <Link href={link.href} className={className}>
                          {link.label}
                        </Link>
                      )}
                    </li>
                  );
                })}
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
