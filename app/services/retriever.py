import math
import re
from collections import Counter

from app.services.graph_store import GraphStore, Provision
from app.services.text import OUT_OF_SCOPE, synonym_vocab, tokenize, tokenize_raw

TIME_INTENT = re.compile(
    r"\b(berapa lama|batas waktu|tenggat|jangka waktu|paling lambat|paling lama|dalam waktu|berapa hari|berapa jam)\b"
)
DEADLINE_IN_TEXT = re.compile(r"\d+\s*x\s*\d+\s*jam|\d+\s*tahun|\d+\s*bulan")

REF_PATTERN = re.compile(
    r"pasal\s+(\d+)(?:\s+ayat\s*\(?(\d+)\)?)?(?:\s+huruf\s+([a-z])\b)?",
    re.IGNORECASE,
)


class Retriever:
    def __init__(self, store: GraphStore, k1: float = 1.5, b: float = 0.75) -> None:
        self.store = store
        self.k1 = k1
        self.b = b
        self.doc_ids: list[str] = []
        self.doc_tokens: list[list[str]] = []
        for provision in store.provisions.values():
            if provision.kind == "huruf" or not provision.summary:
                continue
            parts = [provision.label, provision.summary]
            parts.extend(norm.summary for norm in store.norms_of(provision))
            self.doc_ids.append(provision.id)
            self.doc_tokens.append(tokenize(" ".join(parts)))
        self.vocab = {token for tokens in self.doc_tokens for token in tokens}
        self.known = self.vocab | synonym_vocab()
        self.avg_len = sum(len(t) for t in self.doc_tokens) / len(self.doc_tokens)
        frequency: Counter[str] = Counter()
        for tokens in self.doc_tokens:
            frequency.update(set(tokens))
        total = len(self.doc_tokens)
        self.idf = {
            token: math.log(1 + (total - count + 0.5) / (count + 0.5))
            for token, count in frequency.items()
        }
        self.term_counts = [Counter(tokens) for tokens in self.doc_tokens]
        self.has_deadline = [
            DEADLINE_IN_TEXT.search(store.provisions[i].summary.lower()) is not None
            for i in self.doc_ids
        ]

    def explicit(self, question: str) -> tuple[list[Provision], list[str]]:
        found: list[Provision] = []
        missing: list[str] = []
        for match in REF_PATTERN.finditer(question):
            number, ayat, huruf = match.group(1), match.group(2), match.group(3)
            ident = f"Pasal_{number}"
            label = f"Pasal {number}"
            if ayat:
                ident += f"_ayat_{ayat}"
                label += f" ayat ({ayat})"
            if huruf:
                ident += f"_huruf_{huruf.lower()}"
                label += f" huruf {huruf.lower()}"
            provision = self.store.provisions.get(ident)
            if provision is not None and provision.summary:
                found.append(provision)
                continue
            if provision is not None and provision.parts:
                children = [
                    self.store.provisions[p]
                    for p in provision.parts
                    if self.store.provisions[p].summary
                ]
                if children:
                    found.extend(children)
                    continue
            missing.append(label)
        unique: dict[str, Provision] = {p.id: p for p in found}
        return list(unique.values()), missing

    def coverage(self, question: str) -> float:
        tokens = tokenize_raw(question)
        if not tokens:
            return 0.0
        known = sum(1 for token in tokens if token in self.known)
        return known / len(tokens)

    def is_out_of_scope(self, question: str) -> bool:
        return OUT_OF_SCOPE.search(question.lower()) is not None

    def search(self, question: str, limit: int = 5) -> list[tuple[Provision, float]]:
        query = [t for t in tokenize(question) if t in self.vocab]
        scores: list[tuple[int, float]] = []
        wants_time = TIME_INTENT.search(question.lower()) is not None
        for index, counts in enumerate(self.term_counts):
            length = len(self.doc_tokens[index])
            score = 0.0
            for token in set(query):
                tf = counts.get(token, 0)
                if tf == 0:
                    continue
                norm = tf + self.k1 * (1 - self.b + self.b * length / self.avg_len)
                score += self.idf[token] * tf * (self.k1 + 1) / norm
            if score > 0 and wants_time and self.has_deadline[index]:
                score *= 1.5
            if score > 0:
                scores.append((index, score))
        scores.sort(key=lambda item: item[1], reverse=True)
        return [
            (self.store.provisions[self.doc_ids[index]], score)
            for index, score in scores[:limit]
        ]
