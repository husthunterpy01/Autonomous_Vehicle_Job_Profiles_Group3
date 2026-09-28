import { apiFetch } from "./api";

export type TrendMonth = {
  month_key: number;
  label: string;
  snapshot_at: string;
  jobs_with_skills: number;
};

export type SkillRankPoint = {
  month_key: number;
  rank: number;
  job_count: number;
};

export type SkillTrend = {
  name: string;
  normalized_name: string;
  skill_type: string;
  points: SkillRankPoint[];
};

/** GET /api/v1/trends/skills: the latest month's top skills (in rank
 *  order) with their rank in each month. A month where a skill had no jobs
 *  has no point for it. */
export type SkillTrends = {
  months: TrendMonth[];
  skills: SkillTrend[];
};

/** The chart shows MAX_SERIES (8) skills, one color each. */
export function getSkillTrends(
  limit = 8,
  months = 12,
  signal?: AbortSignal,
): Promise<SkillTrends> {
  return apiFetch<SkillTrends>(
    `/api/v1/trends/skills?limit=${limit}&months=${months}`,
    { signal },
  );
}
