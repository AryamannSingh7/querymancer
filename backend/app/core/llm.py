from functools import lru_cache

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.models import QueryResponse


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    return genai.Client(api_key=get_settings().gemini_api_key)


def generate_sql(
    prompt_text: str,
    system_instruction: str | None = None,
) -> QueryResponse:
    response = _client().models.generate_content(
        model=get_settings().gemini_model,
        contents=prompt_text,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=QueryResponse,
            system_instruction=system_instruction,
        ),
    )
    return QueryResponse.model_validate_json(response.text)
