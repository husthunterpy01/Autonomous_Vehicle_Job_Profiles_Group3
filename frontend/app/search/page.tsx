import SearchClient from "./search-client";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; category?: string }>;
}) {
  const { q, category } = await searchParams;
  return <SearchClient initialKeyword={q ?? ""} initialCategory={category ?? "All"} />;
}
