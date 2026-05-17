"""
base.py — DocumentTypeResult dataclass and BaseDocumentTypeDetector interface.

Three-class density system
--------------------------
  density_class 0 — SPARSE : exam sheets, assignment pages, slides with few items
  density_class 1 — MEDIUM : lecture notes, mixed slides, annotated papers
  density_class 2 — DENSE  : research papers, textbooks, conference proceedings

Legacy doc_type ("dense"/"sparse") is kept as a derived property so existing
callers do not break:  class 0/1 → "sparse",  class 2 → "dense".
"""

DENSITY_LABELS    = {0: "SPARSE", 1: "MEDIUM", 2: "DENSE"}
_CLASS_TO_DOC_TYPE = {0: "sparse", 1: "sparse", 2: "dense"}


class DocumentTypeResult:
    """
    Attributes
    ----------
    density_class : int   0 / 1 / 2  ← primary output
    doc_type      : str   "sparse" or "dense"  (derived, backward-compat)
    confidence    : float 0–1
    signals       : dict  raw measurements
    detector_name : str
    """

    def __init__(self, density_class, confidence, signals, detector_name):
        if density_class not in (0, 1, 2):
            raise ValueError(f"density_class must be 0, 1, or 2, got {density_class!r}")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {confidence}")

        self.density_class = density_class
        self.confidence    = confidence
        self.signals       = signals
        self.detector_name = detector_name

    # ── Derived legacy properties ─────────────────────────────────────────

    @property
    def doc_type(self):
        return _CLASS_TO_DOC_TYPE[self.density_class]

    @property
    def is_dense(self):
        return self.density_class == 2

    @property
    def is_medium(self):
        return self.density_class == 1

    @property
    def is_sparse(self):
        return self.density_class == 0

    @property
    def density_label(self):
        return DENSITY_LABELS[self.density_class]

    def __repr__(self):
        return (
            f"DocumentTypeResult("
            f"density_class={self.density_class}({self.density_label}), "
            f"conf={self.confidence:.2f}, detector={self.detector_name!r})"
        )

    def summary(self):
        lines = [
            f"  Detector      : {self.detector_name}",
            f"  Density class : {self.density_class}  ({self.density_label})",
            f"  Legacy type   : {self.doc_type}",
            f"  Confidence    : {self.confidence:.2f}",
            "  Signals:",
        ]
        for k, v in self.signals.items():
            if isinstance(v, float):
                lines.append(f"    {k:<28} {v:.4f}")
            else:
                lines.append(f"    {k:<28} {v}")
        return "\n".join(lines)


class BaseDocumentTypeDetector:
    """
    Abstract base.  Subclasses implement detect() → DocumentTypeResult
    with density_class in {0, 1, 2}.
    """

    name = "base"

    def detect(self, blobs, font_size, img_width, img_height,
               gray=None, debug=False):
        raise NotImplementedError(f"{self.__class__.__name__} must implement detect()")

    def _clamp(self, value, lo=0.0, hi=1.0):
        return max(lo, min(hi, value))