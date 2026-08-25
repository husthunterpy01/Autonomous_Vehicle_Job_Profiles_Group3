import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for GitHub Pages deployment.
  output: "export",
  // Served under https://<user>.github.io/Autonomous_Vehicle_Job_Profiles_Group3/
  basePath: "/Autonomous_Vehicle_Job_Profiles_Group3",
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
