"""
Model router: one call, several AI providers.

Providers are tried in AI_PROVIDER_ORDER (default "gemini,anthropic").
A provider without an API key is skipped; if a configured provider fails
(outage, rate limit, refusal), the next one is tried, so AutoFlow keeps
working when one AI vendor is down.
"""

import json
import os

from autoflow import config  # noqa: F401  (loads .env)


def extract_json(text):
    """Parse the first JSON object in a reply, tolerating code fences."""

    start, end = text.find("{"), text.rfind("}")

    if start == -1 or end <= start:
        raise ValueError("The reply contained no JSON object.")

    return json.loads(text[start:end + 1])


class AIUnavailable(Exception):
    """No configured provider could answer."""


class GeminiProvider:
    name = "gemini"

    def available(self):
        return bool(os.getenv("GEMINI_API_KEY"))

    def complete(self, system, prompt):
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
            ),
        )
        return response.text


class AnthropicProvider:
    name = "anthropic"

    def available(self):
        return bool(os.getenv("ANTHROPIC_API_KEY"))

    def complete(self, system, prompt):
        import anthropic

        client = anthropic.Anthropic()
        response = client.beta.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5"),
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": os.getenv("ANTHROPIC_EFFORT", "medium")},
            # If the model declines, the API retries on a suitable fallback model
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )

        if response.stop_reason == "refusal":
            raise RuntimeError("The model declined the request.")

        return "".join(block.text for block in response.content if block.type == "text")


PROVIDERS = {provider.name: provider for provider in (GeminiProvider(), AnthropicProvider())}


def provider_order():
    names = os.getenv("AI_PROVIDER_ORDER", "gemini,anthropic")
    return [PROVIDERS[name.strip()] for name in names.split(",") if name.strip() in PROVIDERS]


def complete(system, prompt):
    """Return (text, provider name) from the first provider that answers."""

    errors = []

    for provider in provider_order():
        if not provider.available():
            continue

        try:
            return provider.complete(system, prompt), provider.name
        except Exception as error:  # noqa: BLE001 - any provider failure falls through
            errors.append(f"{provider.name}: {error}")

    if not errors:
        raise AIUnavailable(
            "No AI provider is configured. Set GEMINI_API_KEY or ANTHROPIC_API_KEY."
        )

    raise AIUnavailable("All AI providers failed: " + "; ".join(errors))
