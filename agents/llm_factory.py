"""Deterministic placeholder for the optional legacy agent demonstration."""
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name="Mitotic Count Density Standardizer"):
        self.system_name = system_name

    def invoke(self, prompt):
        PHIGuard.assert_no_phi(prompt)
        return ("Demonstration only: no language model, clinical validation, "
                "or clinical assessment is performed. Use the calibrated "
                "mitoses/mm² conversion for numerical measurement.")


class LLMFactory:
    @staticmethod
    def create(provider="mock", system_name="Mitotic Count Density Standardizer"):
        # No remote provider has been integrated. Never imply that one is in use.
        return MockLLM(system_name)
