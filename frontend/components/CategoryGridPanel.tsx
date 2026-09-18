"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getCategoryStats, type CategoryDemand } from "@/lib/services/home";

export default function CategoryGridPanel() {
  const [categories, setCategories] = useState<CategoryDemand[]>([]);
  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading",
  );

  useEffect(() => {
    let cancelled = false;
    getCategoryStats()
      .then((result) => {
        if (cancelled) return;
        setCategories(result);
        setStatus("success");
      })
      .catch(() => {
        if (cancelled) return;
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (status === "loading") {
    return <p className="text-sm text-ink-secondary">Loading categories…</p>;
  }

  if (status === "error") {
    return (
      <p className="text-sm text-ink-secondary">
        Couldn&apos;t load categories right now.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      {categories.map((category) => (
        <Link
          key={category.name}
          href="/search"
          className="rounded-[10px] border border-line bg-surface p-6 text-center shadow-sm transition-all duration-200 hover:-translate-y-1 hover:border-primary hover:shadow-md"
        >
          <h3 className="font-semibold text-ink">{category.name}</h3>
          <p className="mt-1 text-sm text-ink-secondary">
            {category.jobs} jobs available
          </p>
        </Link>
      ))}
    </div>
  );
}
