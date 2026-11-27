import re

from pydantic import BaseModel

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

ADJUSTMENT_NOTE = "Masa penyesuaian UU PDP berakhir: 17 Okt 2024"

REFUSAL_MESSAGE = (
    "Pertanyaan ini tidak terhubung ke pasal mana pun di UU PDP, "
    "jadi sistem tidak menjawab. Ajukan pertanyaan seputar UU No. 27 Tahun 2022."
)


class KnowledgeEntry(BaseModel):
    keywords: tuple[str, ...]
    answer: AnswerText
    legal_basis: list[LegalBasis]
    norm_summary: list[NormRow]
    graph: GraphView
    graph_detail: str
    quick_action: QuickAction


ENTRIES: list[KnowledgeEntry] = [
    KnowledgeEntry(
        keywords=(
            "kebocoran",
            "bocor",
            "3x24",
            "3 x 24",
            "notifikasi",
            "pemberitahuan",
            "kegagalan",
        ),
        answer=AnswerText(
            lead=(
                "Berdasarkan UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi, "
                "dalam hal terjadi kegagalan pelindungan data pribadi, Pengendali Data "
                "Pribadi wajib menyampaikan pemberitahuan tertulis paling lambat "
                "3 × 24 (tiga kali dua puluh empat) jam kepada Subjek Data Pribadi "
                "dan lembaga pengawas terkait."
            ),
            highlights=["UU No. 27 Tahun 2022", "3 × 24 (tiga kali dua puluh empat) jam"],
            detail=(
                "Pemberitahuan minimal harus memuat: data pribadi yang terungkap, kapan "
                "dan bagaimana data terungkap, serta upaya penanganan dan pemulihan atas "
                "kegagalan oleh Pengendali Data Pribadi."
            ),
        ),
        legal_basis=[
            LegalBasis(label="Pasal 46 ayat (1)", kind="pasal"),
            LegalBasis(label="Pasal 46 ayat (2)", kind="pasal"),
            LegalBasis(label="Sanksi: Pasal 57 ayat (2)", kind="sanksi"),
        ],
        norm_summary=[
            NormRow(label="Tenggat Notifikasi", value="3 × 24 Jam", tone="accent"),
            NormRow(label="Penerima Pemberitahuan", value="Subjek + Lembaga"),
            NormRow(label="Klasifikasi Insiden", value="Kegagalan Pelindungan", tone="accent"),
        ],
        graph=GraphView(
            nodes=[
                GraphNode(id="p46", label="P.46", level=0),
                GraphNode(id="p46a1", label="Ayat 1", level=1),
                GraphNode(id="p46a2", label="Ayat 2", level=1),
                GraphNode(id="p57", label="P.57", level=2),
                GraphNode(id="sanksi", label="", level=3),
            ],
            edges=[
                GraphEdge(source="p46", target="p46a1"),
                GraphEdge(source="p46", target="p46a2"),
                GraphEdge(source="p46a1", target="p57"),
                GraphEdge(source="p57", target="sanksi"),
            ],
        ),
        graph_detail="Pasal 46 terhubung langsung dengan Pasal 57 tentang sanksi administratif",
        quick_action=QuickAction(
            title="Tindakan Cepat Pengendali Data",
            text=(
                "Kegagalan penyampaian dalam 3×24 jam dapat memicu pemeriksaan kepatuhan "
                "oleh lembaga pengawas pelindungan data pribadi serta pengenaan sanksi "
                "administratif."
            ),
        ),
    ),
    KnowledgeEntry(
        keywords=("anak", "orang tua", "orangtua", "wali"),
        answer=AnswerText(
            lead=(
                "Berdasarkan UU No. 27 Tahun 2022, pemrosesan data pribadi anak "
                "diselenggarakan secara khusus dan wajib mendapat persetujuan "
                "orang tua anak dan/atau wali anak."
            ),
            highlights=["UU No. 27 Tahun 2022", "persetujuan orang tua anak dan/atau wali anak"],
            detail=(
                "Persetujuan tersebut harus sesuai dengan ketentuan peraturan "
                "perundang-undangan yang berlaku."
            ),
        ),
        legal_basis=[
            LegalBasis(label="Pasal 25 ayat (1)", kind="pasal"),
            LegalBasis(label="Pasal 25 ayat (2)", kind="pasal"),
            LegalBasis(label="Sanksi: Pasal 57 ayat (2)", kind="sanksi"),
        ],
        norm_summary=[
            NormRow(label="Subjek Data", value="Anak"),
            NormRow(label="Persetujuan Dari", value="Orang Tua / Wali", tone="accent"),
            NormRow(label="Sifat Pemrosesan", value="Khusus", tone="accent"),
        ],
        graph=GraphView(
            nodes=[
                GraphNode(id="p25", label="P.25", level=0),
                GraphNode(id="p25a1", label="Ayat 1", level=1),
                GraphNode(id="p25a2", label="Ayat 2", level=1),
                GraphNode(id="p57", label="P.57", level=2),
                GraphNode(id="sanksi", label="", level=3),
            ],
            edges=[
                GraphEdge(source="p25", target="p25a1"),
                GraphEdge(source="p25", target="p25a2"),
                GraphEdge(source="p25a2", target="p57"),
                GraphEdge(source="p57", target="sanksi"),
            ],
        ),
        graph_detail="Pasal 25 terhubung langsung dengan Pasal 57 tentang sanksi administratif",
        quick_action=QuickAction(
            title="Tindakan Cepat Pengendali Data",
            text=(
                "Pastikan mekanisme persetujuan orang tua atau wali tersedia sebelum "
                "memproses data pribadi anak."
            ),
        ),
    ),
    KnowledgeEntry(
        keywords=("hapus", "menghapus", "penghapusan", "musnah", "memusnahkan"),
        answer=AnswerText(
            lead=(
                "Berdasarkan UU No. 27 Tahun 2022, Subjek Data Pribadi berhak "
                "mengakhiri pemrosesan, menghapus, dan/atau memusnahkan data pribadi "
                "tentang dirinya, dan Pengendali Data Pribadi wajib melakukan "
                "penghapusan data pribadi pada kondisi tertentu."
            ),
            highlights=["UU No. 27 Tahun 2022", "menghapus, dan/atau memusnahkan"],
            detail=(
                "Kewajiban penghapusan antara lain berlaku ketika data tidak lagi "
                "diperlukan, persetujuan ditarik, atau data diproses secara melawan hukum."
            ),
        ),
        legal_basis=[
            LegalBasis(label="Pasal 8", kind="pasal"),
            LegalBasis(label="Pasal 43 ayat (1)", kind="pasal"),
            LegalBasis(label="Sanksi: Pasal 57 ayat (2)", kind="sanksi"),
        ],
        norm_summary=[
            NormRow(label="Hak Subjek", value="Hapus / Musnahkan", tone="accent"),
            NormRow(label="Kewajiban", value="Pengendali Data"),
            NormRow(label="Pemicu", value="Tujuan Selesai / Cabut Persetujuan", tone="accent"),
        ],
        graph=GraphView(
            nodes=[
                GraphNode(id="p8", label="P.8", level=0),
                GraphNode(id="p43", label="P.43", level=1),
                GraphNode(id="p57", label="P.57", level=2),
                GraphNode(id="sanksi", label="", level=3),
            ],
            edges=[
                GraphEdge(source="p8", target="p43"),
                GraphEdge(source="p43", target="p57"),
                GraphEdge(source="p57", target="sanksi"),
            ],
        ),
        graph_detail="Pasal 8 terhubung dengan kewajiban Pasal 43 dan sanksi Pasal 57",
        quick_action=QuickAction(
            title="Tindakan Cepat Pengendali Data",
            text=(
                "Siapkan prosedur penghapusan data pribadi yang dapat dijalankan saat "
                "Subjek Data Pribadi mengajukan permintaan."
            ),
        ),
    ),
    KnowledgeEntry(
        keywords=("dpo", "pejabat", "petugas", "penunjukan", "data protection officer"),
        answer=AnswerText(
            lead=(
                "Berdasarkan UU No. 27 Tahun 2022, Pengendali dan Prosesor Data "
                "Pribadi wajib menunjuk pejabat atau petugas yang melaksanakan fungsi "
                "pelindungan data pribadi dalam kondisi tertentu."
            ),
            highlights=["UU No. 27 Tahun 2022", "menunjuk pejabat atau petugas"],
            detail=(
                "Kondisinya meliputi pemrosesan untuk pelayanan publik, kegiatan inti "
                "yang memerlukan pemantauan teratur dan sistematis atas data pribadi "
                "skala besar, serta kegiatan inti dengan data pribadi spesifik atau "
                "terkait tindak pidana."
            ),
        ),
        legal_basis=[
            LegalBasis(label="Pasal 53 ayat (1)", kind="pasal"),
            LegalBasis(label="Pasal 54", kind="pasal"),
            LegalBasis(label="Sanksi: Pasal 57 ayat (2)", kind="sanksi"),
        ],
        norm_summary=[
            NormRow(label="Kewajiban", value="Menunjuk Pejabat PDP", tone="accent"),
            NormRow(label="Jumlah Kondisi Pemicu", value="3 Kondisi"),
            NormRow(label="Tugas Minimal", value="4 Fungsi", tone="accent"),
        ],
        graph=GraphView(
            nodes=[
                GraphNode(id="p53", label="P.53", level=0),
                GraphNode(id="p54", label="P.54", level=1),
                GraphNode(id="p57", label="P.57", level=2),
                GraphNode(id="sanksi", label="", level=3),
            ],
            edges=[
                GraphEdge(source="p53", target="p54"),
                GraphEdge(source="p53", target="p57"),
                GraphEdge(source="p57", target="sanksi"),
            ],
        ),
        graph_detail="Pasal 53 terhubung dengan tugas Pasal 54 dan sanksi Pasal 57",
        quick_action=QuickAction(
            title="Tindakan Cepat Pengendali Data",
            text=(
                "Periksa apakah kegiatan pemrosesan Anda memenuhi salah satu kondisi "
                "wajib penunjukan pejabat pelindungan data pribadi."
            ),
        ),
    ),
]


def _normalize(text: str) -> str:
    lowered = text.lower()
    return re.sub(r"[^\w\s/]", " ", lowered)


def _score(entry: KnowledgeEntry, text: str) -> int:
    return sum(1 for keyword in entry.keywords if keyword in text)


def answer_question(question: str) -> AskResponse:
    text = _normalize(question)
    best = max(ENTRIES, key=lambda entry: _score(entry, text))

    if _score(best, text) == 0:
        return AskResponse(
            status="refused",
            question=question,
            message=REFUSAL_MESSAGE,
        )

    return AskResponse(
        status="answered",
        question=question,
        answer=best.answer,
        legal_basis=best.legal_basis,
        norm_summary=best.norm_summary,
        graph=best.graph,
        graph_link=GraphLink(
            title="Koneksi Graf Terdeteksi",
            detail=best.graph_detail,
            degrees=max(node.level for node in best.graph.nodes),
        ),
        adjustment_note=ADJUSTMENT_NOTE,
        quick_action=best.quick_action,
    )
