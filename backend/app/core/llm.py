from google import genai
from google.genai import types

from app.core.config import get_settings
from app.models import LLMOutput


def _client() -> genai.Client:
    # See app/core/embed.py for why this isn't cached — the SDK's
    # internal httpx.Client gets stuck in CLOSED state after a handful
    # of requests, breaking every subsequent call until the process
    # restarts. Instantiating per call is cheap relative to network I/O.
    return genai.Client(api_key=get_settings().gemini_api_key)


def generate_sql(
    prompt_text: str,
    system_instruction: str | None = None,
) -> LLMOutput:
    # See app/core/embed.py for the reason this is bound to a local first:
    # the SDK closes its httpx pool when the Client is GC'd, and a chained
    # `_client().models.generate_content(...)` releases the temporary mid-call.
    client = _client()
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
