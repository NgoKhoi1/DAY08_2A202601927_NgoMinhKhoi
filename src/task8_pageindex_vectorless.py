"""
Task 8 — PageIndex Vectorless RAG.

Đăng ký tài khoản tại: https://pageindex.ai/
SDK & sample code: https://github.com/VectifyAI/PageIndex

PageIndex cho phép RAG mà không cần vector store — sử dụng
structural understanding của document thay vì embedding.

Cài đặt:
    pip install pageindex

Hướng dẫn:
    1. Đăng ký account tại pageindex.ai
    2. Lấy API key
    3. Upload documents
    4. Query sử dụng PageIndex API

Lưu ý: API `/retrieval` của PageIndex hiện đã deprecated (vẫn hoạt động, nhưng response
có field "deprecation" cảnh báo) và trả kết quả trong "retrieved_nodes" — mỗi node có
"relevant_contents": list[list[{section_title, relevant_content}]]. In response thật ra
(json.dumps(...)) trước khi viết logic parse, đừng đoán schema từ ví dụ code cũ.
"""

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
COMBINED_PDF_PATH = Path(__file__).parent.parent / "data" / "landing" / "_pageindex_combined.pdf"
DOC_ID_PATH = Path(__file__).parent.parent / "data" / "pageindex_doc_id.json"

# Font Unicode TTF để render tiếng Việt khi gộp markdown -> PDF (PageIndex chỉ nhận PDF).
_FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path(r"C:\Windows\Fonts\seguisym.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
]


def _find_unicode_font() -> Path | None:
    for candidate in _FONT_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def _combine_markdown_to_pdf(md_files: list[Path]) -> Path:
    """
    Gộp toàn bộ markdown trong data/standardized/ thành 1 file PDF duy nhất
    (PageIndex chỉ nhận PDF, không nhận .md trực tiếp).
    """
    from fpdf import FPDF

    pdf = FPDF()
    font_path = _find_unicode_font()

    for md_file in md_files:
        pdf.add_page()
        if font_path:
            pdf.add_font("Body", "", str(font_path))
            pdf.set_font("Body", size=14)
        else:
            pdf.set_font("Helvetica", size=14)
        pdf.multi_cell(0, 8, md_file.stem)
        pdf.ln(2)
        if font_path:
            pdf.set_font("Body", size=10)
        else:
            pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 6, md_file.read_text(encoding="utf-8"))

    COMBINED_PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(COMBINED_PDF_PATH))
    return COMBINED_PDF_PATH


def upload_documents() -> str | None:
    """
    Upload toàn bộ markdown documents lên PageIndex (gộp thành 1 PDF).
    Lưu doc_id vào DOC_ID_PATH để pageindex_search() tái sử dụng.
    """
    if not PAGEINDEX_API_KEY:
        print("⚠ Hãy set PAGEINDEX_API_KEY trong file .env — bỏ qua upload.")
        return None

    md_files = sorted(STANDARDIZED_DIR.rglob("*.md"))
    if not md_files:
        print("⚠ Không có file .md trong data/standardized/ — chạy Task 3 trước.")
        return None

    print(f"Đang gộp {len(md_files)} file markdown thành 1 PDF...")
    pdf_path = _combine_markdown_to_pdf(md_files)

    from pageindex import PageIndexClient

    client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
    resp = client.submit_document(str(pdf_path))
    doc_id = resp.get("doc_id") or resp.get("id")
    print(f"  ✓ Uploaded -> doc_id={doc_id}")

    DOC_ID_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_ID_PATH.write_text(json.dumps({"doc_id": doc_id}), encoding="utf-8")

    print("  Đang chờ PageIndex xử lý (tree generation + OCR)...")
    for _ in range(30):
        if client.is_retrieval_ready(doc_id):
            print("  ✓ Document sẵn sàng để truy vấn.")
            return doc_id
        time.sleep(10)

    print("  ⚠ Vẫn đang xử lý sau thời gian chờ — thử query lại sau.")
    return doc_id


def _get_doc_id() -> str | None:
    if DOC_ID_PATH.exists():
        return json.loads(DOC_ID_PATH.read_text(encoding="utf-8")).get("doc_id")
    return None


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Vectorless retrieval sử dụng PageIndex.
    Dùng làm fallback khi hybrid search không có kết quả tốt.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,
            'score': float,
            'metadata': dict,
            'source': 'pageindex'   # Đánh dấu nguồn retrieval
        }
    """
    if not PAGEINDEX_API_KEY:
        print("⚠ PAGEINDEX_API_KEY chưa được set — không thể dùng PageIndex fallback.")
        return []

    doc_id = _get_doc_id()
    if not doc_id:
        print("⚠ Chưa có document nào trên PageIndex — chạy upload_documents() trước.")
        return []

    from pageindex import PageIndexAPIError, PageIndexClient

    client = PageIndexClient(api_key=PAGEINDEX_API_KEY)

    try:
        resp = client.submit_query(doc_id=doc_id, query=query)
        retrieval_id = resp.get("retrieval_id") or resp.get("id")

        retrieval = None
        for _ in range(20):
            retrieval = client.get_retrieval(retrieval_id)
            if retrieval.get("status") == "completed":
                break
            time.sleep(3)

        if not retrieval or retrieval.get("status") != "completed":
            print("⚠ PageIndex retrieval chưa hoàn tất trong thời gian chờ.")
            return []

        results = []
        rank = 0
        for node in retrieval.get("retrieved_nodes", []):
            for group in node.get("relevant_contents", []):
                for item in group:
                    rank += 1
                    results.append({
                        "content": item.get("relevant_content", ""),
                        "score": round(1.0 / rank, 4),  # PageIndex không trả score trực tiếp
                        "metadata": {"section": item.get("section_title", "")},
                        "source": "pageindex",
                    })
        return results[:top_k]
    except PageIndexAPIError as e:
        print(f"⚠ PageIndex API error: {e}")
        return []


if __name__ == "__main__":
    if not PAGEINDEX_API_KEY:
        print("⚠ Hãy set PAGEINDEX_API_KEY trong file .env")
        print("  Đăng ký tại: https://pageindex.ai/")
    else:
        print("Uploading documents...")
        upload_documents()

        print("\nTest query:")
        results = pageindex_search("danh sách sản phẩm cấm đăng bán", top_k=3)
        for r in results:
            print(f"[{r['score']:.3f}] {r['content'][:100]}...")
