"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV_LINKS = [
  { href: "/search", label: "Find Jobs" },
  { href: "/companies", label: "Companies" },
  { href: "/trends", label: "Market Trends" },
];

export default function NavBar() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 border-b border-line bg-surface">
      <div className="flex h-16 w-full items-center justify-between px-6 md:px-8 xl:px-10 2xl:px-12">
        {/* Logo — acts as the home link */}
        <Link
          href="/"
          className="flex items-center gap-2 font-bold text-ink transition-opacity hover:opacity-75"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-sm font-bold text-white">
            AV
          </span>
          <span>AV Job Finder</span>
        </Link>

        {/* Desktop nav + actions — one tight cluster: nav links, a divider, then Login/Sign Up */}
        <div className="hidden items-center gap-6 md:flex">
          {NAV_LINKS.map((link) => {
            const active =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm font-medium transition-colors ${
                  active ? "text-primary" : "text-ink-secondary hover:text-ink"
                }`}
              >
                {link.label}
              </Link>
            );
          })}

          <span aria-hidden="true" className="h-5 w-px bg-line" />

          <Link
            href="/login"
            className="text-sm font-medium text-ink-secondary hover:text-ink"
          >
            Login
          </Link>
          <Link
            href="/signup"
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
          >
            Sign Up
          </Link>
        </div>

        {/* Mobile hamburger */}
        <button
          type="button"
          aria-label="Toggle menu"
          onClick={() => setMenuOpen((open) => !open)}
          className="flex h-10 w-10 items-center justify-center rounded-lg text-ink-secondary hover:bg-section md:hidden"
        >
          <svg
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.8}
            stroke="currentColor"
          >
            {menuOpen ? (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            ) : (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
              />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="border-t border-line bg-surface px-6 pb-4 pt-2 md:hidden">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setMenuOpen(false)}
              className="block py-2.5 text-sm font-medium text-ink-secondary hover:text-primary"
            >
              {link.label}
            </Link>
          ))}
          <div className="mt-3 flex flex-col gap-2 border-t border-line pt-4">
            <Link
              href="/login"
              className="rounded-lg border border-line px-4 py-2 text-center text-sm font-medium text-ink-secondary hover:border-primary hover:text-primary"
            >
              Login
            </Link>
            <Link
              href="/signup"
              className="rounded-lg bg-primary px-4 py-2 text-center text-sm font-medium text-white hover:bg-primary-hover"
            >
              Sign Up
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
