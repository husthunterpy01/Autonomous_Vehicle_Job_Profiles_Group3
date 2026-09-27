"use client";

import { useEffect, useState } from "react";
import { getSkillTrends } from "@/lib/services/trend";
import {
  SkillRankChartView,
  type SkillTrendsState,
} from "./skill-rank-chart-view";

export const TOP_SKILL_COUNT = 10;
export const TREND_MONTHS = 12;

export default function SkillRankChart() {
  const [state, setState] = useState<SkillTrendsState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    getSkillTrends(TOP_SKILL_COUNT, TREND_MONTHS, controller.signal)
      .then((data) => setState({ status: "success", data }))
      .catch(() => {
        if (!controller.signal.aborted) setState({ status: "error" });
      });
    return () => controller.abort();
  }, []);

  return <SkillRankChartView state={state} />;
}
