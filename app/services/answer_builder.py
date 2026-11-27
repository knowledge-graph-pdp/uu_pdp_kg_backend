import re

from app.schemas.ask import (
    AnswerText,
    AskResponse,
    GraphEdge,
    GraphLink,
    GraphNode,
    GraphView,
    LegalBasis,
    NormRow,
    QuickAction,
)
from app.services.graph_store import GraphStore, Provision

DOCUMENT = "UU No. 27 Tahun 2022"
QUICK_TITLES = {
    "Kewajiban": "Tindakan Cepat Pengendali Data",
    "Hak": "Hak Subjek Data",
    "Larangan": "Batasan Penting",
    "Sanksi": "Ancaman Sanksi",
}
DEADLINE_PATTERN = re.compile(r"\d+\s*x\s*\d+\s*jam|\d+\s*tahun|\d+\s*bulan", re.IGNORECASE)


def _basis_label(provision: Provision) -> str:
    return provision.label


def _lead(provision: Provision) -> tuple[str, list[str]]:
    lead = f"Berdasarkan {provision.label} {DOCUMENT} tentang Pelindungan Data Pribadi: {provision.summary}"
    highlights = [DOCUMENT, provision.label]
    match = DEADLINE_PATTERN.search(provision.summary)
    if match:
        highlights.append(match.group(0))
    return lead, highlights


def _detail(store: GraphStore, provision: Provision, others: list[Provision]) -> str:
    lines: list[str] = []
    for item in others[:2]:
        lines.append(f"{item.label}: {item.summary}")
    exceptions = store.exceptions_for(provision)
    if exceptions:
        names = ", ".join(e.label for e in exceptions[:3])
        lines.append(f"Pengecualian diatur pada {names}.")
    sanction_norms = store.sanction_norms_for(provision)
    if sanction_norms:
        lines.append(f"Konsekuensi: {sanction_norms[0].summary}")
    if not lines and provision.parent:
        parent = store.provisions[provision.parent]
        bab = store.bab_by_pasal.get(provision.number)
        lines.append(f"Ketentuan ini bagian dari {parent.label}" + (f", {bab}." if bab else "."))
    return " ".join(lines) if lines else "Tidak ada ketentuan terkait yang tercatat pada graf."


def _norm_rows(store: GraphStore, provision: Provision) -> list[NormRow]:
    rows: list[NormRow] = []
    norms = store.norms_of(provision)
    primary = norms[0] if norms else None
    rows.append(
        NormRow(
            label="Jenis Norma",
            value=primary.kind if primary else "Ketentuan",
            tone="accent",
        )
    )
    if primary and primary.actors:
        rows.append(NormRow(label="Ditujukan Kepada", value=" + ".join(primary.actors)))
    if primary and primary.deadline:
        rows.append(NormRow(label="Tenggat", value=primary.deadline, tone="accent"))
    else:
        sanction_norms = store.sanction_norms_for(provision)
        types = sorted({n.sanction_type for n in sanction_norms if n.sanction_type})
        if types:
            rows.append(NormRow(label="Jenis Sanksi", value=" + ".join(types), tone="accent"))
    bab = store.bab_by_pasal.get(provision.number)
    if bab and len(rows) < 3:
        rows.append(NormRow(label="Bab", value=bab.split(" ", 2)[0] + " " + bab.split(" ", 2)[1]))
    return rows[:3]


def _graph(store: GraphStore, provision: Provision) -> GraphView | None:
    nodes: dict[str, GraphNode] = {
        provision.id: GraphNode(id=provision.id, label=store.short_label(provision), level=0)
    }
    edges: list[GraphEdge] = []
    sanctions = store.sanctions_for(provision)[:2]
    sanction_ids = {s.id for s in sanctions}
    related = [r for r in store.related(provision) if r.id not in sanction_ids][:3]
    for item in related:
        nodes[item.id] = GraphNode(id=item.id, label=store.short_label(item), level=1)
        edges.append(GraphEdge(source=provision.id, target=item.id))
    for item in sanctions:
        nodes[item.id] = GraphNode(id=item.id, label=store.short_label(item), level=2)
        edges.append(GraphEdge(source=provision.id, target=item.id))
    if len(nodes) < 2:
        return None
    return GraphView(nodes=list(nodes.values()), edges=edges)


def _graph_link(store: GraphStore, provision: Provision, graph: GraphView | None) -> GraphLink | None:
    if graph is None:
        return None
    direct = len(graph.nodes) - 1
    sanctions = store.sanctions_for(provision)
    detail = f"{provision.label} terhubung langsung dengan {direct} ketentuan lain"
    if sanctions:
        detail += f", termasuk {sanctions[0].label} sebagai sanksi"
    degrees = max(1, min(store.relation_depth(provision), 3))
    return GraphLink(title="Koneksi Graf Terdeteksi", detail=detail, degrees=degrees)


def _quick_action(store: GraphStore, provision: Provision) -> QuickAction | None:
    norms = store.norms_of(provision)
    sanction_norms = store.sanction_norms_for(provision)
    if not norms or not sanction_norms:
        return None
    title = QUICK_TITLES.get(norms[0].kind, "Tindakan Cepat")
    return QuickAction(
        title=title,
        text=f"Pelanggaran ketentuan ini dapat berujung pada: {sanction_norms[0].summary}",
    )


def build_answer(
    store: GraphStore,
    question: str,
    primary: Provision,
    others: list[Provision],
) -> AskResponse:
    lead, highlights = _lead(primary)
    legal_basis = [LegalBasis(label=_basis_label(primary), kind="pasal")]
    for item in others[:2]:
        legal_basis.append(LegalBasis(label=_basis_label(item), kind="pasal"))
    for sanction in store.sanctions_for(primary)[:1]:
        legal_basis.append(LegalBasis(label=f"Sanksi: {sanction.label}", kind="sanksi"))
    graph = _graph(store, primary)
    return AskResponse(
        status="answered",
        question=question,
        answer=AnswerText(
            lead=lead,
            highlights=highlights,
            detail=_detail(store, primary, others),
        ),
        legal_basis=legal_basis,
        norm_summary=_norm_rows(store, primary),
        graph=graph,
        graph_link=_graph_link(store, primary, graph),
        adjustment_note=store.adjustment_note(),
        quick_action=_quick_action(store, primary),
    )
