"""Shared generation constraints for answers and Knowledge Structure content."""

ACCURACY_CONTRACT_VERSION = 3

ACCURACY_CONTRACT = """
FACTUAL PRECISION CHECK (applies to prose, profiles, introductions and map leaves):
- Distinguish a definition from one special case. State material assumptions;
  do not turn a sufficient condition into a necessary condition or an example into a universal claim.
- Expand an acronym or initialism at its first meaningful use when its full form is known and unambiguous.
  If it is ambiguous, ask or state the interpretation instead of guessing.
- Use concrete, grammatical subject names. Prerequisites are prior knowledge,
  not a restatement of the question or a downstream activity. Keep them minimal and aligned with the requested depth;
  state when no specialized prior knowledge is required.
- Avoid unsupported frequency, ranking and superlative claims such as "usually the largest" or "always best."
  Qualify them or explain the evidence and conditions on which they depend.
- Do not label an association, predictive feature or observational pattern as causal unless the design and evidence
  support causal identification. Name the weaker relationship when that is all the evidence establishes.
- For a named process, framework or standard, separate its documented core components from later adaptations,
  adjacent practices and implementation recommendations. Do not rename a related method as an official variant.
- Knowledge-map titles must be complete, parallel noun phrases. Never truncate them into fragments such as
  "Industrial vs. customer" when the compared object is analytics, data, strategy or another explicit noun.
- Activation functions introduce nonlinearity, not the existence of gradients.
  ReLU and ordinary leaky ReLU are piecewise linear and not differentiable at zero.
  GELU is smooth but does not generally produce ReLU-like exact sparsity.
  Exactly, GELU(x) = x times the standard normal CDF at x, not a blend of x and that product.
  ReLU has left derivative 0 and right derivative 1 at zero, so its ordinary derivative there does not exist.
  Affine-only networks can separate linearly separable classes, but cannot model nonlinear boundaries.
  Softmax acts on a vector, unlike scalar elementwise activations.
- Entanglement is nonseparability; Bell violation is not necessary for general mixed-state entanglement.
  Classical correlation is not the same as independence. Schmidt bases need not be unique
  for degenerate coefficients. Cryptographic security requires protocol and trust assumptions.
- Operating-system threading tradeoffs depend on workload and implementation;
  I/O-bound work is not inherently a reason to avoid threads. Use standard debugging terminology.
- Retrieval supplies external information within the model's context budget;
  it does not increase the model's fixed context-window capacity.
- Before returning, check each example against its claimed property and qualify
  any statement whose truth depends on a state, workload, protocol or model variant.
"""


def normalize_response_accuracy(text: str, subject: str = "") -> str:
    """Apply small, idempotent corrections for verified recurring factual defects."""
    import re

    value = str(text or "")
    evidence = f"{subject} {value}".casefold()
    if "crisp-dm" in evidence or "crisp dm" in evidence:
        full = "Cross-Industry Standard Process for Data Mining"
        if full.casefold() not in value.casefold():
            value = re.sub(
                r"\bCRISP[\s-]?DM\b",
                f"{full} (CRISP-DM)",
                value,
                count=1,
                flags=re.IGNORECASE,
            )
        value = re.sub(
            r"Analytics Solutions Unified Method\s*\(\s*ASUM-DM\s*\)",
            "Analytics Solutions Unified Method (ASUM)",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"\bASUM-DM\b",
            "Analytics Solutions Unified Method (ASUM)",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"extensions or variants of CRISP-DM\s*\(\s*e\.g\.,?\s*Analytics Solutions Unified Method \(ASUM\)\s*\)",
            "related methods or modern extensions around CRISP-DM, such as Analytics Solutions Unified Method (ASUM)",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"What are common criticisms and proposed extensions\s*\(\s*e\.g\.,?\s*Analytics Solutions Unified Method \(ASUM\)\s*\)\?",
            "What are common criticisms of CRISP-DM, what extensions have been proposed, and how does Analytics Solutions Unified Method (ASUM) relate?",
            value,
            flags=re.IGNORECASE,
        )

    replacements = (
        (r"\bis usually (?:the )?largest time sink\b", "can be one of the more time-consuming stages"),
        (r"\busually (?:the )?largest time sink\b", "can be one of the more time-consuming stages"),
        (r"\bcausal or predictive signals\b", "predictive or associative patterns"),
        (r"\bpredictive or causal signals\b", "predictive or associative patterns"),
    )
    for pattern, replacement in replacements:
        value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
    value = re.sub(r"\bis can be\b", "can be", value, flags=re.IGNORECASE)
    return value


__all__ = [
    "ACCURACY_CONTRACT",
    "ACCURACY_CONTRACT_VERSION",
    "normalize_response_accuracy",
]
