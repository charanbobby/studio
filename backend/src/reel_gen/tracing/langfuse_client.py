"""Langfuse v4 client wrapper.

Provides:
- ``get_langfuse()``: process-wide singleton constructed from env vars
  (``LANGFUSE_PUBLIC_KEY``, ``LANGFUSE_SECRET_KEY``, and ``LANGFUSE_BASE_URL``
  or ``LANGFUSE_HOST``).
- ``with_span(name)``: decorator that wraps a sync callable in a Langfuse span
  using the v4 ``start_as_current_observation`` context manager. Captures
  exceptions, marks the span as ERROR, and re-raises.
- ``flush()``: explicit flush helper for graceful shutdown.

The installed SDK is langfuse 4.5.1 (OTel-based). The v2 ``lf.span()`` /
``span.end()`` API is gone; v4 only exposes context-manager observations.
This wrapper targets sync functions; async coroutines need a separate decorator
because the v4 context manager is sync-only.
"""
from __future__ import annotations

import functools
import os
from contextlib import contextmanager
from typing import Any, Callable, Iterator, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])

# Module-level singleton. Lazily constructed so importing this module does not
# require Langfuse credentials in env.
_singleton: Any = None


def _resolve_host() -> str:
    return (
        os.environ.get("LANGFUSE_BASE_URL")
        or os.environ.get("LANGFUSE_HOST")
        or "https://cloud.langfuse.com"
    )


def get_langfuse() -> Any:
    """Return the process-wide Langfuse client, constructing it on first call.

    Reads ``LANGFUSE_PUBLIC_KEY`` and ``LANGFUSE_SECRET_KEY`` from env. Host is
    read from ``LANGFUSE_BASE_URL`` first (matches the user's ``.env``), then
    ``LANGFUSE_HOST``, then falls back to the public Langfuse Cloud URL.
    """
    global _singleton
    if _singleton is None:
        # Imported lazily so the module loads even when Langfuse is absent
        # from the environment (e.g. during static analysis).
        from langfuse import Langfuse

        _singleton = Langfuse(
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            host=_resolve_host(),
        )
    return _singleton


def _serialize(value: Any) -> Any:
    """Best-effort JSON-friendly view of a value for Langfuse capture.

    Pydantic v2 models -> ``model_dump(mode="json")`` so nested datetimes,
    UUIDs, and Pydantic submodels become JSON-safe. Lists / tuples recurse.
    Anything that fails serialization falls back to ``repr(value)`` so a
    weird object never breaks the trace.
    """
    try:
        # Pydantic v2 BaseModel.
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, (list, tuple)):
            return [_serialize(v) for v in value]
        if isinstance(value, dict):
            return {k: _serialize(v) for k, v in value.items()}
        # Primitives pass through.
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return repr(value)
    except Exception:
        return repr(value)


def with_span(name: str) -> Callable[[_F], _F]:
    """Decorator wrapping a sync callable in a Langfuse span.

    Uses the v4 ``start_as_current_observation`` context manager. Captures the
    full call inputs (args + kwargs, serialized as JSON-safe dicts via
    ``_serialize``) and the full return value as ``output``. For node helpers
    where the input is a Pydantic ``ReelState``, this surfaces the actual
    state snapshot (brief, intent, plan, scenes, etc.) in the dashboard rather
    than the previous ``{"args_len": ...}`` placeholder.

    Exceptions are captured at level ERROR before re-raising. The Langfuse
    client is resolved lazily so applying the decorator at import time does
    not require credentials.
    """

    def decorator(func: _F) -> _F:
        @functools.wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            lf = get_langfuse()
            input_payload = {
                "args": [_serialize(a) for a in args],
                "kwargs": {k: _serialize(v) for k, v in kwargs.items()},
            }
            with lf.start_as_current_observation(
                name=name,
                as_type="span",
                input=input_payload,
            ) as span:
                try:
                    result = func(*args, **kwargs)
                except Exception as exc:
                    span.update(level="ERROR", status_message=repr(exc))
                    raise
                span.update(output=_serialize(result))
                return result

        return wrapped  # type: ignore[return-value]

    return decorator


@contextmanager
def run_session(run_id: str) -> Iterator[None]:
    """Group all spans created inside the ``with`` block under one Langfuse session.

    Uses ``langfuse.propagate_attributes`` (v4 OTel baggage) to attach
    ``session_id=run_id`` and a ``trace_name`` to every observation started
    while the context is active. This is the same pattern the Find Evil
    pipeline uses to make per-run traces show up grouped in the Sessions
    dashboard. ``langfuse.update_current_trace`` does not exist on the v4.5.1
    client, so baggage propagation is the supported path.

    The Langfuse import is lazy so this module loads even when credentials
    are absent. If the import fails (e.g. Langfuse uninstalled in a test
    environment), this becomes a no-op so the calling code keeps working.
    """
    try:
        from langfuse import propagate_attributes  # local import (optional dep)
    except Exception:
        yield
        return

    with propagate_attributes(
        session_id=run_id,
        trace_name=f"run_{run_id}",
        tags=["sri-studio"],
        metadata={"run_id": run_id},
    ):
        yield


def flush() -> None:
    """Flush pending Langfuse events. Safe to call when no client exists yet."""
    if _singleton is not None:
        _singleton.flush()
