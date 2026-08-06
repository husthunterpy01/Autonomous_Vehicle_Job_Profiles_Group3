import CompanyClient from "./company-client";

export default async function CompaniesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; type?: string }>;
}) {
  const { q, type } = await searchParams;
  return <CompanyClient initialKeyword={q ?? ""} initialType={type ?? "All"} />;
}
