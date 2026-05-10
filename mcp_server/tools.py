from pathlib import Path
from .helper_client import HelperClient, BudgetExceeded, HelperUnreachable, HelperError
from .tar_project import tar_dir, TooLargeError

def _err(error: str, **fields) -> dict:
    return {"error": error, **fields}

def helper_render_silent(args: dict) -> dict:
    pd = args.get("project_dir")
    if not pd or not Path(pd).is_dir():
        return _err("project_dir_not_found", path=pd)
    try:
        tar = tar_dir(Path(pd))
    except TooLargeError as e:
        return _err("project_too_large", size_bytes=e.size, limit_bytes=e.limit)
    try:
        return HelperClient().post_silent(tar)
    except HelperUnreachable as e:
        return _err("helper_unreachable", detail=str(e))
    except HelperError as e:
        return _err("helper_error", detail=str(e))

def helper_render_voice(args: dict) -> dict:
    jid = args.get("job_id")
    if not jid:
        return _err("missing_job_id")
    try:
        return HelperClient().post_voice(jid)
    except BudgetExceeded as e:
        return _err("would_exceed_daily_cap", remaining=e.remaining, needed=e.needed,
                    suggest="shorten beats voiceover, or wait until daily reset")
    except HelperUnreachable as e:
        return _err("helper_unreachable", detail=str(e))
    except HelperError as e:
        return _err("helper_error", detail=str(e))

def helper_render_full(args: dict) -> dict:
    pd = args.get("project_dir")
    if not pd or not Path(pd).is_dir():
        return _err("project_dir_not_found", path=pd)
    try:
        tar = tar_dir(Path(pd))
    except TooLargeError as e:
        return _err("project_too_large", size_bytes=e.size, limit_bytes=e.limit)
    try:
        return HelperClient().post_silent(tar, auto_approve=True)
    except BudgetExceeded as e:
        return _err("would_exceed_daily_cap", remaining=e.remaining, needed=e.needed)
    except HelperUnreachable as e:
        return _err("helper_unreachable", detail=str(e))
    except HelperError as e:
        return _err("helper_error", detail=str(e))

def helper_skill(args: dict) -> str:
    try:
        return HelperClient().get_skill()
    except HelperError as e:
        return f"# SKILL fetch failed\n\n{e}"
