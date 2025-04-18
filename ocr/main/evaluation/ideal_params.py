#!/usr/bin/env python
import argparse
import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from glob import glob

# --- Django setup -----------------------------------------------------------
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babaatsite.settings")
django.setup()
# ----------------------------------------------------------------------------

from ocr.main.inference.detections import (  # noqa: E501, E402
    analyze_document,
    config_ocr,
)

# from ocr.main.utils.configs import load_config  # noqa: E402
from ocr.main.utils.loggers import setup_logging  # noqa: E402
from ocr.models import Document, Truth  # noqa: E402


def run_experiment(config_path: str, device_id: int = None):
    """
    Run one config over all relevant documents, compute:
      - per‐document recall
      - overall average recall
    Returns (cfg_name, avg_recall, per_doc_recalls_dict)
    """
    cfg_name = os.path.basename(config_path)
    logging.info(f"[{cfg_name}] ▶️ Starting experiment")

    # Bind to a specific GPU if requested
    if device_id is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(device_id)

    cfg_name = os.path.basename(config_path)
    # config = load_config(config_path)
    ocr = config_ocr(config=config_path)

    logging.info(f"[{cfg_name}] ⚙️ OCR configured, now running detections")

    # 1) find all document_numbers that have at least one Truth
    doc_nums = Truth.objects.values_list(
        "document_number", flat=True
    ).distinct()

    logging.info(f"[{cfg_name}] Found {len(doc_nums)} documents")

    # 2) fetch only those Documents
    docs = Document.objects.filter(document_number__in=doc_nums)

    per_doc_recalls = []
    per_doc_scores = {}

    logging.info(f"[{cfg_name}] Running OCR on {len(docs)} documents")
    for doc in docs:
        # a) run OCR on all pages of this doc
        dets = analyze_document(doc, ocr, experiment=cfg_name)
        detected_texts = {d.text for d in dets}

        # b) get all truths for this doc
        truths = list(
            Truth.objects.filter(
                document_number=doc.document_number
            ).values_list("text", flat=True)
        )
        if not truths:
            # no ground truth; skip
            continue

        # c) compute recall for this doc
        found = sum(1 for t in truths if t in detected_texts)
        recall = found / len(truths)
        per_doc_recalls.append(recall)
        per_doc_scores[doc.document_number] = recall

    # 3) overall average recall
    avg_recall = (
        sum(per_doc_recalls) / len(per_doc_recalls) if per_doc_recalls else 0.0
    )

    logging.info(
        f"[{cfg_name}] ✅ Finished detections, avg recall={avg_recall:.3f}"
    )

    return cfg_name, avg_recall, per_doc_scores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-dir",
        type=str,
        default="ocr/main/configs/detections",
        help="Directory containing your JSON experiment configs",
    )
    parser.add_argument(
        "--gpus",
        type=int,
        default=1,
        help="Number of GPUs / parallel workers",
    )
    args = parser.parse_args()

    setup_logging("ideal_params")
    logging.info("Starting ideal_params.py…")

    configs = glob(os.path.join(args.config_dir, "*.json"))
    device_ids = list(range(args.gpus))

    # collect results: { config_name: (avg_recall, {doc_num:recall, …}) }
    all_results = {}

    with ProcessPoolExecutor(max_workers=args.gpus) as executor:
        futures = {
            executor.submit(
                run_experiment, cfg, device_ids[i % len(device_ids)]
            ): cfg
            for i, cfg in enumerate(configs)
        }

        for fut in as_completed(futures):
            cfg_name, avg_recall, per_doc_scores = fut.result()
            all_results[cfg_name] = (avg_recall, per_doc_scores)
            logging.info(f"[{cfg_name:30s}] avg_recall = {avg_recall:.3f}")

    # 4) Print summary of average recall
    print("\n=== Experiment Averages (best → worst) ===")
    for cfg, (avg, _) in sorted(all_results.items(), key=lambda kv: -kv[1][0]):
        print(f"{cfg:40s}  {avg:.3f}")

    # 5) Optionally, dump per‐document recalls for your inspection
    print("\n=== Per‐Document Recalls (by config) ===")
    for cfg, (_, per_doc) in all_results.items():
        print(f"\n-- {cfg} --")
        for doc_num, recall in per_doc.items():
            print(f"  {doc_num:10s}  {recall:.3f}")


if __name__ == "__main__":
    main()
