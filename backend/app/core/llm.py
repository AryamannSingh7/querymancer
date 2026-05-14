"""LLM client with Gemini-primary, Groq-fallback runtime strategy.

Gemini 2.5 Flash is the primary path. When it returns a 429 (free-tier
daily quota exhausted) or a transient 5xx, `generate_sql` retries the
same prompt against Groq Llama 3.3 70B and returns whichever model
answered. The fallback is a no-op when `groq_api_key` is unset, so the
behaviour matches the pre-fallback code path for local-only setups.

The router still catches `google.genai.errors.ClientError` /
`ServerError`: those exceptions only escape `generate_sql` when BOTH
providers fail (or when the Groq key is unset). When Groq itself fails
we re-raise the original Gemini exception so the router renders the
existing 503/502 UX — adding a new exception class would force every
caller to learn about the dual-provider design.
"""

from __future__ import annotations

import logging

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

from app.core.config import get_settings
from app.models import LLMOutput

logger = logging.getLogger(__name__)

# Groq's JSON mode requires the word "JSON" to appear somewhere in the
# messages and benefits from an explicit shape reminder, since Llama has
# no equivalent to Gemini's response_schema. We append this to the system
# instruction only on the Groq branch — Gemini's structured-output path
# already enforces the schema natively.
_GROQ_JSON_SUFFIX = (
    "\n\nReturn STRICT JSON ONLY matching this schema: "
    '{"sql": string, "explanation": string, '
    '"chart_hint": one of ["table","bar","line","pie","scalar"]}. '
    "Do not wrap the JSON in markdown fences."
)


def _gemini_client() -> genai.Client:
    # See app/core/embed.py for why this isn't cached — the SDK's
    # internal httpx.Client gets stuck in CLOSED state after a handful
    # of requests, breaking every subsequent call until the process
    # restarts. Instantiating per call is cheap relative to network I/O.
    return genai.Client(api_key=get_settings().gemini_api_key)


def _generate_with_gemini(
    prompt_text: str, system_instruction: str | None
) -> LLMOutput:
    # See app/core/embed.py for the reason this is bound to a local first:
    # the SDK closes its httpx pool when the Client is GC'd, and a chained
    # `_client().models.generate_content(...)` releases the temporary mid-call.
    client = _gemini_client()
    response = client.models.generate_content(
        model=get_settings().gemini_model,
        contents=prompt_text,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=LLMOutput,
            system_instruction=system_instruction,
        ),
    )
    return LLMOutput.model_validate_json(response.text)


def _generate_with_groq(
    prompt_text: str, system_instruction: str | None
) -> LLMOutput:
    # Imported lazily so environments without the optional `groq` package
    # installed still work — the fallback only matters when both the key
    # and the SDK are present.
    from groq import Groq

    settings = get_settings()
    client = Groq(api_key=settings.groq_api_key)
    system_content = (system_instruction or "") + _GROQ_JSON_SUFFIX
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt_text},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    return LLMOutput.model_validate_json(response.choices[0].message.content or "")


def generate_sql(
    prompt_text: str,
    system_instruction: str | None = None,
) -> LLMOutput:
    try:
        return _generate_with_gemini(prompt_text, system_instruction)
    except (ClientError, ServerError) as gemini_err:
        # Only fall back on quota / availability errors. A 400 from
        # Gemini (malformed prompt) shouldn't silently re-prompt Groq —
        # the caller deserves to see that bug. ClientError covers 4xx;
        # restrict to 429. ServerError covers 5xx; always retry there.
        is_rate_limited = isinstance(gemini_err, ClientError) and gemini_err.code == 429
        is_server_error = isinstance(gemini_err, ServerError)
        if not (is_rate_limited or is_server_error):
            raise

        if not get_settings().groq_api_key:
            # Fallback disabled — preserve pre-fallback behaviour.
            raise

        logger.info(
            "Gemini %s → falling back to Groq (%s)",
            type(gemini_err).__name__,
            get_settings().groq_model,
        )
        try:
            return _generate_with_groq(prompt_text, system_instruction)
        except Exception as groq_err:  # noqa: BLE001 — both paths failed
            logger.warning("Groq fallback also failed: %r", groq_err)
            raise gemini_err from groq_err
