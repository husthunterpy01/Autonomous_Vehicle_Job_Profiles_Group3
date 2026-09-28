"use client";

import { useState } from "react";
import { ALL_COUNTRIES, COUNTRY_OPTIONS } from "@/lib/country-filter";

export default function HomeSearchForm() {
  const [country, setCountry] = useState(ALL_COUNTRIES);

  return (
    <form
      action="/search"
      method="get"
      aria-label="Search jobs"
      className="mt-8 flex flex-col gap-3 rounded-xl border border-line bg-surface p-3 shadow-sm sm:flex-row sm:items-center"
    >
      <input
        type="text"
        name="q"
        placeholder="Job title, skill or keyword"
        className="w-full flex-1 bg-transparent px-2 py-2 text-sm text-ink outline-none placeholder:text-ink-muted"
      />
      <div className="hidden h-8 w-px bg-line sm:block" />
      <div className="w-full flex-1">
        <label
          htmlFor="home-country-filter"
          className="mb-1 block px-2 text-xs font-medium text-ink-secondary"
        >
          Country
        </label>
        <select
          id="home-country-filter"
          name={country ? "country" : undefined}
          value={country}
          onChange={(event) => setCountry(event.target.value)}
          className="w-full rounded-md bg-transparent px-2 py-1 text-sm text-ink outline-none transition-shadow focus-visible:ring-2 focus-visible:ring-primary/20"
        >
          {COUNTRY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <button
        type="submit"
        className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
      >
        Search Jobs
      </button>
    </form>
  );
}
