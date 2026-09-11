#!/usr/bin/env python3
"""Daily MCP usage digest for InferenceIndexer.

Reads mcp_call_log (and api_request_log registered-key usage) from Supabase,
prints a compact digest. Designed to run as a Hermes cron job: the stdout IS
the report. Exit 0 with empty output if there was no traffic (cron sends
nothing, keeping the signal clean).
"""

import os
import sys

from dotenv import dotenv_values
import psycopg2


def main() -> None:
    url = dotenv_values(os.path.expanduser("~/.hermes/.env"))["SUPABASE_DB_URL"]
    conn = psycopg2.connect(url)
    cur = conn.cursor()

    # --- MCP tool calls, last 24h (classified) ---
    # probes: __verifymcp_auth_probe_* sent by registry scanners, never real tools
    # client errors: failed calls with empty args = malformed request (API 400s it correctly)
    # server errors: everything else that errored
    cur.execute("""
        SELECT tool_name, count(*), count(*) FILTER (WHERE is_error),
               round(avg(duration_ms)), count(DISTINCT session_id),
               count(*) FILTER (WHERE is_error AND tool_name LIKE '\\_\\_verifymcp_auth_probe%'),
               count(*) FILTER (WHERE is_error AND tool_name NOT LIKE '\\_\\_verifymcp_auth_probe%' AND args_summary = '')
        FROM mcp_call_log
        WHERE ts > now() - interval '24 hours'
        GROUP BY 1 ORDER BY 2 DESC
    """)
    mcp_rows = cur.fetchall()

    # --- registered (free-plan) API keys usage, last 24h: provable 3rd parties ---
    cur.execute("""
        SELECT count(*), count(DISTINCT user_label)
        FROM api_request_log
        WHERE ts > now() - interval '24 hours' AND plan = 'free'
    """)
    free_calls, free_users = cur.fetchone()

    cur.close()
    conn.close()

    if not mcp_rows and free_calls == 0:
        sys.exit(0)  # no traffic, cron sends nothing

    lines = ["**II MCP daily digest** (last 24h)", ""]
    total = sum(r[1] for r in mcp_rows)
    errors = sum(r[2] for r in mcp_rows)
    probes = sum(r[5] for r in mcp_rows)
    client_errs = sum(r[6] for r in mcp_rows)
    server_errs = errors - probes - client_errs
    real_total = total - probes
    if total:
        if probes and real_total == 0:
            lines.append(f"MCP tool calls: 0 real (plus {probes} scanner probe(s), correctly rejected)")
        elif real_total:
            err_bits = []
            if server_errs:
                err_bits.append(f"{server_errs} server error(s)")
            if client_errs:
                err_bits.append(f"{client_errs} client rejection(s) (malformed requests, API behaved correctly)")
            err_txt = "no server errors" if not err_bits else ", ".join(err_bits)
            probe_txt = f" + {probes} scanner probe(s)" if probes else ""
            lines.append(f"MCP tool calls: {real_total} real ({err_txt}){probe_txt}")
            lines.append("")
            lines.append("| Tool | Calls | Avg ms |")
            lines.append("|------|-------|--------|")
            for name, calls, errs, avg_ms, _sess, p, ce in mcp_rows:
                if name.startswith("__verifymcp_auth_probe"):
                    continue
                lines.append(f"| {name} | {calls - p} | {avg_ms} |")
    else:
        lines.append("MCP tool calls: 0 (no agent sessions)")

    lines.append("")
    lines.append(f"Registered API keys: {free_calls} calls from {free_users} distinct key(s)")
    lines.append("")
    lines.append("_Registered keys = provable third parties. MCP + anonymous traffic is unattributable by design._")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
