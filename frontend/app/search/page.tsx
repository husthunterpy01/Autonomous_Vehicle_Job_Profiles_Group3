import type { Metadata } from "next";
import { Suspense } from "react";
import SearchClient from "./search-client";

export const metadata: Metadata = { title: "Find Jobs | AV Job Finder" };

export default function SearchPage() {
  return (
    <Suspense fallback={null}>
      <SearchClient />
    </Suspense>
  );
}
