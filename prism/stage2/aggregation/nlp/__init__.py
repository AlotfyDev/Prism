"""NLP-enhanced aggregation package exports."""

from prism.stage2.aggregation.nlp.detector_correlation import DetectorCorrelation
from prism.stage2.aggregation.nlp.heading_sequence import HeadingSequenceAnalyzer

__all__ = [
    "DetectorCorrelation",
    "HeadingSequenceAnalyzer",
]
