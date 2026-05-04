from fastapi import APIRouter, HTTPException, status

from app.core import llm, prompt
from app.models import QueryRequest, QueryResponse

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def post_query(req: QueryRequest) -> QueryResponse:
    try:
        system_instruction, user_prompt = prompt.build_prompt(req.question, req.database_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return llm.generate_sql(
        prompt_text=user_prompt,
        system_instruction=system_instruction,
    )
