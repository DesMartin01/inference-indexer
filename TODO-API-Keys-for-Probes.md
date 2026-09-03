# API Keys Needed for Probe Expansion (PR-3)

Created: 2026-09-03
Paste each key to Frank in chat OR add directly on the Lightsail box:
`ssh ubuntu@3.255.179.226` then edit `/home/ubuntu/inference-indexer/.env` (add line: `PROVIDER_API_KEY=...`)

| # | Provider | Key name suggestion | Where to create | Free tier? |
|---|----------|--------------------|-----------------|------------|
| 1 | DeepInfra | `DEEPINFRA_API_KEY` | https://deepinfra.com/dash/keys | Yes (small credit) |
| 2 | Novita | `NOVITA_API_KEY` | https://novita.ai/dashboard/keys | Yes (small credit) |
| 3 | Together | `TOGETHER_API_KEY` | https://api.together.xyz/settings/api-keys | Yes (small credit) |
| 4 | Groq | `GROQ_API_KEY` | https://console.groq.com/keys | Yes (generous free tier) |
| 5 | SambaNova | `SAMBANOVA_API_KEY` | https://cloud.sambanova.ai/apis | Yes (free tier) |
| 6 | Inference.net | `INFERENCE_NET_API_KEY` | https://inference.net (dashboard -> API keys) | Yes (free tier) |

## Also needed while you're at it (2 existing keys broken)

- **TensorX**: probe key hit its $0.00 budget cap ("Budget has been exceeded"). Raise the key budget in the TensorX console (same place you got TENSORX_API_KEY).
- **xAI**: the XAI_API_KEY on Lightsail is invalid. Regenerate at https://console.x.ai (then it goes to Frank to update the .env, or paste in chat).

## Cost reality

Each probe = ~20 tokens, hourly (720/month/provider). Per-provider cost: ~$0.002-0.05/month.
All 9+ providers combined: under $1.50/month. The free-tier credits alone will cover months.

## What happens after keys arrive

Frank adds them to the Lightsail .env, runs one probe cycle, and /v1/quality + performance fields in recommend go live within the hour. Providers probing successfully: Fireworks (already working: TTFT 393ms measured) + whichever of the 6 keys arrive.
