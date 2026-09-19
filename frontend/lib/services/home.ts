import type { CategoryStat } from "@/lib/category-filter";
import { apiFetch } from "./api";

type SkillStat = {
  skill_id: string;
  skill_name: string;
  number_of_occurrences: number;
};

export type SkillDemand = {
  name: string;
  jobs: number;
};

/** Backend already orders by job count desc, so this just reshapes the
 *  response - matches lib/mock-data's getTopSkills shape. */
export async function getTopSkills(limit = 8): Promise<SkillDemand[]> {
  const stats = await apiFetch<SkillStat[]>(
    `/api/v1/home/skill-stats?limit=${limit}`,
  );
  return stats.map((stat) => ({
    name: stat.skill_name,
    jobs: stat.number_of_occurrences,
  }));
}

export type CategoryDemand = {
  name: string;
  jobs: number;
};

/** One card per taxonomy sub_type (Sensing, Perception, ...), ranked by job
 *  count - matches lib/mock-data's AV_CATEGORIES shape used on the
 *  homepage's "Explore Jobs by Category" grid. */
export function getCategoryStatsRaw(): Promise<CategoryStat[]> {
  return apiFetch<CategoryStat[]>("/api/v1/home/category-stats");
}

export async function getCategoryStats(): Promise<CategoryDemand[]> {
  const stats = await getCategoryStatsRaw();
  return stats
    .map((stat) => ({ name: stat.sub_type, jobs: stat.job_count }))
    .sort((a, b) => b.jobs - a.jobs);
}
