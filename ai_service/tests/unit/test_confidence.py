from app.core.constants import ConfidenceLevel
from app.retrieval.confidence import assess, normalize
from app.vectorstore.base import ScoredChunk


def chunk(score: float, doc: str = "d1") -> ScoredChunk:
    return ScoredChunk(id=f"c-{doc}-{score}", text="text", document_id=doc, score=score)


def test_no_chunks_is_low_confidence():
    report = assess([])
    assert report.level is ConfidenceLevel.LOW
    assert not report.should_answer


def test_strong_agreeing_sources_score_high():
    report = assess([chunk(0.95, "a"), chunk(0.92, "b"), chunk(0.90, "c")])
    assert report.level is ConfidenceLevel.HIGH
    assert report.should_answer


def test_weak_single_match_scores_low():
    report = assess([chunk(0.15)])
    assert report.level is ConfidenceLevel.LOW


def test_cross_encoder_logits_are_normalised():
    assert 0.0 < normalize(-4.0) < 0.5
    assert 0.5 < normalize(4.0) < 1.0
    assert normalize(0.7) == 0.7


def test_agreement_across_documents_raises_score():
    single = assess([chunk(0.8, "a"), chunk(0.8, "a")])
    spread = assess([chunk(0.8, "a"), chunk(0.8, "b")])
    assert spread.score > single.score
