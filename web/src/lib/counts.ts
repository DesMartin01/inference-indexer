// Single source of truth for the live model count fallback.
//
// The authoritative count always comes from the API (`getModelCount()`).
// These constants are only the SSR / API-down fallback baked into the
// initial render. Keep them in sync with the current live count so a brief
// fetch blip never shows a wrong number. Update these values any time the
// site's model count meaningfully changes.
export const CURRENT_MODEL_COUNT = 318;
export const CURRENT_PROVIDER_COUNT = 74;