export type IiInstall = {
  label: string;
  command: string;
  href: string;
};

const byExactName: Record<string, IiInstall[]> = {
  OpenClaw: [
    {
      label: "II skill",
      command: "clawhub install inference-indexer",
      href: "https://www.inferenceindexer.ai/for-agents?src=harnesses-openclaw",
    },
  ],
  Hermes: [
    {
      label: "II skill",
      command: "hermes skills install desmartin01/inference-indexer-skill",
      href: "https://www.inferenceindexer.ai/for-agents?src=harnesses-hermes",
    },
  ],
  AnythingLLM: [
    {
      label: "II MCP",
      command: "MCP URL: https://api.inferenceindexer.ai/mcp",
      href: "https://www.inferenceindexer.ai/for-agents?src=harnesses-anythingllm",
    },
  ],
  Khoj: [
    {
      label: "II MCP",
      command: "MCP URL: https://api.inferenceindexer.ai/mcp",
      href: "https://www.inferenceindexer.ai/for-agents?src=harnesses-khoj",
    },
  ],
  Codex: [
    {
      label: "II skill",
      command: "npx skills add desmartin01/inference-indexer-skill",
      href: "https://www.inferenceindexer.ai/for-agents?src=harnesses-codex",
    },
  ],
  "Open Interpreter": [
    {
      label: "II skill",
      command: "npx skills add desmartin01/inference-indexer-skill",
      href: "https://www.inferenceindexer.ai/for-agents?src=harnesses-open-interpreter",
    },
  ],
  letta: [
    {
      label: "II MCP",
      command: "MCP URL: https://api.inferenceindexer.ai/mcp",
      href: "https://www.inferenceindexer.ai/for-agents?src=harnesses-letta",
    },
  ],
};

export function iiInstallFor(name: string): IiInstall[] {
  return byExactName[name] ?? [];
}
