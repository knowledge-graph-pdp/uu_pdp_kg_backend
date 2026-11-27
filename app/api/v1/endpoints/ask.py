from fastapi import APIRouter

from app.schemas.ask import AskRequest, AskResponse
from app.services.ask_service import answer_question

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest) -> AskResponse:
    response = answer_question(payload.question)
    return response
