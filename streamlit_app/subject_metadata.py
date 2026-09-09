"""Shared subject metadata for response profiles and map headings."""

import re


def subject_metadata(text: str) -> dict[str, str]:
    text = text.casefold()
    entries = (
        (r"\b(?:operating systems?|multitasking|cpu scheduling|process scheduling)\b", {
            "Subject": "Operating systems",
            "Entity type": "Operating-system mechanism",
            "Broad field": "Computer Science / Operating Systems",
            "Related topics": "Processes, threads, CPU scheduling, context switching, virtual memory, synchronization, and I/O",
            "Prerequisites": "CPU and memory basics; program execution; basic computer architecture; input/output",
        }),
        (r"\bactivation functions?\b", {
            "Subject": "Activation functions in neural networks",
            "Entity type": "Neural-network mathematical component",
            "Broad field": "Machine Learning / Deep Learning",
            "Related topics": "Nonlinearity, affine transformations, ReLU, sigmoid, tanh, GELU, backpropagation, and gradient flow",
            "Prerequisites": "Functions; vectors and matrices; weighted sums; derivatives for the mathematical explanation",
        }),
        (r"\b(?:quantum entanglement|entangled states?)\b", {
            "Subject": "Quantum entanglement",
            "Entity type": "Quantum phenomenon",
            "Broad field": "Physics / Quantum Information",
            "Related topics": "Separable states, density matrices, measurement, Bell inequalities, quantum steering, and decoherence",
            "Prerequisites": "Probability; vectors and complex numbers; quantum states; superposition; quantum measurement",
        }),
    )
    for pattern, fields in entries:
        if re.search(pattern, text):
            result = dict(fields)
            if result["Subject"] == "Operating systems" and re.search(
                r"multitask|multiple programs|scheduling|concurrent|same time", text
            ):
                result["Subject"] = "Operating-system multitasking"
            if result["Subject"] == "Quantum entanglement" and "correlation" in text:
                result["Subject"] = "Quantum entanglement and classical correlation"
            return result
    return {}
