"""Automated evaluation of the assistant against a labelled question set.

    dataset.json          the questions and their labels
    retrieval_metrics.py  precision, recall, MRR, NDCG
    answer_metrics.py     refusal, clarification, links, citations, faithfulness
    evaluator.py          the runner, offline by default

Run it with ``python -m evaluation.evaluator``.
"""
