"""Per-beat Playwright scene modules. Each module exposes:

    async def record(page) -> None

The runner imports `<beat_name>` and awaits its `record` function inside
a Playwright context with video recording enabled.

REPLACE: copy examples/find_evil_demo/scenes/*.py to here as starting
templates, then rewrite for your own demo's beats.
"""
