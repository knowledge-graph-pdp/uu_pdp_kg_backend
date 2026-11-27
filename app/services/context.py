from app.services.graph_store import GraphStore, Provision


def _facts(store: GraphStore, provision: Provision) -> str:
    parts = [f"[{provision.id}] {provision.label}"]
    norms = store.norms_of(provision)
    if norms:
        norm = norms[0]
        parts.append(f"jenis norma: {norm.kind}")
        if norm.actors:
            parts.append("ditujukan kepada: " + ", ".join(norm.actors))
        if norm.deadline:
            parts.append(f"tenggat: {norm.deadline}")
    parts.append(f"ringkasan: {provision.summary}")
    sanctions = store.sanctions_for(provision)
    if sanctions:
        parts.append("sanksi pada: " + ", ".join(f"{s.label} ({s.id})" for s in sanctions[:3]))
    exceptions = store.exceptions_for(provision)
    if exceptions:
        parts.append("pengecualian pada: " + ", ".join(f"{e.label} ({e.id})" for e in exceptions[:3]))
    return " | ".join(parts)


def build_context(store: GraphStore, seeds: list[str], limit: int) -> tuple[str, list[str]]:
    ordered: list[str] = []

    def add(ident: str) -> None:
        provision = store.provisions.get(ident)
        if provision is None or not provision.summary or ident in ordered:
            return
        ordered.append(ident)

    for ident in seeds:
        add(ident)
    for ident in list(ordered):
        provision = store.provisions[ident]
        for sanction in store.sanctions_for(provision):
            add(sanction.id)
        for sibling in store.siblings(provision):
            add(sibling.id)
        for exception in store.exceptions_for(provision):
            add(exception.id)
    for ident in list(ordered):
        provision = store.provisions[ident]
        for other in provision.refers_to + provision.referred_by:
            add(other)
    ordered = ordered[:limit]
    lines = [_facts(store, store.provisions[i]) for i in ordered]
    return "\n".join(lines), ordered
