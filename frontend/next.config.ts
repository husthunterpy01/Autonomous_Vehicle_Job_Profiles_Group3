import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for GitHub Pages deployment.
  output: "export",
  // Served under https://<user>.github.io/Autonomous_Vehicle_Job_Profiles_Group3/
  // Only set for the Pages build (GITHUB_PAGES=true in cd-frontend.yml) —
  // local/Docker serving (next start, `serve -s out`) mounts the export at
  // "/", so a hardcoded basePath there 404s every asset via the SPA fallback.
  basePath: process.env.GITHUB_PAGES === "true" ? "/Autonomous_Vehicle_Job_Profiles_Group3" : "",
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
