"""Run l02_eval.py unchanged, logging the token usage of every judge call.

    python measure_judge_tokens.py <log.json> <l02_eval flags...>

The Anthropic SDK's Messages.create is wrapped before l02_eval imports
DeepEval, so every judge request is counted with its real input/output tokens
(the agent's calls happen inside the stand and are not touched).
"""
import atexit
import json
import runpy
import sys

from anthropic.resources import messages as _messages

LOG: list[dict] = []
_sync = _messages.Messages.create


def _create(self, *args, **kwargs):
    resp = _sync(self, *args, **kwargs)
    usage = getattr(resp, "usage", None)
    if usage is not None:
        LOG.append({"in": usage.input_tokens, "out": usage.output_tokens})
    return resp


_messages.Messages.create = _create

_async = getattr(_messages, "AsyncMessages", None)
if _async is not None:
    _acreate_orig = _async.create

    async def _acreate(self, *args, **kwargs):
        resp = await _acreate_orig(self, *args, **kwargs)
        usage = getattr(resp, "usage", None)
        if usage is not None:
            LOG.append({"in": usage.input_tokens, "out": usage.output_tokens})
        return resp

    _async.create = _acreate


def _dump(path: str) -> None:
    n = len(LOG)
    if not n:
        print("\nJUDGE TOKENS: no judge calls logged")
        return
    tin = sum(x["in"] for x in LOG)
    tout = sum(x["out"] for x in LOG)
    print(f"\nJUDGE TOKENS: calls={n} in={tin} out={tout} "
          f"avg_in={tin / n:.0f} avg_out={tout / n:.0f}")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"calls": n, "input_tokens": tin, "output_tokens": tout, "per_call": LOG}, f)


log_path = sys.argv[1]
atexit.register(_dump, log_path)
sys.argv = ["l02_eval.py"] + sys.argv[2:]
runpy.run_path("l02_eval.py", run_name="__main__")
