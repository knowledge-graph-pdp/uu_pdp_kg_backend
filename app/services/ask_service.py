from functools import lru_cache
from typing import Protocol

from app.core.config import settings
from app.schemas.ask import AskResponse
from app.services.answer_builder import build_answer
from app.services.context import build_context
from app.services.graph_store import GraphStore
from app.services.llm_answerer import LLMAnswerer
from app.services.llm_client import LLMClient
from app.services.retriever import Retriever
from app.services.sparql_planner import SparqlPlanner

REFUSAL_MESSAGE = (
    "Pertanyaan ini tidak terhubung ke pasal mana pun di UU PDP, "
    "jadi sistem tidak menjawab. Ajukan pertanyaan seputar UU No. 27 Tahun 2022."
)


class Engine(Protocol):
    def answer(self, question: str) -> AskResponse: ...


class AskEngine:
    def __init__(self, store: GraphStore, retriever: Retriever) -> None:
        self.store = store
        self.retriever = retriever

    def refuse(self, question: str, message: str = REFUSAL_MESSAGE) -> AskResponse:
        return AskResponse(status="refused", question=question, message=message)

    def missing_message(self, missing: list[str]) -> str:
        names = ", ".join(missing)
        return (
            f"{names} tidak ditemukan pada graf UU PDP, jadi sistem tidak menjawab. "
            "Periksa nomor pasal atau ayat yang dimaksud."
        )

    def answer(self, question: str) -> AskResponse:
        if self.retriever.is_out_of_scope(question):
            return self.refuse(question)
        explicit, missing = self.retriever.explicit(question)
        if explicit:
            primary = explicit[0]
            others = explicit[1:] or self.store.siblings(primary)
            return build_answer(self.store, question, primary, others)
        if missing:
            return self.refuse(question, self.missing_message(missing))
        if self.retriever.coverage(question) < settings.MIN_QUERY_COVERAGE:
            return self.refuse(question)
        results = self.retriever.search(question)
        if not results or results[0][1] < settings.MIN_RETRIEVAL_SCORE:
            return self.refuse(question)
        primary = results[0][0]
        others = [p for p, _ in results[1:4] if p.id != primary.id]
        return build_answer(self.store, question, primary, others)


class HybridEngine:
    def __init__(self, extractive: AskEngine, planner: SparqlPlanner, answerer: LLMAnswerer) -> None:
        self.extractive = extractive
        self.planner = planner
        self.answerer = answerer

    def answer(self, question: str) -> AskResponse:
        base = self.extractive
        store = base.store
        if base.retriever.is_out_of_scope(question):
            return base.refuse(question)
        explicit, missing = base.retriever.explicit(question)
        if missing and not explicit:
            return base.refuse(question, base.missing_message(missing))

        seeds: list[str] = [p.id for p in explicit[:4]]
        if not explicit:
            _, sparql_ids = self.planner.run(question)
            for ident in sparql_ids:
                if ident not in seeds:
                    seeds.append(ident)
        for provision, _ in base.retriever.search(question, limit=5):
            if provision.id not in seeds:
                seeds.append(provision.id)
        if not seeds:
            return base.refuse(question)

        context, allowed = build_context(store, seeds, settings.LLM_MAX_CONTEXT_PROVISIONS)
        data = self.answerer.ask(question, context)
        if str(data.get("status", "")).lower() != "answered":
            return base.refuse(question)

        valid = [
            i
            for i in [data.get("primary_id"), *(data.get("cited_ids") or []), *seeds]
            if isinstance(i, str) and i in allowed and store.provisions[i].kind != "huruf"
        ]
        if not valid:
            return base.refuse(question)
        primary = store.provisions[valid[0]]
        cited_others = [
            store.provisions[i]
            for i in (data.get("cited_ids") or [])
            if isinstance(i, str) and i in allowed and i != primary.id and store.provisions[i].kind != "huruf"
        ]
        others = cited_others or store.siblings(primary)
        draft = build_answer(store, question, primary, others)
        composed = self.answerer.compose(draft, data, allowed)
        if composed is None:
            return base.refuse(question)
        return composed


@lru_cache
def get_engine() -> Engine:
    store = GraphStore(settings.GRAPH_PATH)
    extractive = AskEngine(store, Retriever(store))
    if not settings.llm_enabled:
        return extractive
    client = LLMClient(settings)
    return HybridEngine(extractive, SparqlPlanner(store, client), LLMAnswerer(store, client))


def answer_question(question: str) -> AskResponse:
    return get_engine().answer(question)
