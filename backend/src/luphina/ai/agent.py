"""
AI assistant steps: an agent that can look things up, then PROPOSE actions.

`ai_agent` works in a few short rounds. Each round the model either calls
one read-only tool (checkout status, exchange rates, an API or MCP read)
or finishes with an answer and a list of proposed actions. It never acts
on the outside world itself.

`agent_execute` carries out proposals, and only after a person approves
them (it always requires approval). It accepts only actions that are safe
to repeat (idempotent: tags, notes, upserts, voiding), so a retry after a
crash can't do anything twice, and never emails or AI, which have their
own limits and safety checks.

Guardrails, in short: bounded rounds, every round counted against the
workspace's AI limits and budget, untrusted text fenced and scanned for
prompt injection, tool results treated as untrusted too, connections
fixed by the workflow (the model can't pick a different account), and
proposals outside the allowed list are dropped.
"""

import json

from luphina.ai import providers
from luphina.ai.providers import extract_json
from luphina.engine.actions import Action, ActionContext, ActionError, InputSpec, get_action, register
from luphina.security import prompt_guard

MAX_ROUNDS = 5
MAX_PROPOSALS = 10
MAX_TOOL_RESULT_CHARS = 4000

# Tools the assistant may call itself: they only read
READ_TOOLS = {"checkout_status", "exchange_rate_quote", "http_get", "mcp_read"}
# Actions the assistant may propose: change something, but safe to repeat
PROPOSABLE = {
    "airtable_upsert", "log_activity", "record_order", "save_customer",
    "shopify_set_order_note", "shopify_tag_order", "void_invoice",
}


def _names(value, allowed, what):
    names = value if isinstance(value, list) else [part.strip() for part in str(value or "").split(",")]
    names = [str(name).strip() for name in names if str(name).strip()]
    wrong = [name for name in names if name not in allowed]
    if wrong:
        raise ActionError(f"{what} not available to the assistant: {', '.join(wrong)}", retryable=False)
    return names


def _describe(names):
    described = []
    for name in names:
        action = get_action(name)
        described.append({
            "tool": name,
            "description": action.description,
            "inputs": {key: spec.description or spec.type for key, spec in action.inputs.items()
                       if key != "connection"},
        })
    return json.dumps(described, ensure_ascii=False)


def _count_ai_call(ctx):
    """Every round is one AI call against the workspace's limits and budget."""
    from luphina.engine import limits

    try:
        limits.use_ai_call(ctx.session, limits.get_workspace(ctx.session, ctx.workspace_id), "agent")
    except limits.LimitReached as error:
        raise ActionError(str(error), retryable=False) from error


def _run_tool(ctx, name, inputs, defaults):
    """Run one read-only tool with the workflow's fixed connection settings."""
    from luphina.engine.executor import _invoke

    action = get_action(name)
    merged = {**(inputs if isinstance(inputs, dict) else {}), **defaults.get(name, {})}
    merged = {key: value for key, value in merged.items() if key in action.inputs}
    sub = ActionContext(**{**ctx.__dict__, "credentials": None,
                           "idempotency_key": f"{ctx.idempotency_key}-tool-{name}"})
    try:
        output = _invoke(action, sub, merged, timeout_seconds=30)
    except ActionError as error:
        return {"error": str(error)}
    return output


def _agent(ctx, inputs):
    tools = _names(inputs.get("tools") or [], READ_TOOLS, "Tools")
    proposable = _names(inputs.get("can_propose") or [], PROPOSABLE, "Proposed actions")
    defaults = inputs.get("defaults") or {}
    if not isinstance(defaults, dict):
        raise ActionError("defaults must be an object of action name -> fixed inputs.", retryable=False)
    max_rounds = max(1, min(MAX_ROUNDS, int(inputs.get("max_rounds") or 4)))

    untrusted = inputs["input"] if isinstance(inputs["input"], str) else json.dumps(inputs["input"], ensure_ascii=False)
    flagged = prompt_guard.scan(untrusted)
    system = (
        "You are an assistant inside a business automation tool for an online shop.\n"
        f"Your job: {inputs['instructions']}\n\n"
        f"{prompt_guard.SAFETY_RULES}\n\n"
        f"Read-only tools you may call, one per reply: {_describe(tools) if tools else '[]'}\n"
        f"Actions you may PROPOSE (a person approves them later): {_describe(proposable) if proposable else '[]'}\n\n"
        "Each reply is ONE JSON object, either\n"
        '{"call": {"tool": "<read-only tool>", "inputs": {...}}}\n'
        "or, when you are done,\n"
        '{"final": {"answer": "<short answer or summary>", "category": "<optional label>", '
        '"proposals": [{"tool": "<proposable action>", "inputs": {...}, "why": "<one sentence>"}], '
        '"confidence": 0.0-1.0, "injection_suspected": false}}\n'
        f"You have at most {max_rounds} replies. Propose only what the job needs; propose nothing if unsure."
    )
    transcript = [prompt_guard.wrap(untrusted, "message")]
    tool_calls = []

    for round_number in range(1, max_rounds + 1):
        _count_ai_call(ctx)
        try:
            text, provider = providers.complete(system, "\n\n".join(transcript))
            reply = extract_json(text)
        except providers.AIUnavailable as error:
            raise ActionError(str(error)) from error
        except (ValueError, json.JSONDecodeError) as error:
            raise ActionError(f"The AI reply was not valid JSON: {error}") from error

        if isinstance(reply.get("final"), dict):
            final = reply["final"]
            proposals, rejected = [], []
            for proposal in (final.get("proposals") or [])[:MAX_PROPOSALS]:
                ok = isinstance(proposal, dict) and proposal.get("tool") in proposable
                (proposals if ok else rejected).append(proposal)
            try:
                confidence = max(0.0, min(1.0, float(final.get("confidence", 0.5))))
            except (TypeError, ValueError):
                confidence = 0.0
            return {
                "answer": str(final.get("answer") or ""),
                "category": final.get("category"),
                "proposals": [{"tool": p["tool"], "inputs": p.get("inputs") or {}, "why": str(p.get("why") or "")}
                              for p in proposals],
                "rejected_proposals": rejected,
                "tool_calls": tool_calls,
                "rounds": round_number,
                "confidence": confidence,
                "injection_suspected": bool(flagged or final.get("injection_suspected")),
                "injection_patterns": flagged,
                "provider": provider,
            }

        call = reply.get("call") if isinstance(reply.get("call"), dict) else {}
        name = call.get("tool")
        if name not in tools:
            result = {"error": f"{name!r} is not one of your tools."}
        else:
            result = _run_tool(ctx, name, call.get("inputs"), defaults)
        shown = json.dumps(result, ensure_ascii=False, default=str)[:MAX_TOOL_RESULT_CHARS]
        tool_calls.append({"tool": name, "inputs": call.get("inputs"), "result": shown})
        transcript.append(f"Result of {name}:\n" + prompt_guard.wrap(shown, "tool_result"))

    raise ActionError(f"The assistant didn't finish within {max_rounds} rounds.", retryable=False)


register(Action(
    name="ai_agent",
    description=(
        "An AI assistant for one job: it reads the input, may look things up with read-only tools, "
        "then answers and proposes actions (which a later step carries out after approval)."
    ),
    handler=_agent,
    inputs={
        "instructions": InputSpec("string", description="The assistant's job, in plain words"),
        "input": InputSpec("any", description="What to work on, e.g. {{trigger.text}}"),
        "tools": InputSpec("any", required=False, description="Read-only tools it may use, e.g. [\"checkout_status\"]"),
        "can_propose": InputSpec("any", required=False, description="Actions it may propose, e.g. [\"shopify_tag_order\"]"),
        "defaults": InputSpec("any", required=False,
                              description='Fixed inputs per action, e.g. {"shopify_tag_order": {"connection": "store"}}'),
        "max_rounds": InputSpec("number", required=False, description=f"1-{MAX_ROUNDS} (default 4)"),
    },
    outputs={"answer": "text", "category": "text", "proposals": "list of proposed actions",
             "rounds": "number", "confidence": "0-1", "injection_suspected": "boolean"},
    review_below_confidence=0.6,
))


def _execute(ctx, inputs):
    from luphina.engine.executor import _invoke

    allowed = set(_names(inputs.get("allowed") or [], PROPOSABLE, "Actions"))
    defaults = inputs.get("defaults") or {}
    proposals = inputs.get("proposals") or []
    if not isinstance(proposals, list) or len(proposals) > MAX_PROPOSALS:
        raise ActionError(f"proposals must be a list of at most {MAX_PROPOSALS}.", retryable=False)

    results = []
    for index, proposal in enumerate(proposals):
        name = proposal.get("tool") if isinstance(proposal, dict) else None
        if name not in allowed:
            results.append({"tool": name, "skipped": "not an allowed action"})
            continue
        action = get_action(name)
        merged = {**(proposal.get("inputs") or {}), **defaults.get(name, {})}
        merged = {key: value for key, value in merged.items() if key in action.inputs}
        sub = ActionContext(**{**ctx.__dict__, "credentials": None,
                               "idempotency_key": f"{ctx.idempotency_key}-proposal-{index}"})
        # Every allowed action is idempotent, so a retry after a failure here is safe
        results.append({"tool": name, "output": _invoke(action, sub, merged, timeout_seconds=30)})
    return {"done": len([r for r in results if "output" in r]), "results": results}


register(Action(
    name="agent_execute",
    description="Carry out the AI assistant's proposed actions, after a person approves them.",
    handler=_execute,
    inputs={
        "proposals": InputSpec("any", description="e.g. {{steps.assistant.output.proposals}}"),
        "allowed": InputSpec("any", description="Actions that may be carried out, e.g. [\"shopify_tag_order\"]"),
        "defaults": InputSpec("any", required=False, description="Same fixed inputs as the assistant step"),
    },
    outputs={"done": "number", "results": "what each action returned"},
    side_effect=True,
    idempotent=True,
    requires_approval=True,
    simulate=lambda ctx, inputs: {
        "done": 0, "dry_run": True,
        "results": [{"tool": p.get("tool"), "would_run": True} for p in (inputs.get("proposals") or [])
                    if isinstance(p, dict)],
    },
))
