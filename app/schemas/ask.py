from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=3, max_length=500)


class AnswerText(BaseModel):
    lead: str
    highlights: list[str] = Field(default_factory=list)
    detail: str


class LegalBasis(BaseModel):
    label: str
    kind: Literal["pasal", "sanksi"]


class NormRow(BaseModel):
    label: str
    value: str
    tone: Literal["accent", "neutral"] = "neutral"


class GraphNode(BaseModel):
    id: str
    label: str
    level: int = Field(ge=0)


class GraphEdge(BaseModel):
    source: str
    target: str


class GraphView(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class GraphLink(BaseModel):
    title: str
    detail: str
    degrees: int


class QuickAction(BaseModel):
    title: str
    text: str


class AskResponse(BaseModel):
    status: Literal["answered", "refused"]
    question: str
    message: str | None = None
    answer: AnswerText | None = None
    legal_basis: list[LegalBasis] = Field(default_factory=list)
    norm_summary: list[NormRow] = Field(default_factory=list)
    graph: GraphView | None = None
    graph_link: GraphLink | None = None
    adjustment_note: str | None = None
    quick_action: QuickAction | None = None
