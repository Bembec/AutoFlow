from autoflow.classification.ai_classifier import classify_with_ai
from autoflow.pipeline import classify_with_rules


def test_rules_classification():
    assert classify_with_rules("i want to know your price") == "Sales"
    assert classify_with_rules("i need help with my account") == "Support"
    assert classify_with_rules("thank you for your service") == "Other"


def test_ai_disabled_returns_none():
    assert classify_with_ai("I want to know your price") is None
