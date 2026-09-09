"""Shared generation constraints for answers and Knowledge Structure content."""

ACCURACY_CONTRACT = """
FACTUAL PRECISION CHECK (applies to prose, profiles, introductions and map leaves):
- Distinguish a definition from one special case. State material assumptions;
  do not turn a sufficient condition into a necessary condition or an example into a universal claim.
- Use concrete, grammatical subject names. Prerequisites are prior knowledge,
  not a restatement of the question; distinguish conceptual from implementation requirements.
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
