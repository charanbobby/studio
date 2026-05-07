"""
probe_09_langfuse_cloud_trace.py

Verify Langfuse Cloud SDK creates a trace with nested spans visible in the
dashboard. Send one trace with two child spans and flush.

Pass: PROBE OK; trace ID printed. Manually confirm in
https://us.cloud.langfuse.com that the trace appears within 30s.

Note on SDK version: the installed SDK is langfuse>=4 (OTel-based). The v2
`lf.trace()` / `trace.span()` API was removed; v4 exposes
`start_as_current_observation` as a context manager. Empirically verified
against Langfuse Cloud (auth_check returned True, trace flushed cleanly).
"""
from __future__ import annotations

import os
import sys
import time

from langfuse import Langfuse


def main() -> int:
    host = (
        os.environ.get("LANGFUSE_BASE_URL")
        or os.environ.get("LANGFUSE_HOST")
        or "https://cloud.langfuse.com"
    )
    lf = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=host,
    )

    if not lf.auth_check():
        print("PROBE FAIL: Langfuse auth_check returned False.")
        return 1

    trace_id: str | None = None

    with lf.start_as_current_observation(
        name="probe_09_smoke",
        as_type="span",
        input={"probe": "probe_09"},
        metadata={"probe": True},
    ) as root:
        trace_id = lf.get_current_trace_id()

        with lf.start_as_current_observation(
            name="extract_node", as_type="span", input={"brief": "test"}
        ) as s1:
            time.sleep(0.5)
            s1.update(output={"intent": "test_intent"})

        with lf.start_as_current_observation(
            name="plan_node", as_type="span", input={"intent": "test_intent"}
        ) as s2:
            time.sleep(0.5)
            s2.update(output={"plan": "stub"})

        root.update(output={"ok": True})

    lf.flush()

    print("PROBE 09")
    print(f"  langfuse host: {host}")
    print(f"  trace_id: {trace_id}")
    print("  Open the Langfuse Cloud dashboard and confirm trace appears.")
    print("PROBE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
