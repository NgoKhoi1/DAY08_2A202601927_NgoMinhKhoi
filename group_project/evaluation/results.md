# RAG Evaluation Results

## Framework sử dụng

**RAGAS** (`ragas==0.1.21`) — 4 metrics chuẩn: Faithfulness, Answer Relevancy, Context Recall, Context Precision. LLM đánh giá: OpenAI (`OPENAI_API_KEY`, model theo `task10_generation`).

Golden dataset: 16 câu hỏi (`golden_dataset.json`).

---

## Overall Scores

| Metric | Config A (hybrid_rerank) | Config B (dense_only) | Δ (A-B) |
|--------|---|---|---|
| Faithfulness | 0.673 | 0.644 | +0.029 |
| Answer Relevance | 0.480 | 0.624 | -0.145 |
| Context Recall | 0.812 | 0.812 | +0.000 |
| Context Precision | 0.922 | 0.922 | +0.000 |
| **Average** | **0.722** | **0.751** | **-0.029** |

---

## A/B Comparison Analysis

**Config A (hybrid_rerank):** Semantic (dense) + BM25 (sparse) → merge bằng RRF → rerank lại bằng RRF trên list đã merge (`src/task9_retrieval_pipeline.py`, `use_reranking=True`).

**Config B (dense_only):** Semantic + BM25 → merge bằng RRF, **không** rerank thêm bước cuối (`use_reranking=False`) — vẫn là hybrid ở bước merge, chỉ bỏ bước rerank phụ.

**Kết luận:** Config **dense_only** có điểm trung bình cao hơn (0.751 vs 0.722). Chênh lệch chủ yếu đến từ bước rerank cuối giúp sắp xếp lại thứ tự context truyền cho LLM.

---

## Worst Performers (Bottom 3 — theo Config A)

| # | Question | Faithfulness | Relevance | Recall | Precision | Root Cause (gợi ý) |
|---|----------|-------------|-----------|--------|-----------|---------------------|
| 1 | Tôi vừa mua một chiếc laptop chơi game giá 30 triệu, làm sao... | 0.00 | 0.00 | 0.00 | 0.00 | Thiếu context liên quan trong vector store |
| 2 | Cần chuẩn bị bằng chứng gì khi yêu cầu trả hàng/hoàn tiền?... | 0.00 | 0.00 | 0.00 | 1.00 | Thiếu context liên quan trong vector store |
| 3 | Yêu cầu về hình ảnh sản phẩm khi đăng bán trên Shopee là gì?... | 0.00 | 0.00 | 1.00 | 1.00 | LLM trả lời không bám sát context |

---

## Recommendations

### Cải tiến 1
**Action:** Tăng `top_k` retrieval trước rerank (hiện `top_k * 2` ở Task 9) nếu Context Recall thấp, để có nhiều candidate hơn trước khi lọc.
**Expected impact:** Tăng Context Recall, giảm rủi ro bỏ sót đoạn liên quan nằm ngoài top-k ban đầu.

### Cải tiến 2
**Action:** Với câu hỏi ngoài phạm vi dữ liệu (vd câu hỏi lạc đề trong golden dataset), kiểm tra lại `SCORE_THRESHOLD` (đang 0.3) đã calibrate đúng theo corpus thực tế chưa.
**Expected impact:** Giảm Faithfulness thấp do LLM cố trả lời dù context không liên quan.

### Cải tiến 3
**Action:** Thử `rerank_cross_encoder` (Jina Reranker, cần `JINA_API_KEY`) thay cho RRF-only để so sánh thêm 1 config C.
**Expected impact:** Cross-encoder rerank thường cải thiện Context Precision so với RRF thuần rank-based.
