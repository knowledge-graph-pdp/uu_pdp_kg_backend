import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import DCTERMS

PDP = Namespace("https://pdp-graph.example.org/ontology#")
D = Namespace("https://pdp-graph.example.org/data/")

NORM_LINKS = (
    PDP.establishesNorm,
    PDP.grantsRight,
    PDP.imposesObligation,
    PDP.imposesProhibition,
)
PROVISION_KINDS = {PDP.Pasal: "pasal", PDP.Ayat: "ayat", PDP.Huruf: "huruf"}
NORM_KINDS = {
    PDP.Hak: "Hak",
    PDP.Kewajiban: "Kewajiban",
    PDP.Larangan: "Larangan",
    PDP.Sanksi: "Sanksi",
}
ID_PATTERN = re.compile(r"^Pasal_(\d+)(?:_ayat_(\d+))?(?:_huruf_([a-z]))?$")
MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "Mei",
    "Jun",
    "Jul",
    "Agu",
    "Sep",
    "Okt",
    "Nov",
    "Des",
]


@dataclass
class Norm:
    id: str
    kind: str
    summary: str
    actors: list[str] = field(default_factory=list)
    deadline: str | None = None
    sanction_type: str | None = None
    sanctioned_by: list[str] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)


@dataclass
class Provision:
    id: str
    kind: str
    label: str
    summary: str
    number: int
    ayat: int | None
    huruf: str | None
    norm_ids: list[str] = field(default_factory=list)
    refers_to: list[str] = field(default_factory=list)
    referred_by: list[str] = field(default_factory=list)
    parts: list[str] = field(default_factory=list)
    parent: str | None = None


def _local(uri: URIRef) -> str:
    return str(uri).rsplit("/", 1)[-1]


def _text(graph: Graph, subject: URIRef, predicate: URIRef) -> str:
    value = graph.value(subject, predicate)
    return str(value) if isinstance(value, Literal) else ""


class GraphStore:
    def __init__(self, path: Path) -> None:
        graph = Graph()
        graph.parse(path, format="turtle")
        self.graph = graph
        self.provisions: dict[str, Provision] = {}
        self.norms: dict[str, Norm] = {}
        self.norm_owner: dict[str, str] = {}
        self.bab_by_pasal: dict[int, str] = {}
        self._load_provisions()
        self._load_norms()
        self._link()
        self._load_babs()

    def _load_provisions(self) -> None:
        graph = self.graph
        for type_uri, kind in PROVISION_KINDS.items():
            for subject in graph.subjects(RDF.type, type_uri):
                ident = _local(subject)
                match = ID_PATTERN.match(ident)
                if match is None:
                    continue
                number = int(match.group(1))
                ayat = int(match.group(2)) if match.group(2) else None
                huruf = match.group(3)
                self.provisions[ident] = Provision(
                    id=ident,
                    kind=kind,
                    label=_text(graph, subject, RDFS.label) or ident.replace("_", " "),
                    summary=_text(graph, subject, PDP.ringkasan),
                    number=number,
                    ayat=ayat,
                    huruf=huruf,
                )

    def _load_norms(self) -> None:
        graph = self.graph
        for type_uri, kind in NORM_KINDS.items():
            for subject in graph.subjects(RDF.type, type_uri):
                ident = _local(subject)
                actors = [
                    _text(graph, actor, RDFS.label)
                    for actor in graph.objects(subject, PDP.appliesTo)
                ]
                deadline_node = graph.value(subject, PDP.hasDeadline)
                deadline = _text(graph, deadline_node, RDFS.label) if deadline_node else None
                self.norms[ident] = Norm(
                    id=ident,
                    kind=kind,
                    summary=_text(graph, subject, PDP.ringkasan),
                    actors=[actor for actor in actors if actor],
                    deadline=deadline or None,
                    sanction_type=_text(graph, subject, PDP.sanksiTipe) or None,
                    sanctioned_by=sorted(
                        _local(o) for o in graph.objects(subject, PDP.sanctionedBy)
                    ),
                    exceptions=sorted(
                        _local(o) for o in graph.objects(subject, PDP.hasException)
                    ),
                )

    def _link(self) -> None:
        graph = self.graph
        for ident, provision in self.provisions.items():
            subject = D[ident]
            norm_ids: list[str] = []
            for predicate in NORM_LINKS:
                for obj in graph.objects(subject, predicate):
                    norm_id = _local(obj)
                    if norm_id in self.norms and norm_id not in norm_ids:
                        norm_ids.append(norm_id)
                        self.norm_owner.setdefault(norm_id, ident)
            provision.norm_ids = norm_ids
            provision.refers_to = sorted(
                _local(o) for o in graph.objects(subject, PDP.refersTo) if _local(o) in self.provisions
            )
            provision.referred_by = sorted(
                _local(o) for o in graph.objects(subject, PDP.referredBy) if _local(o) in self.provisions
            )
            provision.parts = sorted(
                (_local(o) for o in graph.objects(subject, PDP.hasPart) if _local(o) in self.provisions),
                key=self.sort_key,
            )
        for ident, provision in self.provisions.items():
            for part in provision.parts:
                self.provisions[part].parent = ident

    def _load_babs(self) -> None:
        graph = self.graph
        for bab in graph.subjects(RDF.type, PDP.Bab):
            label = _text(graph, bab, RDFS.label)
            for part in graph.objects(bab, PDP.hasPart):
                match = ID_PATTERN.match(_local(part))
                if match:
                    self.bab_by_pasal[int(match.group(1))] = label

    def sort_key(self, ident: str) -> tuple[int, int, str]:
        match = ID_PATTERN.match(ident)
        if match is None:
            return (0, 0, ident)
        return (int(match.group(1)), int(match.group(2) or 0), match.group(3) or "")

    def norms_of(self, provision: Provision) -> list[Norm]:
        return [self.norms[n] for n in provision.norm_ids]

    def sanctions_for(self, provision: Provision) -> list[Provision]:
        found: list[str] = []
        for norm in self.norms_of(provision):
            for sanction_norm in norm.sanctioned_by:
                owner = self.norm_owner.get(sanction_norm)
                if owner and owner not in found:
                    found.append(owner)
        for other_id in provision.referred_by:
            other = self.provisions[other_id]
            if any(n.kind == "Sanksi" for n in self.norms_of(other)) and other_id not in found:
                found.append(other_id)
        return [self.provisions[i] for i in sorted(found, key=self.sort_key)]

    def sanction_norms_for(self, provision: Provision) -> list[Norm]:
        found: list[Norm] = []
        for sanction in self.sanctions_for(provision):
            for norm in self.norms_of(sanction):
                if norm.kind == "Sanksi" and norm not in found:
                    found.append(norm)
        for norm in self.norms_of(provision):
            for sanction_norm in norm.sanctioned_by:
                candidate = self.norms.get(sanction_norm)
                if candidate and candidate not in found:
                    found.append(candidate)
        return found

    def exceptions_for(self, provision: Provision) -> list[Provision]:
        found: list[str] = []
        for norm in self.norms_of(provision):
            for ident in norm.exceptions:
                if ident in self.provisions and ident not in found:
                    found.append(ident)
        return [self.provisions[i] for i in sorted(found, key=self.sort_key)]

    def siblings(self, provision: Provision) -> list[Provision]:
        if provision.parent is None:
            return []
        parent = self.provisions[provision.parent]
        return [
            self.provisions[i]
            for i in parent.parts
            if i != provision.id and self.provisions[i].kind != "huruf" and self.provisions[i].summary
        ]

    def related(self, provision: Provision) -> list[Provision]:
        found: list[str] = []
        for ident in provision.refers_to + provision.referred_by:
            if ident not in found:
                found.append(ident)
        for sibling in self.siblings(provision):
            if sibling.id not in found:
                found.append(sibling.id)
        return [self.provisions[i] for i in found if i != provision.id]

    def relation_depth(self, provision: Provision, limit: int = 4) -> int:
        seen = {provision.id}
        frontier = [provision.id]
        depth = 0
        while frontier and depth < limit:
            nxt: list[str] = []
            for ident in frontier:
                current = self.provisions[ident]
                neighbors = set(current.refers_to) | set(current.referred_by)
                neighbors |= {s.id for s in self.sanctions_for(current)}
                for neighbor in neighbors:
                    if neighbor not in seen:
                        seen.add(neighbor)
                        nxt.append(neighbor)
            if not nxt:
                break
            depth += 1
            frontier = nxt
        return depth

    def adjustment_note(self) -> str | None:
        document = D.UU_27_2022
        issued = self.graph.value(document, DCTERMS.issued)
        norm = self.norms.get("Norm_74_0")
        if issued is None or norm is None or norm.deadline is None:
            return None
        years = re.match(r"(\d+)\s*tahun", norm.deadline)
        if years is None:
            return None
        start = date.fromisoformat(str(issued))
        end = start.replace(year=start.year + int(years.group(1)))
        return f"Masa penyesuaian UU PDP berakhir: {end.day} {MONTHS[end.month - 1]} {end.year}"

    def short_label(self, provision: Provision) -> str:
        text = f"P.{provision.number}"
        if provision.ayat is not None:
            text += f"({provision.ayat})"
        if provision.huruf is not None:
            text += provision.huruf
        return text
