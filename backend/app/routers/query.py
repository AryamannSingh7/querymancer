from fastapi import APIRouter, HTTPException, status

from app.core import agent
from app.models import QueryRequest, QueryResponse

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def post_query(req: QueryRequest) -> QueryResponse:
    try:
        result = agent.run(req.question, req.database_id)
    except ValueError as e:
        # unknown database_id from build_prompt
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except agent.AgentError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "agent failed to produce safe, executable SQL",
                "attempts": e.attempts,
                "errors": e.errors,
            },
        )

    return QueryResponse(
        sql=result.sql,
        explanation=result.explanation,
        chart_hint=result.chart_hint,
        columns=result.columns,
        rows=[list(r) for r in result.rows],
        attempts=result.attempts,
    )
