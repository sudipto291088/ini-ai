from api.capability_boundary import assess_capability


def test_tax_instruction_is_refused() -> None:
    decision = assess_capability("Instruct me about the tax structure in India")

    assert decision is not None
    assert decision.domain == "tax"
    assert "haven’t yet been equipped with verified tax knowledge" in decision.reply
    assert "generate a Question Map" in decision.reply


def test_tax_acronyms_are_refused() -> None:
    assert assess_capability("Explain GST in India") is not None
    assert assess_capability("How does VAT work?") is not None
    assert assess_capability("What is TDS?") is not None


def test_supported_learning_topic_is_not_blocked() -> None:
    assert assess_capability("Generate a Question Map for gradient descent") is None
    assert assess_capability("Explain Kubernetes deployments") is None


def test_tax_in_an_economics_learning_question_is_not_refused() -> None:
    query = (
        "What are supply and demand, how is market equilibrium formed, "
        "and how do taxes and price controls change it?"
    )

    assert assess_capability(query) is None


def test_carbon_tax_and_cap_and_trade_is_environmental_economics() -> None:
    query = (
        "How do carbon taxes and cap-and-trade systems differ, and what determines "
        "whether either policy reduces emissions effectively?"
    )
    assert assess_capability(query) is None


def test_personal_and_jurisdiction_tax_guidance_remains_blocked() -> None:
    assert assess_capability("How should I file my tax return?") is not None
    assert assess_capability("Explain the income tax structure in India") is not None
