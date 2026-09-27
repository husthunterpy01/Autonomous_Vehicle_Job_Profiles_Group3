"use client";

import { useEffect, useState } from "react";
import { MAX_SERIES } from "@/lib/skill-trend-chart";
import { getSkillTrends } from "@/lib/services/trend";
import {
  SkillTrendChartView,
  type SkillTrendsState,
} from "./skill-trend-chart-view";

export const TREND_MONTHS = 12;

export default function SkillTrendChart() {
  const [state, setState] = useState<SkillTrendsState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    // One color per skill caps the chart at MAX_SERIES skills.
    getSkillTrends(MAX_SERIES, TREND_MONTHS, controller.signal)
      .then((data) => setState({ status: "success", data }))
      .catch(() => {
        if (!controller.signal.aborted) setState({ status: "error" });
      });
    return () => controller.abort();
  }, []);

  return <SkillTrendChartView state={state} />;
}
