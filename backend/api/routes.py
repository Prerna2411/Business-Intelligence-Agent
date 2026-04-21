from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends

from backend.app.dependencies import get_bi_service
from services.service import BIService

router = APIRouter(prefix="/api", tags=["business-intelligence"])


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3)


class QueryResponse(BaseModel):
    result: dict


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, service: BIService = Depends(get_bi_service)) -> QueryResponse:
    return QueryResponse(result=service.ask(request.question))
