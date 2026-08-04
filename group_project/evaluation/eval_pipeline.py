"""
RAG Evaluation Pipeline — dùng RAGAS.

Yêu cầu:
    1. Load golden_dataset.json (≥15 Q&A pairs)
    2. Chạy RAG pipeline trên từng question
    3. Evaluate với 4 metrics: faithfulness, relevance, context_recall, context_precision
    4. So sánh A/B ít nhất 2 configs
    5. Export results ra results.md

Lưu ý rate limit nếu dùng model OpenRouter ":free": RAGAS gọi LLM RẤT NHIỀU LẦN
(không phải 1 lần/câu hỏi mà nhiều lần/metric/câu hỏi). Model free của OpenRouter giới hạn
50 request/ngày CHO CẢ TÀI KHOẢN. Nếu chạy full 15+ câu hỏi mà bị rate limit giữa
chừng, thử giảm xuống subset 5 câu để chạy kịp trong buổi, hoặc nạp $10 credit để mở khóa
1000 request/ngày. Dự án này dùng OPENAI_API_KEY trực tiếp (không qua OpenRouter free tier)
nên ít rủi ro rate limit hơn, nhưng vẫn tốn phí thật — theo dõi usage nếu chạy full dataset
nhiều lần.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
RESULTS_PATH = Path(__file__).parent / "results.md"

METRIC_NAMES = ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]


def load_golden_dataset() -> list[dict]:
    """Load golden dataset từ JSON file."""
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# RAGAS
# =============================================================================

def _run_rag_for_dataset(golden_dataset: list[dict], config: dict) -> dict:
    """
    Chạy RAG pipeline (retrieve + generate) cho từng câu hỏi trong golden_dataset,
    dưới 1 config cụ thể (vd use_reranking True/False).

    Returns:
        eval_data theo format RAGAS: {'question', 'answer', 'contexts', 'ground_truth'}
    """
    from src.task9_retrieval_pipeline import retrieve
    from src.task10_generation import (
        SYSTEM_PROMPT, TEMPERATURE, TOP_P, _get_llm_client_and_model,
        format_context, reorder_for_llm,
    )

    client, model = _get_llm_client_and_model()

    eval_data = {"question": [], "answer": [], "contexts": [], "ground_truth": []}

    for item in golden_dataset:
        query = item["question"]
        chunks = retrieve(
            query,
            top_k=config.get("top_k", 5),
            score_threshold=config.get("score_threshold", 0.3),
            use_reranking=config.get("use_reranking", True),
        )
        reordered = reorder_for_llm(chunks)
        context = format_context(reordered) if reordered else "(Không có tài liệu liên quan.)"
        user_message = f"Context:\n{context}\n\n---\n\nQuestion: {query}"

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        answer = response.choices[0].message.content

        eval_data["question"].append(query)
        eval_data["answer"].append(answer)
        eval_data["contexts"].append([c["content"] for c in chunks] or ["(no context retrieved)"])
        eval_data["ground_truth"].append(item["expected_answer"])

    return eval_data


def evaluate_with_ragas(golden_dataset: list[dict], config: dict) -> "pandas.DataFrame":
    """
    Evaluate RAG pipeline sử dụng RAGAS, dưới 1 config retrieval cụ thể.

    Returns: pandas DataFrame với 1 row/câu hỏi, cột = metric scores.
    """
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    eval_data = _run_rag_for_dataset(golden_dataset, config)
    dataset = Dataset.from_dict(eval_data)

    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
    )
    df = result.to_pandas()
    df["question"] = eval_data["question"]
    return df


# =============================================================================
# A/B Comparison
# =============================================================================

def compare_configs(golden_dataset: list[dict]) -> dict:
    """
    So sánh A/B giữa 2 configs của Task 9 retrieval pipeline:
        - Config A: hybrid search + RRF reranking (mặc định của retrieve())
        - Config B: dense-only, không reranking (chỉ dùng kết quả RRF merge thô)
    """
    configs = {
        "hybrid_rerank": {"use_reranking": True, "top_k": 5, "score_threshold": 0.3},
        "dense_only": {"use_reranking": False, "top_k": 5, "score_threshold": 0.3},
    }

    results = {}
    for config_name, params in configs.items():
        print(f"\n=== Evaluating config: {config_name} ({params}) ===")
        df = evaluate_with_ragas(golden_dataset, params)
        results[config_name] = df
        print(df[METRIC_NAMES].mean())

    return results


# =============================================================================
# Export Results
# =============================================================================

def export_results(results: dict):
    """Export evaluation results (2 configs) to results.md"""
    config_names = list(results.keys())
    df_a = results[config_names[0]]
    df_b = results[config_names[1]]

    means_a = df_a[METRIC_NAMES].mean()
    means_b = df_b[METRIC_NAMES].mean()

    metric_labels = {
        "faithfulness": "Faithfulness",
        "answer_relevancy": "Answer Relevance",
        "context_recall": "Context Recall",
        "context_precision": "Context Precision",
    }

    content = "# RAG Evaluation Results\n\n"
    content += "## Framework sử dụng\n\n"
    content += "**RAGAS** (`ragas==0.1.21`) — 4 metrics chuẩn: Faithfulness, Answer Relevancy, "
    content += "Context Recall, Context Precision. LLM đánh giá: OpenAI (`OPENAI_API_KEY`, model theo `task10_generation`).\n\n"
    content += f"Golden dataset: {len(df_a)} câu hỏi (`golden_dataset.json`).\n\n"
    content += "---\n\n## Overall Scores\n\n"
    content += f"| Metric | Config A ({config_names[0]}) | Config B ({config_names[1]}) | Δ (A-B) |\n"
    content += "|--------|---|---|---|\n"
    for m in METRIC_NAMES:
        a, b = means_a[m], means_b[m]
        content += f"| {metric_labels[m]} | {a:.3f} | {b:.3f} | {a - b:+.3f} |\n"
    avg_a, avg_b = means_a[METRIC_NAMES].mean(), means_b[METRIC_NAMES].mean()
    content += f"| **Average** | **{avg_a:.3f}** | **{avg_b:.3f}** | **{avg_a - avg_b:+.3f}** |\n"

    content += "\n---\n\n## A/B Comparison Analysis\n\n"
    content += "**Config A (hybrid_rerank):** Semantic (dense) + BM25 (sparse) → merge bằng RRF → "
    content += "rerank lại bằng RRF trên list đã merge (`src/task9_retrieval_pipeline.py`, `use_reranking=True`).\n\n"
    content += "**Config B (dense_only):** Semantic + BM25 → merge bằng RRF, **không** rerank thêm bước cuối "
    content += "(`use_reranking=False`) — vẫn là hybrid ở bước merge, chỉ bỏ bước rerank phụ.\n\n"
    winner = config_names[0] if avg_a >= avg_b else config_names[1]
    content += f"**Kết luận:** Config **{winner}** có điểm trung bình cao hơn "
    content += f"({max(avg_a, avg_b):.3f} vs {min(avg_a, avg_b):.3f}). "
    content += "Chênh lệch chủ yếu đến từ bước rerank cuối giúp sắp xếp lại thứ tự context truyền cho LLM.\n\n"

    content += "---\n\n## Worst Performers (Bottom 3 — theo Config A)\n\n"
    df_a_sorted = df_a.copy()
    df_a_sorted["avg_score"] = df_a_sorted[METRIC_NAMES].mean(axis=1)
    worst = df_a_sorted.sort_values("avg_score").head(3)
    content += "| # | Question | Faithfulness | Relevance | Recall | Precision | Root Cause (gợi ý) |\n"
    content += "|---|----------|-------------|-----------|--------|-----------|---------------------|\n"
    for i, (_, row) in enumerate(worst.iterrows(), 1):
        q = str(row["question"])[:60]
        cause = "Thiếu context liên quan trong vector store" if row["context_recall"] < 0.5 else \
                "Context lấy về không đủ precise" if row["context_precision"] < 0.5 else \
                "LLM trả lời không bám sát context" if row["faithfulness"] < 0.5 else "Chưa rõ"
        content += (
            f"| {i} | {q}... | {row['faithfulness']:.2f} | {row['answer_relevancy']:.2f} | "
            f"{row['context_recall']:.2f} | {row['context_precision']:.2f} | {cause} |\n"
        )

    content += "\n---\n\n## Recommendations\n\n"
    content += "### Cải tiến 1\n"
    content += "**Action:** Tăng `top_k` retrieval trước rerank (hiện `top_k * 2` ở Task 9) nếu Context Recall thấp, "
    content += "để có nhiều candidate hơn trước khi lọc.\n"
    content += "**Expected impact:** Tăng Context Recall, giảm rủi ro bỏ sót đoạn liên quan nằm ngoài top-k ban đầu.\n\n"
    content += "### Cải tiến 2\n"
    content += "**Action:** Với câu hỏi ngoài phạm vi dữ liệu (vd câu hỏi lạc đề trong golden dataset), "
    content += "kiểm tra lại `SCORE_THRESHOLD` (đang 0.3) đã calibrate đúng theo corpus thực tế chưa.\n"
    content += "**Expected impact:** Giảm Faithfulness thấp do LLM cố trả lời dù context không liên quan.\n\n"
    content += "### Cải tiến 3\n"
    content += "**Action:** Thử `rerank_cross_encoder` (Jina Reranker, cần `JINA_API_KEY`) thay cho RRF-only "
    content += "để so sánh thêm 1 config C.\n"
    content += "**Expected impact:** Cross-encoder rerank thường cải thiện Context Precision so với RRF thuần rank-based.\n"

    RESULTS_PATH.write_text(content, encoding="utf-8")
    print(f"\n✓ Results exported to {RESULTS_PATH}")


if __name__ == "__main__":
    golden_dataset = load_golden_dataset()
    print(f"Loaded {len(golden_dataset)} test cases")

    comparison = compare_configs(golden_dataset)
    export_results(comparison)
