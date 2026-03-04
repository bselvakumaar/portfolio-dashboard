import hashlib
import logging

logger = logging.getLogger(__name__)


class SentimentEngine:
    """
    Pluggable sentiment engine.
    Current implementation is a deterministic stub to keep scoring pipeline stable.
    """

    def __init__(self, provider: str = "stub") -> None:
        self.provider = provider

    def get_sentiment_score(self, ticker: str) -> float:
        # Deterministic pseudo-score in [0, 10] until Vertex/OpenAI integration is enabled.
        digest = hashlib.sha256(ticker.encode("utf-8")).hexdigest()
        basis_points = int(digest[:4], 16) % 1001
        score = round(basis_points / 100.0, 2)
        logger.info(
            "Generated sentiment score",
            extra={"ticker": ticker, "provider": self.provider, "sentiment_score": score},
        )
        return score
