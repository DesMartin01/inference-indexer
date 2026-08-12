#!/usr/bin/env python3
"""
Download provider favicons and save them to web/public/favicons/.

For each unique domain in PROVIDER_DOMAINS (parsed from web/src/lib/api.ts),
fetches `https://www.google.com/s2/favicons?domain={domain}&sz=64` and saves
it to `web/public/favicons/{domain}.png`.

- Skips domains that already have a favicon file (unless --force is passed).
- Handles per-domain failures gracefully (logs a warning and continues).
- Prints a summary at the end (downloaded / skipped / failed counts).

Uses only the standard library (urllib) so it runs on the VPS without
requests being installed.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# --- Paths -----------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
API_TS_PATH = SCRIPT_DIR / "web" / "src" / "lib" / "api.ts"
FAVICONS_DIR = SCRIPT_DIR / "web" / "public" / "favicons"

# Google's favicon service: returns a PNG (sz=64 -> 64x64) for the domain.
FAVICON_URL_TEMPLATE = "https://www.google.com/s2/favicons?domain={domain}&sz=64"

# How long to wait for each favicon download (seconds).
DOWNLOAD_TIMEOUT = 15

# Pause between requests to be polite to Google's favicon service.
INTER_REQUEST_DELAY = 0.1

# Match lines like:  "OpenAI": "openai.com",
# Captures (provider, domain). The provider isn't actually used for filenames
# (we key on the domain), but we capture it for clarity / future use.
ENTRY_RE = re.compile(r'^\s*"([^"]+)"\s*:\s*"([^"]+)"\s*,?\s*$')


def parse_provider_domains(api_ts_path: Path) -> dict[str, str]:
    """
    Parse the PROVIDER_DOMAINS mapping out of api.ts.

    Looks for the `const PROVIDER_DOMAINS: Record<string, string> = { ... };`
    block and extracts every `"key": "value"` pair inside it.
    Returns a dict mapping provider name -> domain.
    """
    if not api_ts_path.exists():
        raise FileNotFoundError(f"Could not find api.ts at {api_ts_path}")

    text = api_ts_path.read_text(encoding="utf-8")

    # Locate the PROVIDER_DOMAINS block. Find the opening brace after the
    # declaration and the matching closing brace.
    decl_marker = "PROVIDER_DOMAINS"
    decl_idx = text.find(decl_marker)
    if decl_idx == -1:
        raise ValueError("PROVIDER_DOMAINS not found in api.ts")

    open_brace_idx = text.find("{", decl_idx)
    if open_brace_idx == -1:
        raise ValueError("Could not find opening brace for PROVIDER_DOMAINS")

    # Scan forward to find the matching closing brace (handles nested braces,
    # though this object shouldn't have any).
    depth = 0
    close_brace_idx = -1
    for i in range(open_brace_idx, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                close_brace_idx = i
                break
    if close_brace_idx == -1:
        raise ValueError("Could not find closing brace for PROVIDER_DOMAINS")

    block_text = text[open_brace_idx + 1 : close_brace_idx]

    mapping: dict[str, str] = {}
    for line in block_text.splitlines():
        m = ENTRY_RE.match(line)
        if m:
            provider, domain = m.group(1), m.group(2)
            mapping[provider] = domain

    if not mapping:
        raise ValueError("Parsed PROVIDER_DOMAINS block but found no entries")

    return mapping


def download_favicon(domain: str, dest_path: Path) -> bool:
    """
    Download the favicon for `domain` to `dest_path`.
    Returns True on success, False on failure.
    """
    url = FAVICON_URL_TEMPLATE.format(domain=domain)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; FaviconFetcher/1.0; "
                "+https://github.com/inference-futures-exchange)"
            ),
            "Accept": "image/png,image/*;q=0.8,*/*;q=0.5",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
            data = resp.read()
            if not data:
                print(f"  ⚠  WARNING: empty response for {domain}")
                return False
            # Sanity check: Google's service should return PNG bytes. If we got
            # an extremely small payload (e.g. a 1x1 blank), still save it —
            # it's a valid (if boring) favicon. Only treat 0 bytes as failure.
            dest_path.write_bytes(data)
            return True
    except urllib.error.HTTPError as e:
        print(f"  ⚠  WARNING: HTTP {e.code} for {domain} ({url})")
        return False
    except urllib.error.URLError as e:
        print(f"  ⚠  WARNING: URL error for {domain}: {e.reason}")
        return False
    except Exception as e:
        print(f"  ⚠  WARNING: failed to download {domain}: {e!r}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download provider favicons to web/public/favicons/."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download favicons even if the file already exists.",
    )
    args = parser.parse_args()

    # Parse the provider->domain mapping from the source file so the script
    # stays in sync with api.ts automatically.
    try:
        provider_domains = parse_provider_domains(API_TS_PATH)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # Unique domains only — multiple providers may share the same domain
    # (e.g. "Meta" and "Meta Llama" both map to meta.com). We download once
    # per unique domain.
    unique_domains: list[str] = sorted(set(provider_domains.values()))

    print(f"Loaded {len(provider_domains)} provider entries "
          f"({len(unique_domains)} unique domains) from {API_TS_PATH.name}")

    # Ensure the output directory exists.
    FAVICONS_DIR.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    skipped = 0
    failed: list[str] = []

    for domain in unique_domains:
        dest = FAVICONS_DIR / f"{domain}.png"

        if dest.exists() and not args.force:
            print(f"  ✓  skip (exists): {domain}")
            skipped += 1
            continue

        print(f"  ↓  downloading: {domain}")
        if download_favicon(domain, dest):
            size = dest.stat().st_size
            print(f"  ✓  saved: {dest.name} ({size} bytes)")
            downloaded += 1
        else:
            failed.append(domain)
            # Clean up a potentially partial/empty file on failure.
            if dest.exists():
                try:
                    dest.unlink()
                except OSError:
                    pass

        time.sleep(INTER_REQUEST_DELAY)

    print()
    print("=" * 50)
    print("FAVICON DOWNLOAD SUMMARY")
    print("=" * 50)
    print(f"  Downloaded: {downloaded}")
    print(f"  Skipped:    {skipped}")
    print(f"  Failed:     {len(failed)}")
    if failed:
        print("  Failed domains:")
        for d in failed:
            print(f"    - {d}")
    print(f"  Output dir: {FAVICONS_DIR}")
    print("=" * 50)

    # Exit 0 even on partial failures — favicons are non-critical and we want
    # the parent command to succeed. Failures are reported in the summary.
    return 0


if __name__ == "__main__":
    sys.exit(main())
