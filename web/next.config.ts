import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      // --- Model slug renames (provider slug changed in DB) ---
      // Prefix wildcard redirects: old slug -> new slug, preserving the model sub-path
      { source: "/models/zai-org/:model*", destination: "/models/z-ai/:model*", permanent: true },
      { source: "/models/xiaomimimo/:model*", destination: "/models/xiaomi/:model*", permanent: true },
      { source: "/models/minimaxai/:model*", destination: "/models/minimax/:model*", permanent: true },
      // --- Namespace renames found by the 2026-09-26 SEO crawl (src ns fully dead) ---
      { source: "/models/pearl-ai/:model*", destination: "/models/google/:model*", permanent: true },
      { source: "/models/perceptron/:model*", destination: "/models/thinkingmachines/:model*", permanent: true },
      { source: "/models/stepfun-ai/:model*", destination: "/models/stepfun/:model*", permanent: true },
      // xai -> x-ai (Oct 22 reversal): OpenRouter emits x-ai/*, so x-ai is
      // canonical in the DB; xai/* rows were consolidated back onto x-ai/*
      { source: "/models/xai/:model*", destination: "/models/x-ai/:model*", permanent: true },
      // --- Exact renames where the source namespace still has live models ---
      // glm-5.3: 0 live, 1 dead; target ns live
      { source: "/models/glm-5.3", destination: "/models/z-ai/glm-5.3", permanent: true },
      // glm-5.3-flash: 0 live, 1 dead; target ns live
      { source: "/models/glm-5.3-flash", destination: "/models/z-ai/glm-5.3-flash", permanent: true },
      // mistral/ministral-8b: 0 live, 1 dead; target ns live
      { source: "/models/mistral/ministral-8b", destination: "/models/mistralai/ministral-8b", permanent: true },
      // mistral/mistral-nemo: 0 live, 1 dead; target ns live
      { source: "/models/mistral/mistral-nemo", destination: "/models/mistralai/mistral-nemo", permanent: true },
      // openrelay/deepseek-v3.1-terminus: 0 live, 1 dead; target ns live
      { source: "/models/openrelay/deepseek-v3.1-terminus", destination: "/models/deepseek/deepseek-v3.1-terminus", permanent: true },
      // openrelay/glm-5.3-flash: 0 live, 1 dead; target ns live
      { source: "/models/openrelay/glm-5.3-flash", destination: "/models/z-ai/glm-5.3-flash", permanent: true },
      // qwen3.8-27b: 0 live, 1 dead; target ns live
      { source: "/models/qwen3.8-27b", destination: "/models/qwen/qwen3.8-27b", permanent: true },
      // sambanova/gemma-4-31b-it: 0 live, 1 dead; target ns live
      { source: "/models/sambanova/gemma-4-31b-it", destination: "/models/google/gemma-4-31b-it", permanent: true },
      // sambanova/gpt-oss-120b: 0 live, 1 dead; target ns live
      { source: "/models/sambanova/gpt-oss-120b", destination: "/models/openai/gpt-oss-120b", permanent: true },
      // sambanova/minimax-m2.7: 0 live, 1 dead; target ns live
      { source: "/models/sambanova/minimax-m2.7", destination: "/models/minimax/minimax-m2.7", permanent: true },
      // sambanova/minimax-m3: 0 live, 1 dead; target ns live
      { source: "/models/sambanova/minimax-m3", destination: "/models/minimax/minimax-m3", permanent: true },
      // --- Provider page renames (name-based URL paths) ---
      // Google/browsers request URL-encoded paths, so use %20 (not literal spaces)
      { source: "/providers/Zai%20Org", destination: "/providers/Z.AI", permanent: true },
      { source: "/providers/Z%20Ai", destination: "/providers/Z.AI", permanent: true },
      { source: "/providers/Minimaxai", destination: "/providers/Minimax", permanent: true },
      // Handle un-encoded literal-space variants too (rare, but harmless)
      { source: "/providers/Zai Org", destination: "/providers/Z.AI", permanent: true },
      { source: "/providers/Z Ai", destination: "/providers/Z.AI", permanent: true },
      // --- Retired model IDs (Oct 22 consolidation; pages 404 without these) ---
      // (The five x-ai/grok-* entries are covered by the xai -> x-ai prefix
      // redirect above, so only the non-xai renames need exact rules.)
      { source: "/models/meta/llama-3.3-70b", destination: "/models/meta-llama/llama-3.3-70b", permanent: true },
      { source: "/models/meta/llama-4-maverick", destination: "/models/meta-llama/llama-4-maverick", permanent: true },
      { source: "/models/meta/llama-4-scout", destination: "/models/meta-llama/llama-4-scout", permanent: true },
      { source: "/models/mistralai/mistral-medium-3-5", destination: "/models/mistralai/mistral-medium-3.5", permanent: true },
      { source: "/models/bytedance-seed/seed-2-1-turbo", destination: "/models/bytedance-seed/seed-2.1-turbo", permanent: true },
      { source: "/models/deepseek-ai/deepseek-v3-0324", destination: "/models/deepseek/deepseek-v3-0324", permanent: true },
    ];
  },
};

export default nextConfig;