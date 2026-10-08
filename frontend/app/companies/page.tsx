import type { Metadata } from "next";
import { Suspense } from "react";
import CompanyClient from "./company-client";

export const metadata: Metadata = { title: "Companies | AV Job Finder" };

export default function CompaniesPage() {
  return (
    <Suspense fallback={null}>
      <CompanyClient />
    </Suspense>
  );
}
