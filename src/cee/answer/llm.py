"""The provider plumbing and the legacy single answer call (prompt v4.1, MAP=off). Since #247 the
default flow is plan -> map -> reduce (cee.answer.extract, cee.answer.reduce), which reuses the
clients, requests and parsing helpers here; calls follow the decomposition (ADR-021 rule 7).
Providers: mock | anthropic | openai | deepseek (#242: OpenAI SDK, strict function tools on the /beta
base URL, thinking on or off).

Skeleton placeholder, owner: S2 (Jiapeng Liu).
mock is offline and free: it cites the top hits verbatim. Use it for development and tests.
"""
from __future__ import annotations

import contextvars
import json
import time

from cee.answer.prompt import SYSTEM_PROMPT
from cee.answer.schema import Answer, llm_output_schema
from cee.config import settings
from cee.retrieve.fts import Hit

TOOL_NAME = "submit_answer"
# Output cap of the answer call (ADR-019, #230): 20000 for every call. Was 8000 (#181, #204, #213);
# a five-firm answer over ~60k input tokens came back empty at 8000 (#229 Q22). Thinking, when the
# model runs it, shares this cap. The SDK refuses a non-streaming call above 21,333 (its 600 s
# rule; a test checks it). The eval's cache key includes the cap when it differs from 8000, so a
# run at 20000 never reuses an output made at 8000. A cut at the cap is an invalid output.
MAX_TOKENS = 20000
# Anthropic request version (#232): both tools (submit_answer, submit_plan) are sent with
# `strict: true`, so the API enforces their input schemas. The eval's answer and plan cache keys
# carry it for the anthropic provider only, so a strict request never reuses a non-strict output;
# OpenAI keys are unchanged (its requests were already strict). Prompt texts are unchanged.
ANTHROPIC_REQUEST_VERSION = "strict-1"


# DeepSeek (#242). Output caps by thinking mode (True = on): reasoning shares max_tokens, so thinking
# gets the API's own thinking default (64K) for the answer and room to reason for the planner; off
# is answer 20000, planner 8000 (#245; the planner was 2000 before). Quality first (TL, plan review 1).
DEEPSEEK_MAX_TOKENS = {False: 20000, True: 64000}
# #245: plan-v3 has no aspect cap: off 2000 -> 8000; on 16000 -> 64000 (TL decision after the Q19
# planner was cut at 16000 reasoning tokens; the same as the answer cap and DeepSeek's thinking default)
DEEPSEEK_PLANNER_MAX_TOKENS = {False: 8000, True: 64000}
# Read timeout per read, not per request. The docs only say empty lines are sent while a request
# waits (one not started after 10 minutes is closed); nothing about lines during inference, so the
# whole generation of a non-streamed call may be one silent read: 3600 s covers 64000 tokens at about
# 18 tokens/s. #275: a streamed call (every W11 stage by default) is read with DEEPSEEK_IDLE_S instead
# (default 120 s, plus IDLE_READ_MARGIN_S for the socket read), and a watchdog aborts it when no chunk
# arrived for DEEPSEEK_IDLE_S (keep-alive lines are bytes but not chunks). A stalled call fails fast
# (StreamIdle) and is saved as failed with its partial output; it is never retried automatically.
DEEPSEEK_TIMEOUT_S, DEEPSEEK_CONNECT_S = 3600.0, 30.0
IDLE_READ_MARGIN_S = 5.0
DEEPSEEK_OK = ("tool_calls", "stop")   # finish_reason of a usable tool answer (forced choice: stop)
DEEPSEEK_STOP_CODES = {401: "the API key was rejected (401); check DEEPSEEK_API_KEY in .env",
                       402: "insufficient balance (402); top up the DeepSeek account, then run again",
                       429: "rate limit reached (429); wait, then run again"}


# #272: the W11 flow's stages (planner, map, reduce) each have their own effort (off | low | high | max), cap,
# model (the map may use another model) and streaming; the legacy MAP=off answer call keeps DEEPSEEK_THINKING and
# DEEPSEEK_MAX_TOKENS. Thinking-mode cap 128000 (was 64000, which cut Q20, Q21, Q27 in #250; the API allows 384K);
# off-mode caps as before (planner 8000, map and reduce 20000).
DEEPSEEK_STAGES = ("plan", "map", "reduce")
DEEPSEEK_THINKING_CAP = 128000
DEEPSEEK_OFF_CAPS = {"plan": 8000, "map": 20000, "reduce": 20000}
# #275: a thinking-off reduce writes the whole answer as output (the #272 answers reach 27,059 tokens), so a
# streamed off reduce gets 64000 (the API allows 1..384K in both modes, api-docs.deepseek.com
# /api/create-chat-completion, read 2026-11-22); a non-streamed one keeps 20000 (the SDK refuses a
# non-streamed call above 21,333).
DEEPSEEK_REDUCE_OFF_STREAMED_CAP = 64000


def stage_effort(stage: str) -> str:
    """off | low | high | max for one stage (DEEPSEEK_EFFORT_PLAN / _MAP / _REDUCE)."""
    if stage not in DEEPSEEK_STAGES:
        raise ValueError(f"unknown stage {stage!r}")
    return getattr(settings(), f"deepseek_effort_{stage}")


def stage_thinking(stage: str) -> bool:
    return stage_effort(stage) != "off"


def stage_max_tokens(stage: str) -> int:
    if stage_thinking(stage):
        return DEEPSEEK_THINKING_CAP
    if stage == "reduce" and stage_stream(stage):
        return DEEPSEEK_REDUCE_OFF_STREAMED_CAP
    return DEEPSEEK_OFF_CAPS[stage]


def stage_model(stage: str) -> str:
    """The DeepSeek model of one stage: DEEPSEEK_MODEL_MAP for the map when set, else DEEPSEEK_MODEL."""
    s = settings()
    return (s.deepseek_model_map or s.deepseek_model) if stage == "map" else s.deepseek_model


def stage_stream(stage: str) -> bool:
    """DEEPSEEK_STREAM: on streams every stage; nothink only the stages with thinking off; off none."""
    mode = settings().deepseek_stream
    return mode == "on" or (mode == "nothink" and not stage_thinking(stage))


def request_version(provider: str, stage: str | None = None) -> str | None:
    """The request version that joins the eval's cache keys (#232): anthropic strict-1; deepseek
    (#242) names the thinking mode and both caps, so an output made in one mode is never reused for
    the other; openai none. #272: with a stage, deepseek names that stage's effort, cap and streaming
    only, so each stage's key changes only with its own settings (a reduce-only re-run reuses every
    plan and map record)."""
    if provider == "anthropic":
        return ANTHROPIC_REQUEST_VERSION
    if provider == "deepseek" and stage is not None:
        # #283: the map request carries the shared firm prefix up to MAP_PREFIX_TOKENS (one tool schema, the
        # cell's instruction last): "-pf<ceiling>" keeps those keys apart from the per-cell #272 map records
        pf = f"-pf{settings().map_prefix_tokens}" if stage == "map" else ""
        return (f"ds-strict-2-{stage}-{stage_effort(stage)}-c{stage_max_tokens(stage)}"
                f"-s{1 if stage_stream(stage) else 0}{pf}")
    if provider == "deepseek":
        on = settings().deepseek_thinking
        return (f"ds-strict-1-think-{'on' if on else 'off'}"
                f"-a{DEEPSEEK_MAX_TOKENS[on]}-p{DEEPSEEK_PLANNER_MAX_TOKENS[on]}")
    return None


def answer_max_tokens(provider: str) -> int:
    """The answer call's output cap (#242): by thinking mode for deepseek, else MAX_TOKENS."""
    return DEEPSEEK_MAX_TOKENS[settings().deepseek_thinking] if provider == "deepseek" else MAX_TOKENS


# Context windows from the providers' docs, checked 2026-11-19: DeepSeek deepseek-v4-pro 1M (Models &
# Pricing page); Claude Sonnet 5.5 1M (Anthropic model table). OpenAI gpt-5: 400,000 context window and
# 128,000 max output tokens (developers.openai.com/api/docs/models/gpt-5, read 2026-11-20, #248); the
# same page also states a separate 272,000-token input limit, which this window - output check does
# not apply (the openai provider is not used in the W11 runs; marked deprecated on that page).
# Used by the map's per-call input check and the reduce's (#246, #247): an input over the window minus
# the output cap is not sent, never trimmed (the #245 interim guard was removed in #247).
CONTEXT_WINDOW = {"deepseek": 1_000_000, "anthropic": 1_000_000, "openai": 400_000}


def input_tokens(question: str, hits: list[Hit], plan=None, window=None) -> int:
    """Estimated input tokens of the answer call (characters / 4): system prompt, tool schema and
    the user message as built for these hits."""
    chars = (len(SYSTEM_PROMPT) + len(json.dumps(llm_output_schema()))
             + len(build_user_message(question, hits, plan, window)))
    return round(chars / 4)


class ProviderStop(RuntimeError):
    """The provider refused the request before any output (#242: DeepSeek 401 / 402 / 429). Never a
    fallback and never saved: the question (or the eval run) stops with this message."""


class ModelOutputError(RuntimeError):
    """A paid model call returned something that is not a valid Answer (#187).

    `raw` is the provider payload, always JSON-safe, so the caller can save what was paid for
    (CLAUDE.md "Paid API calls" step 3) instead of losing it with the exception."""

    def __init__(self, message: str, raw, provider: str, stop_reason: str | None = None,
                 usage: dict | None = None):
        super().__init__(message)
        self.raw, self.provider, self.stop_reason = raw, provider, stop_reason
        self.usage = usage or {}


CUT_REASONS = ("max_tokens", "length")   # Anthropic stop_reason / OpenAI finish_reason at the cap
# #232: an API refusal can stop a tool input mid-way, and strict mode's schema guarantee does not
# hold then. Not the model's own answer behavior "refuse" (answerable false), which is valid.
REFUSAL = "refusal"


def check_output(answer: Answer, raw=None, provider: str = "") -> Answer:
    """#230: a model output that cannot be trusted as an answer is invalid (ModelOutputError): a
    finding, never shown or scored, never re-rolled. Checked on the model's own output, before code
    adds part gaps or caveats; also on a saved output when the eval reuses it.
    1. Cut at the output cap (stop_reason max_tokens / finish_reason length), even when the partial
       output validates.
    2. Empty: no claims, no adjacent items and no gaps, unless it is a refusal (behavior refuse with
       answerable false: the prompt's "no claims")."""
    stop = answer.stop_reason
    if stop in CUT_REASONS:
        n = answer.usage.get("output_tokens")
        raise ModelOutputError(f"Model output cut at max_tokens ({n} output tokens)", raw, provider,
                               stop, answer.usage)
    refusal = answer.behavior == "refuse" and not answer.answerable
    if not (answer.claims or answer.adjacent or answer.gaps or refusal):
        raise ModelOutputError("Model output has no claims, adjacent items or gaps", raw, provider,
                               stop or None, answer.usage)
    return answer


def _usage(resp, input_key: str, output_key: str) -> dict:
    u = getattr(resp, "usage", None)
    out = {"input_tokens": getattr(u, input_key, None), "output_tokens": getattr(u, output_key, None)}
    # #248: Anthropic's prompt-cache tokens (outside input_tokens), when the response has them, for the cost
    for k in ("cache_read_input_tokens", "cache_creation_input_tokens"):
        v = getattr(u, k, None)
        if isinstance(v, int) and not isinstance(v, bool):
            out[k] = v
    return out


def _block_dict(b) -> dict:
    """One Anthropic content block as plain JSON data (SDK objects have model_dump; fakes may not)."""
    if hasattr(b, "model_dump"):
        return b.model_dump(mode="json")
    return {k: getattr(b, k) for k in ("type", "text", "name", "input") if hasattr(b, k)}


NO_PASSAGES = "(no passages were found for this part)"
KEPT_ELSEWHERE = ("(no further passages; the passages found for this part are listed under another part "
                  "or the research passages)")
RESEARCH_HEADING = "Research passages (found for the whole question):"
PEERS_HEADING = "Peer firms on the question's theme:"


def _chunk(h: Hit) -> str:
    seg = f", segment {h.segment}" if h.segment else ""
    dated = (f"period n/a, page content as of {h.published_at} (undated web page)"  # ADR-007 T-09
             if getattr(h, "date_basis", "source") == "retrieved"
             else f"period {h.period_end or 'n/a'}, published {h.published_at}")
    where = f"{h.entity_id or 'Research'} {h.doc_type}{seg}, {dated}, {h.section or ''}"
    if h.page:
        where += f", p.{h.page}"
    return f'<chunk id="{h.chunk_id}" source="{where}">\n{h.text}\n</chunk>'


def _part_head(part) -> str:
    from cee.answer.validate import _short_name
    firms = ", ".join(_short_name(f) for f in part.firms)
    return f"{part.id}" + (f" [{firms}]" if firms else "") + f": {' '.join(part.text.split())}"


def window_line(window) -> str:
    """Prompt v4.1 (#230): the question's time window (filtered in SQL) and the order it asks for."""
    return (f"Time window: {window[0]} to {window[1]} (only passages dated in it were searched). "
            "Order the answer newest first across all parts.")


def build_user_message(question: str, hits: list[Hit], plan=None, window=None) -> str:
    """Prompt v4 (#215): the plan's parts, then the evidence grouped under the part it was found
    for (hits keep their order inside a group), then research and peer passages. A part with no
    passages of its own says why, from its candidate pool before exclusion (plan.searched): pool
    0 -> nothing found; otherwise its passages sit under another part or the research passages.
    No plan: one part p1, the whole question, holding every hit that is not research or peers.
    `window` (v4.1, #230): (from, to) of a question with a time window: one line after the question."""
    parts = list(getattr(plan, "parts", None) or [])
    if not parts:
        from cee.retrieve.planner import Part
        parts = [Part("p1", question, [])]
    single = len(parts) == 1
    # #245: a competitor sub-question the floor across competitors emptied reads as nothing found
    pools = {s["id"]: 0 if s.get("floor_emptied") else s.get("pool")
             for s in getattr(plan, "searched", None) or []}

    def part_of(h: Hit) -> str | None:
        pid = getattr(h, "part_id", None)
        if pid in ("research", "peers"):
            return pid
        if single:
            return parts[0].id
        return pid if any(p.id == pid for p in parts) else "other"

    lines = [f"Question: {question}", *([window_line(window)] if window else []), "",
             "Parts of the question (from the search plan; every claim, adjacent item and gap gives the "
             "part_id it answers):"]
    lines += [f"- {_part_head(p)}" for p in parts]
    lines += ["", "Evidence chunks, grouped by the part they were found for:"]
    for p in parts:
        own = [h for h in hits if part_of(h) == p.id]
        lines.append(f"Part {_part_head(p)}")
        if own:
            lines += [_chunk(h) for h in own]
        else:
            lines.append(NO_PASSAGES if pools.get(p.id) == 0 else KEPT_ELSEWHERE)
    for heading, kind in ((RESEARCH_HEADING, "research"), (PEERS_HEADING, "peers"),
                          ("Other passages:", "other")):   # "other": a part not in the plan, never left out
        group = [h for h in hits if part_of(h) == kind]
        if group:
            lines.append(heading)
            lines += [_chunk(h) for h in group]
    return "\n".join(lines)


def generate(question: str, hits: list[Hit], provider: str | None = None, plan=None,
             window=None) -> Answer:
    provider = provider or settings().llm_provider
    from cee.answer import cancel
    cancel.check()   # #277: no new call after Stop
    if provider == "mock":
        return _mock(hits, plan)
    if provider == "anthropic":
        return _anthropic(question, hits, plan=plan, window=window)
    if provider == "openai":
        return _openai(question, hits, plan=plan, window=window)
    if provider == "deepseek":
        return _deepseek(question, hits, plan=plan, window=window)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def _clip(text: str, n: int = 300) -> str:
    """Cut at a word boundary, so a figure or its unit is never cut in half (#52)."""
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0]


def _mock(hits: list[Hit], plan=None) -> Answer:
    """The top 3 hits verbatim; each claim carries its hit's plan part (#215), so the part check
    runs on mock answers too (a part the mock does not cite gets a code gap)."""
    from cee.answer import cancel
    cancel.sleep(settings().mock_delay_s)  # 0 unless MOCK_DELAY_S is set (verify-cee, #80); a Stop cuts it (#277)
    ids = {p.id for p in getattr(plan, "parts", None) or []}
    claims = [{"text": _clip(" ".join(h.text.split())), "chunk_ids": [h.chunk_id],
               "part_id": h.part_id if getattr(h, "part_id", None) in ids else ""} for h in hits[:3]]
    return Answer(answerable=True, behavior="answer", claims=claims, llm_called=False)


def anthropic_request(question: str, hits: list[Hit], plan=None, window=None) -> dict:
    return {
        "model": settings().llm_model,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM_PROMPT + "\nYou MUST return the result by calling the submit_answer tool;"
                                  " do not answer in plain text.",
        # strict (#232): the API enforces the schema on the tool input (llm_output_schema already
        # meets strict mode's rules; a test checks it). It does not force a call: no call is invalid.
        "tools": [{"name": TOOL_NAME, "description": "Submit the cited answer.", "strict": True,
                   "input_schema": llm_output_schema()}],
        # Current Claude models reject forced tool_choice; the prompt requires the tool instead.
        "tool_choice": {"type": "auto"},
        "messages": [{"role": "user", "content": build_user_message(question, hits, plan, window)}],
    }


def anthropic_client():
    """The Anthropic client for the answer and the planner call (#214)."""
    import os

    import anthropic

    # Keys not scoped to a workspace must name one in a header. max_retries=0 (TL, #230): a timeout
    # or transport error is a reported failure, never a second paid request made by the SDK.
    ws = os.getenv("ANTHROPIC_WORKSPACE_ID", "").strip()
    return anthropic.Anthropic(default_headers={"anthropic-workspace-id": ws} if ws else None,
                               max_retries=0)


def openai_client():
    """The OpenAI client for the answer and the planner call (#214)."""
    import openai

    return openai.OpenAI(max_retries=0)   # TL, #230: the SDK never repeats a paid request


def deepseek_client():
    """The DeepSeek client for the answer and the planner call (#242): the OpenAI SDK on
    DEEPSEEK_BASE_URL (default /beta, needed for strict tools), max_retries=0 (never a second paid
    request), read timeout DEEPSEEK_TIMEOUT_S (a streamed call: DEEPSEEK_IDLE_S per read and the idle
    watchdog, #275; a stall fails, never retried). Needs DEEPSEEK_API_KEY; never uses OPENAI_API_KEY."""
    import os

    import openai

    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set; put it in .env (see .env.example)")
    return openai.OpenAI(api_key=key, base_url=settings().deepseek_base_url, max_retries=0,
                         timeout=openai.Timeout(DEEPSEEK_TIMEOUT_S, connect=DEEPSEEK_CONNECT_S))


def deepseek_tool_request(name: str, description: str, schema: dict, system: str, user: str,
                          max_tokens: int, stage: str | None = None) -> dict:
    """One strict function tool (#242). Thinking off: the named function is forced. Thinking on:
    tool_choice auto (a forced choice is a 400 in thinking mode); the prompt requires the tool.
    #272: with a stage, that stage's effort (sent as reasoning_effort when thinking is on), model, cap
    and streaming (stream=True with the usage chunk); without one, the legacy request (DEEPSEEK_THINKING)."""
    s = settings()
    if stage is None:
        on, model, body = s.deepseek_thinking, s.deepseek_model, {}
    else:
        on, model, max_tokens = stage_thinking(stage), stage_model(stage), stage_max_tokens(stage)
        body = {"reasoning_effort": stage_effort(stage)} if on else {}
    req = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "tools": [{"type": "function", "function": {"name": name, "description": description,
                                                    "strict": True, "parameters": schema}}],
        "tool_choice": "auto" if on else {"type": "function", "function": {"name": name}},
        "extra_body": {"thinking": {"type": "enabled" if on else "disabled"}, **body},
    }
    if stage is not None and stage_stream(stage):
        req["stream"] = True
        req["stream_options"] = {"include_usage": True}
    return req


def deepseek_request(question: str, hits: list[Hit], plan=None, window=None) -> dict:
    return deepseek_tool_request(
        TOOL_NAME, "Submit the cited answer.", llm_output_schema(),
        SYSTEM_PROMPT + "\nYou MUST return the result by calling the submit_answer tool;"
                        " do not answer in plain text.",
        build_user_message(question, hits, plan, window), answer_max_tokens("deepseek"))


class StreamIdle(Exception):
    """#275: a streamed call with no chunk for DEEPSEEK_IDLE_S seconds (or a silent socket), aborted. `partial` is
    the message assembled so far (content, reasoning_content, tool_calls as JSON data), `output_seen` whether any
    delta (text, reasoning or tool call) arrived, `ttft_s` the seconds to the first one. Saved as a failed call; no
    automatic retry (TL ruling on #275)."""

    def __init__(self, message: str, partial: dict, output_seen: bool, ttft_s: float | None, idle_s: float):
        super().__init__(message)
        self.partial, self.output_seen, self.ttft_s, self.idle_s = partial, output_seen, ttft_s, idle_s


def stream_timeout(idle_s: float):
    """The SDK timeout of a streamed request: each read waits at most idle_s + IDLE_READ_MARGIN_S."""
    import openai
    return openai.Timeout(idle_s + IDLE_READ_MARGIN_S, connect=DEEPSEEK_CONNECT_S)


# #283: a callback run once when a streamed DeepSeek call receives its first chunk with a delta (the map's
# leader-first gate opens on it); set per call by extract.run_round in the worker's context. None: no callback.
FIRST_CHUNK: contextvars.ContextVar = contextvars.ContextVar("cee_first_chunk", default=None)


def deepseek_create(client, request: dict, on_delta=None):
    """Send one DeepSeek request; 401 / 402 / 429 become ProviderStop with a plain message. #272: a
    streamed request (stream=True) is read to the end and assembled into the same response shape as a
    non-streamed one (assemble_stream), with ttft_s, the seconds to the first chunk that carries text,
    reasoning or a tool call. #275: a streamed request is read with the DEEPSEEK_IDLE_S timeout and a
    watchdog; a stall raises StreamIdle with the partial output (no retry). `on_delta(index, name, text)`
    gets each tool-call argument delta as it arrives (the reduce's streamed claims), in this thread."""
    import openai

    from cee.answer import cancel
    cancel.check()   # #277: no new call after Stop
    t0 = time.monotonic()
    try:
        if not request.get("stream"):
            return client.chat.completions.create(**request)
        idle = settings().deepseek_idle_s
        resp = client.chat.completions.create(**request, timeout=stream_timeout(idle))
        if hasattr(resp, "choices") and not hasattr(resp, "__iter__"):
            return resp   # a whole response (a client that ignores stream) is used as is
        return read_stream(resp, t0, idle, on_delta)
    except openai.APIStatusError as e:
        why = DEEPSEEK_STOP_CODES.get(getattr(e, "status_code", None))
        if why:
            raise ProviderStop(f"DeepSeek: {why}") from e
        raise


def _is_timeout(e: BaseException) -> bool:
    import openai
    return isinstance(e, openai.APITimeoutError) or "Timeout" in type(e).__name__


def read_stream(stream, t0: float, idle_s: float, on_delta=None):
    """#275: assemble the stream under a watchdog thread that closes it when no chunk arrived for idle_s (the
    iteration then ends or raises). A stall (the watchdog, or a read timeout of the SDK) raises StreamIdle with
    the partial message; any other error propagates. #277: the watchdog also closes the stream when the run's
    cancel token is set (Stop), and the read raises cancel.Cancelled (with `partial`) instead of StreamIdle;
    the loop checks the token between chunks too."""
    import threading

    from cee.answer import cancel

    asm = StreamAssembler(t0, on_delta)
    done, fired, stopped = threading.Event(), threading.Event(), threading.Event()
    token = cancel.current()

    def watch():
        while not done.wait(min(0.5, idle_s / 4)):
            cut = token is not None and token.is_set()
            if cut or time.monotonic() - asm.last > idle_s:
                (stopped if cut else fired).set()
                close = getattr(stream, "close", None)
                if close is not None:
                    try:
                        close()
                    except Exception:   # noqa: BLE001 - closing a dead stream may fail; the flag is what counts
                        pass
                return

    threading.Thread(target=watch, daemon=True, name="deepseek-idle").start()
    try:
        for ch in stream:
            if token is not None and token.is_set():
                stopped.set()
            if fired.is_set() or stopped.is_set():
                break
            asm.feed(ch)
    except Exception as e:   # noqa: BLE001 - a read error after the watchdog fired, or a read timeout
        if stopped.is_set() or (token is not None and token.is_set()):
            stopped.set()
        elif not (fired.is_set() or _is_timeout(e)):
            raise
        else:
            fired.set()
    finally:
        done.set()
    if stopped.is_set():
        close = getattr(stream, "close", None)
        if close is not None:
            try:
                close()
            except Exception:   # noqa: BLE001 - already closed by the watchdog
                pass
        e = cancel.Cancelled(f"stream closed by Stop after {time.monotonic() - t0:.1f} s")
        e.partial = _jsonable(asm.message())   # type: ignore[attr-defined]
        raise e
    if fired.is_set():
        raise StreamIdle(f"stream idle: no chunk for {idle_s:g} s (aborted after {time.monotonic() - t0:.1f} s; "
                         f"{'some output arrived' if asm.ttft is not None else 'no output arrived'})",
                         _jsonable(asm.message()), asm.ttft is not None, asm.ttft, idle_s)
    return asm.response()


class StreamAssembler:
    """#272 / #275: one streamed chat completion, chunk by chunk: content, reasoning, tool calls (argument deltas
    joined by index), finish_reason, usage, ttft_s; `last` = monotonic time of the last chunk that carried a
    delta, a finish_reason or usage (the idle clock)."""

    def __init__(self, t0: float | None = None, on_delta=None):
        self.t0 = time.monotonic() if t0 is None else t0
        self.last = time.monotonic()
        self.on_delta = on_delta
        self.content, self.reasoning, self.calls = [], [], {}
        self.finish, self.usage, self.ttft = None, None, None

    def feed(self, ch) -> None:
        alive = False
        if getattr(ch, "usage", None) is not None:
            self.usage = ch.usage
            alive = True
        for choice in getattr(ch, "choices", None) or []:
            d = getattr(choice, "delta", None)
            got = False
            if d is not None:
                if getattr(d, "content", None):
                    self.content.append(d.content)
                    got = True
                if getattr(d, "reasoning_content", None):
                    self.reasoning.append(d.reasoning_content)
                    got = True
                for tc in getattr(d, "tool_calls", None) or []:
                    i = getattr(tc, "index", 0) or 0
                    c = self.calls.setdefault(i, {"id": None, "name": "", "arguments": []})
                    c["id"] = getattr(tc, "id", None) or c["id"]
                    f = getattr(tc, "function", None)
                    if f is not None:
                        c["name"] = getattr(f, "name", None) or c["name"]
                        if getattr(f, "arguments", None):
                            c["arguments"].append(f.arguments)
                            if self.on_delta is not None:
                                self.on_delta(i, c["name"], f.arguments)
                    got = True
            if got and self.ttft is None:
                self.ttft = round(time.monotonic() - self.t0, 2)
                hook = FIRST_CHUNK.get()
                if hook is not None:
                    hook()
            if getattr(choice, "finish_reason", None):
                self.finish = choice.finish_reason
                alive = True
            alive = alive or got
        if alive:
            self.last = time.monotonic()

    def message(self):
        from types import SimpleNamespace as NS
        tool_calls = [NS(id=c["id"], type="function", function=NS(name=c["name"], arguments="".join(c["arguments"])))
                      for _, c in sorted(self.calls.items())]
        return NS(role="assistant", content="".join(self.content) or None,
                  reasoning_content="".join(self.reasoning) or None, tool_calls=tool_calls or None)

    def response(self):
        from types import SimpleNamespace as NS
        return NS(choices=[NS(message=self.message(), finish_reason=self.finish)], usage=self.usage,
                  ttft_s=self.ttft, streamed=True)


def assemble_stream(chunks, t0: float | None = None, on_delta=None):
    """#272: one streamed chat completion as a response object (SimpleNamespace): choices[0].message
    with content, reasoning_content and tool_calls (argument deltas joined by index), finish_reason,
    usage (from the final usage chunk; None when the stream sent none), ttft_s and streamed=True."""
    asm = StreamAssembler(t0, on_delta)
    for ch in chunks:
        asm.feed(ch)
    return asm.response()


def _jsonable(obj):
    """SDK objects (model_dump), dicts, lists and test fakes (SimpleNamespace) as JSON data."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if hasattr(obj, "__dict__"):
        return {k: _jsonable(v) for k, v in vars(obj).items()}
    return str(obj)


def deepseek_tool_call(resp, name: str, request: dict | None = None):
    """(first tool call named `name` or None, finish_reason, usage, payload) of one response.
    usage: input / output tokens, cache hit / miss, reasoning tokens, tool call count, thinking mode.
    payload: the whole message as JSON data (content, reasoning_content, tool calls).
    #272: with the request, thinking, effort and model come from it (each stage has its own), and a
    streamed response adds streamed and ttft_s."""
    choice = resp.choices[0]
    msg = choice.message
    stop = getattr(choice, "finish_reason", None)
    calls = list(getattr(msg, "tool_calls", None) or [])
    u = getattr(resp, "usage", None)
    details = getattr(u, "completion_tokens_details", None)
    usage = {"input_tokens": getattr(u, "prompt_tokens", None),
             "output_tokens": getattr(u, "completion_tokens", None),
             "cache_hit_tokens": getattr(u, "prompt_cache_hit_tokens", None),
             "cache_miss_tokens": getattr(u, "prompt_cache_miss_tokens", None),
             "reasoning_tokens": getattr(details, "reasoning_tokens", None),
             "tool_calls": len(calls),
             "thinking": "on" if settings().deepseek_thinking else "off"}
    if request is not None:
        body = request.get("extra_body") or {}
        usage["thinking"] = "on" if (body.get("thinking") or {}).get("type") == "enabled" else "off"
        usage["effort"] = body.get("reasoning_effort") or ("off" if usage["thinking"] == "off" else None)
        usage["model"] = request.get("model")
    if getattr(resp, "streamed", False) is True:
        usage["streamed"] = True
        usage["ttft_s"] = getattr(resp, "ttft_s", None)
    call = next((c for c in calls if getattr(getattr(c, "function", None), "name", None) == name), None)
    return call, stop, usage, _jsonable(msg)


TRAILING_BRACES = "trailing_braces"
_STRAY = set(" \t\r\n}]")


def loads_object(text, flags: list | None = None) -> dict:
    """A model's JSON object (tool arguments or structured content). TL decision on #246 (Q24): a
    known DeepSeek strict-mode glitch returns a complete JSON object followed by stray closing braces;
    the first complete object is taken (json.JSONDecoder().raw_decode) only when everything after it
    is whitespace and `}` / `]`, and `trailing_braces` is appended to `flags`. Any other trailing text,
    a non-object or text that is not JSON raises ValueError. The object still goes through every
    schema and code check."""
    if not isinstance(text, str):
        raise TypeError(f"arguments are {type(text).__name__}, not text")
    s = text.lstrip()
    obj, end = json.JSONDecoder().raw_decode(s)
    rest = s[end:]
    if rest.strip():
        if not set(rest) <= _STRAY:
            raise ValueError(f"Extra data after the JSON object: {rest.strip()[:40]!r}")
        if flags is not None and TRAILING_BRACES not in flags:
            flags.append(TRAILING_BRACES)
    if not isinstance(obj, dict):
        raise ValueError(f"arguments are a JSON {type(obj).__name__}, not an object")
    return obj


def deepseek_arguments(call, flags: list | None = None) -> dict:
    """The call's arguments parsed (loads_object); ValueError when not a JSON object (DeepSeek may
    send bad JSON); stray closing braces after a complete object are accepted and flagged."""
    return loads_object(call.function.arguments, flags)


def _deepseek(question: str, hits: list[Hit], client=None, plan=None, window=None) -> Answer:
    """#242. Invalid (ModelOutputError, saved, never re-rolled), in this order: finish_reason not
    tool_calls / stop (length = cut, content_filter, insufficient_system_resource, aborted); no
    submit_answer call; arguments not JSON or not an object; not a valid Answer; check_output."""
    if client is None:
        client = deepseek_client()
    resp = deepseek_create(client, deepseek_request(question, hits, plan, window))
    call, stop, usage, payload = deepseek_tool_call(resp, TOOL_NAME)
    if stop in CUT_REASONS:
        raise ModelOutputError(f"Model output cut at max_tokens ({usage['output_tokens']} output tokens)",
                               payload, "deepseek", stop, usage)
    if stop not in DEEPSEEK_OK:
        raise ModelOutputError(f"Model output stopped by finish_reason {stop}", payload, "deepseek", stop, usage)
    if call is None:
        raise ModelOutputError(f"Model did not call {TOOL_NAME} (finish_reason={stop or '?'})",
                               payload, "deepseek", stop, usage)
    text = call.function.arguments
    flags: list = []
    try:
        raw = deepseek_arguments(call, flags)
    except (TypeError, ValueError) as e:
        raise ModelOutputError(f"Model arguments are not a JSON object: {e}", text, "deepseek", stop, usage) from e
    if flags:
        usage = {**usage, "parse_flags": flags}
    try:
        answer = Answer(**raw, llm_called=True)
    except (ValueError, TypeError) as e:
        raise ModelOutputError(f"Model output is not a valid Answer: {e}", raw, "deepseek", stop, usage) from e
    answer.stop_reason, answer.usage = stop or "", usage
    msg = payload if isinstance(payload, dict) else {}
    answer._provider_payload = {"reasoning_content": msg.get("reasoning_content"), "content": msg.get("content")}
    return check_output(answer, raw, "deepseek")


def _anthropic(question: str, hits: list[Hit], client=None, plan=None, window=None) -> Answer:
    if client is None:
        client = anthropic_client()
    resp = client.messages.create(**anthropic_request(question, hits, plan, window))
    stop = getattr(resp, "stop_reason", None)
    usage = {**_usage(resp, "input_tokens", "output_tokens"),
             "blocks": [getattr(b, "type", "?") for b in resp.content]}   # e.g. thinking, tool_use
    block = next((b for b in resp.content if b.type == "tool_use" and b.name == TOOL_NAME), None)
    if block is None:
        raise ModelOutputError(f"Model did not call {TOOL_NAME} (stop_reason={stop or '?'})",
                               [_block_dict(b) for b in resp.content], "anthropic", stop, usage)
    raw = block.input
    if stop in CUT_REASONS:   # #230: a cut answer is never trusted, even when it validates
        raise ModelOutputError(f"Model output cut at max_tokens ({usage['output_tokens']} output tokens)",
                               [_block_dict(b) for b in resp.content], "anthropic", stop, usage)
    if stop == REFUSAL:       # #232: never trusted, even when the tool input validates
        raise ModelOutputError("Model output stopped by refusal (stop_reason refusal)",
                               [_block_dict(b) for b in resp.content], "anthropic", stop, usage)
    try:
        answer = Answer(**raw, llm_called=True)
    except (ValueError, TypeError) as e:  # pydantic ValidationError is a ValueError
        raise ModelOutputError(f"Model output is not a valid Answer: {e}", raw, "anthropic", stop, usage) from e
    answer.stop_reason, answer.usage = stop or "", usage
    return check_output(answer, raw, "anthropic")


def openai_request(question: str, hits: list[Hit], plan=None, window=None) -> dict:
    return {
        "model": settings().openai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT + "\nReturn JSON matching the schema."},
            {"role": "user", "content": build_user_message(question, hits, plan, window)},
        ],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "answer", "strict": True,
                                            "schema": llm_output_schema()}},
    }


def _openai(question: str, hits: list[Hit], client=None, plan=None, window=None) -> Answer:
    if client is None:
        client = openai_client()
    resp = client.chat.completions.create(**openai_request(question, hits, plan, window))
    choice = resp.choices[0]
    content = choice.message.content
    stop = getattr(choice, "finish_reason", None)
    usage = _usage(resp, "prompt_tokens", "completion_tokens")
    if stop in CUT_REASONS:   # #230
        raise ModelOutputError(f"Model output cut at max_tokens ({usage['output_tokens']} output tokens)",
                               content, "openai", stop, usage)
    flags: list = []
    try:
        answer = Answer(**loads_object(content, flags), llm_called=True)
    except (ValueError, TypeError) as e:  # None, not JSON, not an object, or not a valid Answer
        raise ModelOutputError(f"Model output is not a valid Answer: {e}", content, "openai", stop, usage) from e
    if flags:
        usage = {**usage, "parse_flags": flags}
    answer.stop_reason, answer.usage = stop or "", usage
    return check_output(answer, content, "openai")
