import type { CategoryName } from "@/lib/mock-data";
import { CATEGORY_COLORS } from "./category-colors";

export default function CategoryTag({ category }: { category: CategoryName }) {
  const colors = CATEGORY_COLORS[category];

  return (
    <span
      className={`inline-flex rounded-md px-2.5 py-1 text-xs font-medium ${colors.background} ${colors.text}`}
    >
      {category}
    </span>
  );
}
