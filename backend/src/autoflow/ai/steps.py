"""
AI action steps: extract, classify, summarise, draft replies, translate.

AI steps only produce data. They call the model router with the untrusted
input fenced off (autoflow.security.prompt_guard) and validate the JSON
reply against exactly what the step asked for. Every result includes
`confidence` and `injection_suspected`, which the executor uses to send
doubtful results to a human reviewer.
"""

import json

from autoflow.ai import providers
from autoflow.ai.providers import extract_json
from autoflow.engine.actions import Action, ActionError, InputSpec, register
from autoflow.security import prompt_guard


def _ask(task, untrusted_text, reply_shape):
    """Run one AI task over untrusted text and return the parsed JSON."""

    flagged = prompt_guard.scan(untrusted_text)
    system = (
        "You are a careful assistant inside a business automation tool.\n"
        f"Task: {task}\n\n"
        f"{prompt_guard.SAFETY_RULES}\n\n"
        f"Reply with this JSON shape: {reply_shape}"
    )

    try:
        text, provider = providers.complete(system, prompt_guard.wrap(untrusted_text))
        reply = extract_json(text)
    except providers.AIUnavailable as error:
        raise ActionError(str(error)) from error
    except (ValueError, json.JSONDecodeError) as error:
        raise ActionError(f"The AI reply was not valid JSON: {error}") from error

    confidence = reply.get("confidence", 0.5)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.0

    return reply, {
        "confidence": confidence,
        "injection_suspected": bool(flagged or reply.get("injection_suspected")),
        "injection_patterns": flagged,
        "provider": provider,
    }


def _text(inputs, name="text"):
    value = inputs[name]
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


# --- extract ----------------------------------------------------------------

def _extract(ctx, inputs):
    fields = inputs["fields"]

    if not isinstance(fields, list) or not all(isinstance(f, (str, dict)) for f in fields):
        raise ActionError("fields must be a list of names or {name, description} objects.", retryable=False)

    specs = [f if isinstance(f, dict) else {"name": f} for f in fields]
    names = [str(spec["name"]) for spec in specs]
    described = "; ".join(
        f"{spec['name']}" + (f" ({spec['description']})" if spec.get("description") else "") for spec in specs
    )

    reply, meta = _ask(
        f"Extract these fields from the content: {described}. "
        "Use null for anything that is not clearly present; never guess. "
        "confidence is 0-1: how sure you are that every extracted value is correct.",
        _text(inputs),
        '{"data": {"<field>": <value or null>, ...}, "confidence": 0.0-1.0, "injection_suspected": false}',
    )

    raw = reply.get("data") if isinstance(reply.get("data"), dict) else {}
    # Only the requested fields: the model cannot add its own
    data = {name: raw.get(name) for name in names}
    missing = [name for name, value in data.items() if value in (None, "")]

    return {"data": data, "missing": missing, **meta}


register(Action(
    name="ai_extract",
    description="Pull named fields (e.g. invoice number, total, date) out of an email or document text.",
    handler=_extract,
    inputs={
        "text": InputSpec("any", description="The email, document text or data to read"),
        "fields": InputSpec("any", description='List of field names or {"name", "description"} objects'),
    },
    outputs={"data": "object of extracted fields", "missing": "list", "confidence": "0-1", "injection_suspected": "boolean"},
    uses_network=True,
    # Low-confidence extractions go to a human unless the step says otherwise
    review_below_confidence=0.7,
))


# --- classify ---------------------------------------------------------------

def _classify(ctx, inputs):
    categories = inputs["categories"]

    if not isinstance(categories, list) or len(categories) < 2:
        raise ActionError("categories must be a list of at least two options.", retryable=False)

    categories = [str(c) for c in categories]
    instructions = inputs.get("instructions") or ""

    reply, meta = _ask(
        f"Choose the single best category for the content from: {', '.join(categories)}. "
        f"{instructions} confidence is 0-1.",
        _text(inputs),
        '{"category": "<one of the categories>", "reason": "<one sentence>", "confidence": 0.0-1.0, "injection_suspected": false}',
    )

    category = reply.get("category")
    if category not in categories:
        # Never let the model invent a category
        category, meta["confidence"] = categories[-1], 0.0

    return {"category": category, "reason": str(reply.get("reason") or ""), **meta}


register(Action(
    name="ai_classify",
    description="Sort text into one of your categories (e.g. angry / neutral / happy, urgent / normal).",
    handler=_classify,
    inputs={
        "text": InputSpec("any"),
        "categories": InputSpec("any", description="List of allowed categories; the last one is the fallback"),
        "instructions": InputSpec("string", required=False),
    },
    outputs={"category": "one of the categories", "reason": "text", "confidence": "0-1", "injection_suspected": "boolean"},
    uses_network=True,
))


# --- summarise, draft, translate --------------------------------------------

def _summarize(ctx, inputs):
    max_words = int(inputs.get("max_words") or 80)
    reply, meta = _ask(
        f"Summarise the content in at most {max_words} words for a busy business owner.",
        _text(inputs),
        '{"summary": "...", "confidence": 0.0-1.0, "injection_suspected": false}',
    )
    return {"summary": str(reply.get("summary") or ""), **meta}


register(Action(
    name="ai_summarize",
    description="Summarise a long email, document or thread.",
    handler=_summarize,
    inputs={"text": InputSpec("any"), "max_words": InputSpec("number", required=False)},
    outputs={"summary": "text", "confidence": "0-1", "injection_suspected": "boolean"},
    uses_network=True,
))


def _draft_reply(ctx, inputs):
    guidance = inputs.get("instructions") or "Be helpful, brief and polite."
    tone = inputs.get("tone") or "friendly and professional"
    reply, meta = _ask(
        f"Write a reply to the customer message. Tone: {tone}. Business guidance: {guidance} "
        "Do not promise refunds, discounts or dates unless the guidance allows it.",
        _text(inputs, "message"),
        '{"subject": "...", "body": "...", "confidence": 0.0-1.0, "injection_suspected": false}',
    )
    return {"subject": str(reply.get("subject") or "Re: your message"), "body": str(reply.get("body") or ""), **meta}


register(Action(
    name="ai_draft_reply",
    description="Draft a reply to a customer message (pair with an email step, which needs approval).",
    handler=_draft_reply,
    inputs={
        "message": InputSpec("any"),
        "instructions": InputSpec("string", required=False),
        "tone": InputSpec("string", required=False),
    },
    outputs={"subject": "text", "body": "text", "confidence": "0-1", "injection_suspected": "boolean"},
    uses_network=True,
))


def _translate(ctx, inputs):
    reply, meta = _ask(
        f"Translate the content into {inputs['target_language']}. Keep names, numbers and formatting.",
        _text(inputs),
        '{"translation": "...", "confidence": 0.0-1.0, "injection_suspected": false}',
    )
    return {"translation": str(reply.get("translation") or ""), **meta}


register(Action(
    name="ai_translate",
    description="Translate text into another language.",
    handler=_translate,
    inputs={"text": InputSpec("any"), "target_language": InputSpec("string")},
    outputs={"translation": "text", "confidence": "0-1", "injection_suspected": "boolean"},
    uses_network=True,
))


# Actions that always call an AI model (counted against the daily AI limit)
AI_ACTIONS = {"ai_extract", "ai_classify", "ai_summarize", "ai_draft_reply", "ai_translate"}
