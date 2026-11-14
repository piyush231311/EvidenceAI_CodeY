"""Benchmark script comparing PaddleOCR models on screenshot text."""

import os
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(PROJECT_ROOT / "models_cache" / "paddlex"))
os.environ.setdefault("PADDLE_HOME", str(PROJECT_ROOT / "models_cache" / "paddle"))
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

# Create realistic screenshot with small text, names, dates, timestamps
def create_test_screenshot(output_path: Path):
    img = Image.new("RGB", (700, 220), color=(245, 247, 250))
    d = ImageDraw.Draw(img)

    lines = [
        ("Evidence AI Incident Report - Case #2026-8941", (20, 20)),
        ("Victim: Jane Doe | Suspect: Alex Vance", (20, 60)),
        ("Timestamp: 2026-11-14 14:32:05 EST", (20, 100)),
        ("Threat: Do not contact the authorities or you will regret this.", (20, 140)),
        ("Digital Evidence Verified [SHA-256 Hash: e3b0c44298fc1c149afbf4c8996fb924]", (20, 180)),
    ]

    for text, pos in lines:
        d.text(pos, text, fill=(20, 25, 35))

    img.save(output_path)


def benchmark_model(det_name: str, rec_name: str, label: str, image_path: Path):
    from paddleocr import PaddleOCR

    print(f"\n==========================================")
    print(f"Testing {label}: {det_name} + {rec_name}")
    print(f"==========================================")

    # Measure initialization time
    t0 = time.perf_counter()
    ocr = PaddleOCR(
        text_detection_model_name=det_name,
        text_recognition_model_name=rec_name,
        enable_mkldnn=False,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    init_time = time.perf_counter() - t0
    print(f"  [Init Time]: {init_time:.2f}s")

    # Warmup / First inference
    t1 = time.perf_counter()
    res1 = ocr.predict(str(image_path))
    inf_time_1 = time.perf_counter() - t1
    print(f"  [First Inference]: {inf_time_1:.2f}s")

    # Second inference (pure runtime without any jit/cold start)
    t2 = time.perf_counter()
    res2 = ocr.predict(str(image_path))
    inf_time_2 = time.perf_counter() - t2
    print(f"  [Second Inference]: {inf_time_2:.2f}s")

    # Extract detected text & evaluate accuracy
    texts = []
    scores = []
    for r in res2:
        texts.extend(r.get("rec_texts", []))
        scores.extend(r.get("rec_scores", []))

    full_text = " ".join(texts)
    avg_score = sum(scores) / len(scores) if scores else 0.0

    # Key entity checks
    has_case = "2026-8941" in full_text
    has_victim = "Jane Doe" in full_text or "Jane" in full_text
    has_suspect = "Alex Vance" in full_text or "Alex" in full_text
    has_date = "2026-11-14" in full_text
    has_time = "14:32:05" in full_text
    has_threat = "authorities" in full_text.lower() or "regret" in full_text.lower()

    print(f"  [Avg Confidence]: {avg_score * 100:.1f}%")
    print(f"  [Lines Detected]: {len(texts)}")
    print(f"  [Key Entities Captured]:")
    print(f"    - Case ID: {'✓' if has_case else '✗'}")
    print(f"    - Names (Jane Doe / Alex Vance): {'✓' if (has_victim and has_suspect) else '✗'}")
    print(f"    - Date (2026-11-14): {'✓' if has_date else '✗'}")
    print(f"    - Time (14:32:05): {'✓' if has_time else '✗'}")
    print(f"    - Threat content: {'✓' if has_threat else '✗'}")
    print(f"  [Raw Text Preview]: {full_text[:120]}...")

    ocr.close()

    return {
        "label": label,
        "det": det_name,
        "rec": rec_name,
        "init_time": init_time,
        "inf_time": inf_time_2,
        "avg_confidence": avg_score,
        "all_entities": all([has_case, has_victim, has_suspect, has_date, has_time, has_threat]),
    }


def main():
    img_path = PROJECT_ROOT / "test_screenshot_bench.png"
    create_test_screenshot(img_path)

    configs = [
        ("PP-OCRv6_medium_det", "PP-OCRv6_medium_rec", "PP-OCRv6 Medium (Current)"),
        ("PP-OCRv6_small_det", "PP-OCRv6_small_rec", "PP-OCRv6 Small (Lightweight)"),
        ("PP-OCRv6_tiny_det", "PP-OCRv6_tiny_rec", "PP-OCRv6 Tiny (Ultra-fast)"),
    ]

    results = []
    try:
        for det, rec, label in configs:
            res = benchmark_model(det, rec, label, img_path)
            results.append(res)
    finally:
        if img_path.exists():
            img_path.unlink()

    print("\n\n==========================================")
    print("        BENCHMARK SUMMARY RESULTS         ")
    print("==========================================")
    print(f"{'Model Variant':<28} | {'Init (s)':<9} | {'Infer (s)':<10} | {'Confidence':<11} | {'Accuracy'}")
    print("-" * 75)
    for r in results:
        acc_str = "All Captured ✓" if r["all_entities"] else "Partial"
        print(f"{r['label']:<28} | {r['init_time']:<9.2f} | {r['inf_time']:<10.2f} | {r['avg_confidence']*100:<10.1f}% | {acc_str}")


if __name__ == "__main__":
    main()
