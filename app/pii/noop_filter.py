class NoopFilter:
    """Pass-through PII filter for MVP."""

    def filter(self, text: str) -> str:
        return text

    def restore(self, text: str) -> str:
        return text
