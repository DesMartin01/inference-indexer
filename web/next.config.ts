import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      // --- Model slug renames (provider slug changed in DB) ---
      // Prefix wildcard redirects: old slug -> new slug, preserving the model sub-path
      {
        source: "/models/zai-org/:model*",
        destination: "/models/z-ai/:model*",
        permanent: true, // 301
      },
      {
        source: "/models/xiaomimimo/:model*",
        destination: "/models/xiaomi/:model*",
        permanent: true,
      },
      {
        source: "/models/minimaxai/:model*",
        destination: "/models/minimax/:model*",
        permanent: true,
      },

      // --- Provider page renames (name-based URL paths) ---
      // Google/browsers request URL-encoded paths, so use %20 (not literal spaces)
      {
        source: "/providers/Zai%20Org",
        destination: "/providers/Z.AI",
        permanent: true,
      },
      {
        source: "/providers/Z%20Ai",
        destination: "/providers/Z.AI",
        permanent: true,
      },
      {
        source: "/providers/Minimaxai",
        destination: "/providers/Minimax",
        permanent: true,
      },
      // Handle un-encoded literal-space variants too (rare, but harmless)
      {
        source: "/providers/Zai Org",
        destination: "/providers/Z.AI",
        permanent: true,
      },
      {
        source: "/providers/Z Ai",
        destination: "/providers/Z.AI",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;