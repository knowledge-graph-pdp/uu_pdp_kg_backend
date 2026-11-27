import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.services import ask_service
from app.services.ask_service import AskEngine, HybridEngine
from app.services.graph_store import GraphStore
from app.services.llm_answerer import LLMAnswerer
from app.services.llm_client import LLMClient
from app.services.retriever import Retriever
from app.services.sparql_planner import SparqlPlanner

SPARQL = (
    "PREFIX pdp: <https://pdp-graph.example.org/ontology#> "
    "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> "
    "SELECT ?p ?label WHERE { ?p pdp:imposesObligation ?n ; rdfs:label ?label ; pdp:ringkasan ?r . "
    "?n pdp:hasDeadline ?dl . FILTER(CONTAINS(LCASE(STR(?r)), \"kegagalan\")) } LIMIT 20"
)


def make_engine(handler):
    settings = Settings(LLM_API_KEY="test-key")
    client = LLMClient(settings, transport=httpx.MockTransport(handler))
    store = GraphStore(settings.GRAPH_PATH)
    extractive = AskEngine(store, Retriever(store))
    return HybridEngine(extractive, SparqlPlanner(store, client), LLMAnswerer(store, client))


def reply(payload):
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(payload)}}]})


def scripted(answer):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        system = body["messages"][0]["content"]
        if "SPARQL" in system:
            return reply({"sparql": SPARQL})
        return reply(answer)

    return handler


GOOD = {
    "status": "answered",
    "primary_id": "Pasal_46_ayat_1",
    "cited_ids": ["Pasal_46_ayat_1", "Pasal_46_ayat_2"],
    "lead": "Berdasarkan UU No. 27 Tahun 2022, Pasal 46 ayat (1) mewajibkan pemberitahuan tertulis paling lambat 3x24 jam.",
    "highlights": ["UU No. 27 Tahun 2022", "3x24 jam", "frasa yang tidak ada"],
    "detail": "Pasal 46 ayat (2) mengatur isi pemberitahuan.",
}


def test_answer_uses_llm_text_and_graph_facts():
    engine = make_engine(scripted(GOOD))
    response = engine.answer("Berapa lama batas waktu pemberitahuan kebocoran data pribadi?")
    assert response.status == "answered"
    assert response.answer.lead.startswith("Berdasarkan UU No. 27 Tahun 2022")
    assert response.answer.highlights == ["UU No. 27 Tahun 2022", "3x24 jam"]
    labels = [b.label for b in response.legal_basis]
    assert labels[:2] == ["Pasal 46 ayat (1)", "Pasal 46 ayat (2)"]
    assert any(b.kind == "sanksi" for b in response.legal_basis)
    assert response.norm_summary[0].value == "Kewajiban"


def test_hallucinated_pasal_falls_back_to_graph_text():
    bad = {**GOOD, "lead": "Berdasarkan UU No. 27 Tahun 2022, Pasal 99 mengatur hal ini."}
    engine = make_engine(scripted(bad))
    response = engine.answer("Berapa lama batas waktu pemberitahuan kebocoran data pribadi?")
    assert "Pasal 99" not in response.answer.lead
    assert "3x24 jam" in response.answer.lead


def test_llm_refusal_returns_refused():
    engine = make_engine(scripted({"status": "refused"}))
    response = engine.answer("Bagaimana prosedur keamanan siber nasional?")
    assert response.status == "refused"


def test_unsafe_sparql_is_ignored():
    def handler(request: httpx.Request) -> httpx.Response:
        system = json.loads(request.content)["messages"][0]["content"]
        if "SPARQL" in system:
            return reply({"sparql": "SELECT ?p WHERE { SERVICE <http://evil.example/sparql> { ?p ?x ?y } }"})
        return reply(GOOD)

    engine = make_engine(handler)
    response = engine.answer("Berapa lama batas waktu pemberitahuan kebocoran data pribadi?")
    assert response.status == "answered"


def test_endpoint_maps_llm_errors(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={})

    engine = make_engine(handler)
    monkeypatch.setattr(ask_service, "get_engine", lambda: engine)
    with TestClient(app) as client:
        response = client.post("/api/v1/ask", json={"question": "Berapa lama batas waktu pemberitahuan kebocoran data pribadi?"})
    assert response.status_code == 502


def test_timeout_maps_to_504(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    engine = make_engine(handler)
    monkeypatch.setattr(ask_service, "get_engine", lambda: engine)
    with TestClient(app) as client:
        response = client.post("/api/v1/ask", json={"question": "Berapa lama batas waktu pemberitahuan kebocoran data pribadi?"})
    assert response.status_code == 504


def test_without_key_uses_extractive_engine():
    ask_service.get_engine.cache_clear()
    engine = ask_service.get_engine()
    assert isinstance(engine, AskEngine)
