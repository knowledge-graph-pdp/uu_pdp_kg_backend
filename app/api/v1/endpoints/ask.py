from fastapi import APIRouter, HTTPException

from app.schemas.ask import AskRequest, AskResponse
from app.services.ask_service import answer_question
from app.services.llm_client import LLMError

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest) -> AskResponse:
    try:
        response = answer_question(payload.question)
    except LLMError as error:
        status = 504 if error.kind == "timeout" else 502
        raise HTTPException(status_code=status, detail=error.message) from error
    return response
