"""Endpoints API — Agent IA (diagnostic + chat)."""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.diagnostic_agent import AlarmContext, DiagnosticAgent
from app.agents.llm_provider import LLMMessage, LLMProvider, LLMRole

router = APIRouter(prefix="/agent")


# ─── Diagnostic ───────────────────────────────────────────────────────────────


class DiagnoseRequest(BaseModel):
    alarm_code: str
    alarm_label: str
    alarm_timestamp: datetime
    equipment_name: str
    equipment_type: str
    site_name: str
    recent_measurements: list[dict] = []
    weather_current: dict | None = None
    related_alarms: list[dict] = []


class DiagnoseResponse(BaseModel):
    summary: str
    raw_response: str
    sources: list[dict]
    confidence: float
    latency_ms: int
    model: str
    safety_alert: bool


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(payload: DiagnoseRequest) -> DiagnoseResponse:
    """Diagnostique une alarme avec contexte GTB + RAG."""
    agent = DiagnosticAgent()
    context = AlarmContext(**payload.model_dump())
    try:
        result = await agent.diagnose(context)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return DiagnoseResponse(
        summary=result.summary,
        raw_response=result.raw_response,
        sources=result.sources,
        confidence=result.confidence,
        latency_ms=result.latency_ms,
        model=result.model,
        safety_alert=result.safety_alert,
    )


# ─── Chat (Phase 3 — UI conversationnelle) ────────────────────────────────────


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    rubric: str | None = None  # "depannage" | "analyse" | "energie" | "plan_action"


@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest) -> StreamingResponse:
    """Chat conversationnel en streaming (Server-Sent Events).

    Utilisé par l'interface React (Phase 3 — T8.3).
    """
    provider = LLMProvider()
    llm_messages = [LLMMessage(LLMRole(m.role), m.content) for m in payload.messages]

    async def event_stream():
        async for chunk in provider.stream(llm_messages):
            # Format SSE
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
