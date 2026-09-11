#!/usr/bin/env python3
"""
Creator country-of-origin map for InferenceIndexer.

AA's Intelligence Index v4.3 RSC layout dropped the modelCreatorCountry
field (verified Sep 11, 2026: zero occurrences on the leaderboard page), so
creator origin now comes from this static map, keyed on the normalized
creator name seen in AA's data or OpenRouter's model id prefix.

Scope note: this is the country of the model's CREATOR (the lab that built
the model), not the inference provider hosting it. A model by a Chinese lab
hosted on a US aggregator is 'cn'.
"""

# Normalized creator name -> ISO 3166-1 alpha-2 (lowercase)
# Keys are lowercased, alphanumerics-only forms of lab names.
CREATOR_COUNTRY = {
    # US labs
    "openai": "us",
    "openaiopenai": "us",
    "anthropic": "us",
    "metameta": "us",
    "metal": "us",
    "meta": "us",
    "metallama": "us",
    "xai": "us",
    "spacexai": "us",
    "nvidia": "us",
    "nvidianvidia": "us",
    "ibm": "us",
    "ibmgranite": "us",
    "cohere": "ca",
    "voyageai": "us",
    "nomic": "us",
    "perplexity": "us",
    "openai gpt": "us",
    "gpt": "us",
    "openbmb": "cn",
    "inception": "us",
    "sambanova": "us",
    "cerebras": "us",
    "groq": "us",
    "together": "us",
    "fireworks": "us",
    "gradient": "us",
    "nousresearch": "us",
    "sakanaai": "jp",
    "sakana": "jp",
    "aisingapore": "sg",
    "upstage": "kr",
    "naver": "kr",
    "kakao": "kr",
    "lgai": "kr",
    "naverlabseurope": "de",
    "ai21labs": "il",
    "ai21": "il",
    "cognitivecomputations": "us",
    "gryphe": "us",
    "undi95": "us",
    "allenai": "us",
    "allen institute": "us",
    "mancerus": "us",
    "openrelay": "us",
    "topazlabs": "us",
    "thinkingmachines": "us",
    "thinkingmachineslab": "us",
    "thinking machines": "us",
    "poolside": "us",
    "writer": "us",
    "morph": "us",
    "rekaai": "us",
    "reka": "us",
    "sao10k": "us",
    "vui labs": "vn",
    "apodex": "unknown",
    "kokoro": "unknown",

    # China
    "deepseek": "cn",
    "deepseekdeepseek": "cn",
    "qwen": "cn",
    "qwenalibaba": "cn",
    "alibabacloud": "cn",
    "alibaba": "cn",
    "zai": "cn",
    "zzai": "cn",
    "zaiorg": "cn",
    "zhipu": "cn",
    "zhipuai": "cn",
    "glm": "cn",
    "moonshot": "cn",
    "moonshotai": "cn",
    "moonshotkimi": "cn",
    "minimax": "cn",
    "minimaxai": "cn",
    "minimaxmini": "cn",
    "bytedance": "cn",
    "bytedanceseed": "cn",
    "stepfun": "cn",
    "stepfunai": "cn",
    "baichuan": "cn",
    "inclusionai": "cn",
    "kwaipilot": "cn",
    "tencent": "cn",
    "xiaomi": "cn",
    "baidu": "cn",
    "nexagi": "cn",
    "nexagi nexagi": "cn",
    "huggingfacenex": "cn",
    "paddlepaddle": "cn",
    "01ai": "cn",
    "01 ai": "cn",
    "internlm": "cn",
    "thudm": "cn",
    "teleai": "cn",
    "mindai": "unknown",

    # Europe
    "mistral": "fr",
    "mistralai": "fr",
    "mistralai mistral": "fr",
    "lighton": "fr",
    "deepgram": "us",
    "jina": "de",
    "jinajina": "de",
    "alephalpha": "de",
    "theuuup": "de",
    "tngtech": "de",
    "deepep": "cn",
    "lmstudio": "unknown",
    "arliai": "unknown",
    "openchat": "unknown",
    "mancer": "unknown",

    # UK / Israel / UAE / India
    "stability": "gb",
    "stabilityai": "gb",
    "ibm uk": "gb",
    "phind": "us",
    "cognitivecomputations dolphin": "us",
    "52": "us",

    # Canada
    "cohereca": "ca",
    "cohere labs": "ca",

    # Others
    "google": "us",
    "google google": "us",
    "googledeepmind": "gb",
    "microsoft": "us",
    "amazon": "us",
    "liquid": "il",
    "liquidai": "il",
    "aionlabs": "unknown",
    "aionlabs aionlabs": "unknown",
    "anthracite": "us",
    "arceeai": "us",
    "deepcogito": "unknown",
    "elevenlabs": "us",
    "hermes": "us",
    "meituan": "cn",
    "pearlai": "unknown",
    "perceptron": "us",
    "relace": "unknown",
    "thedrummer": "unknown",
    "venice": "us",
    "glm53": "cn",
    "mindai": "unknown",
    "pearlai": "unknown",
    "nextagi": "unknown",
    "relace": "unknown",
    "microsoftphi": "us",
}


def normalize_creator(name):
    import re
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def country_for_creator(creator_name):
    """Return ISO country code for a lab/creator name, or None."""
    key = normalize_creator(creator_name)
    if not key:
        return None
    # exact normalized match first
    if key in CREATOR_COUNTRY:
        cc = CREATOR_COUNTRY[key]
        return None if cc == "unknown" else cc
    # substring match: try the longest known key contained in the name
    best = None
    for known, cc in CREATOR_COUNTRY.items():
        nk = normalize_creator(known)
        if len(nk) >= 4 and (nk in key or key in nk):
            if best is None or len(nk) > len(best[0]):
                best = (nk, cc)
    if best:
        return None if best[1] == "unknown" else best[1]
    return None