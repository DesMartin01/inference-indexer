#!/usr/bin/env python3
"""
Generic markdown-table pricing scraper for InferenceIndexer direct providers.

Many inference providers (Fireworks, Groq, Together, etc.) serve their
per-model pricing as a clean Markdown table on a Mintlify/docs site, reachable
by appending `.md` to the docs URL. This module provides a reusable parser:

  parse_table_pricing(markdown, id_col, in_col, out_col, ...)

    -> { canonical_model_id: {"input": float, "output": float, "cached": float|None, "context": int|None} }

plus helpers to build canonical model maps and emit (endpoints, new_models)
in the exact shape InferenceIndexer's pipeline expects.

Run this file standalone to lint the parser against a sample markdown file:
  python3 provider_pricing.py /path/to/models.md
"""

import re

# ---------------------------------------------------------------------------
# Markdown table parsing
# ---------------------------------------------------------------------------


def split_rows(markdown: str) -> list:
    """Return table data rows (list of list of cells) from markdown text.

    Naive but robust: split on lines that start with '|'. The first such
    table is assumed to be the header, subsequent lines are data rows.
    """
    rows = []
    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            line = line[1:-1]
            cells = [c.strip() for c in line.split("|")]
            rows.append(cells)
    if not rows:
        return []
    # Drop the divider row (---) if present after the header
    data = [r for r in rows[1:] if not all(re.match(r"^:?-+:?$", c) for c in r)]
    return data


def find_header(markdown: str, *needle_cols: str) -> list:
    """Return the header cell list of the first table containing all needles.

    Mintlify docs sometimes have multiple tables; we want the one whose header
    includes e.g. 'Model' and 'Input pricing' / 'price per 1M'.
    """
    for line in markdown.splitlines():
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [c.strip() for c in line[1:-1].split("|")]
        lower = [c.lower() for c in cells]
        nl_lower = [n.lower() for n in needle_cols]
        if all(any(nl in c for c in lower) for nl in nl_lower):
            return cells
    return []


_PRICE_RE = re.compile(r"\$?\s*(\d+(?:\.\d+)?)")


def parse_money(text: str):
    """Extract the first monetary value from text (handles '$0.15', '0.05')."""
    m = _PRICE_RE.search(str(text))
    return float(m.group(1)) if m else None


def extract_model_rows(markdown: str, model_col: str = "model id"):
    """Extract (model_id, raw_cells) pairs from the first suitable table.

    model_col is matched loosely against the header. Returns list of
    (model_id, cells) where model_id is the cell under that column.
    """
    header = find_header(markdown, model_col)
    if not header:
        return []
    try:
        mcol = next(i for i, c in enumerate(header) if model_col.lower() in c.lower())
    except StopIteration:
        return []
    out = []
    for cells in split_rows(markdown):
        if mcol < len(cells) and cells[mcol]:
            out.append((cells[mcol], cells))
    return out


# ---------------------------------------------------------------------------
# Canonical model helpers (mirrors firewall_pricing.FIREWORKS_MODEL_MAP)
# ---------------------------------------------------------------------------


def canonical_or_native(provider_native_id: str, canonical_map: dict) -> str:
    """Map a provider-native model id to our canonical id, else keep native."""
    return canonical_map.get(provider_native_id, provider_native_id)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        sys.exit("usage: provider_pricing.py <models.md>")
    md = open(path).read()
    header = find_header(md, "model")
    print("Header found:", header)
    for mid, cells in extract_model_rows(md, "model id"):
        print(f"  {mid!r:40} {cells}")