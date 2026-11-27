import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.ask_service import get_engine


def main() -> None:
    path = ROOT / "data" / "eval" / "pdp_qa.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    engine = get_engine()
    engine = getattr(engine, "extractive", engine)
    stats: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    misses: list[str] = []
    for row in rows:
        response = engine.answer(row["pertanyaan"])
        kind = row["tipe"]
        if not row["dapat_dijawab"]:
            ok = response.status == "refused"
        else:
            cited = row["sitasi"].split("|")[0]
            labels = {cited.replace("_ayat_", " ayat (").replace("_", " ") + (")" if "_ayat_" in cited else "")}
            shown = [b.label for b in response.legal_basis if b.kind == "pasal"]
            ok = response.status == "answered" and any(label in shown for label in labels)
        stats[kind][0] += int(ok)
        stats[kind][1] += 1
        if not ok and len(misses) < 15:
            misses.append(f"{kind}: {row['pertanyaan']} -> {response.status} {[b.label for b in response.legal_basis]} want {row['sitasi']}")
    total_ok = sum(v[0] for v in stats.values())
    total = sum(v[1] for v in stats.values())
    for kind, (ok, count) in sorted(stats.items()):
        print(f"{kind:14s} {ok}/{count}")
    print(f"{'total':14s} {total_ok}/{total}")
    for line in misses:
        print(line)


if __name__ == "__main__":
    main()
