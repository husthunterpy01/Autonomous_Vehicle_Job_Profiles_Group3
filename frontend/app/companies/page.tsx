import { Suspense } from "react";
import CompanyClient from "./company-client";

export default function CompaniesPage() {
  return (
    <Suspense fallback={null}>
      <CompanyClient />
    </Suspense>
  );
}
