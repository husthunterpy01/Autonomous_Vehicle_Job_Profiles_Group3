import type { CategoryName } from "@/lib/mock-data";

export type CategoryColor = {
  background: string;
  text: string;
};

// Keep category styling in one place so cards and tables stay consistent.
export const CATEGORY_COLORS: Record<CategoryName, CategoryColor> = {
  Perception: { background: "bg-blue-50", text: "text-blue-700" },
  Localization: { background: "bg-teal-50", text: "text-teal-700" },
  Planning: { background: "bg-amber-50", text: "text-amber-700" },
  Control: { background: "bg-orange-50", text: "text-orange-700" },
  Sensing: { background: "bg-purple-50", text: "text-purple-700" },
  System: { background: "bg-pink-50", text: "text-pink-700" },
  "Vehicle Interface": { background: "bg-green-50", text: "text-green-700" },
  Map: { background: "bg-cyan-50", text: "text-cyan-700" },
};
