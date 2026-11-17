"""Asset model: a tradable financial instrument identified by its ticker."""

from dataclasses import dataclass

from finance_engine.exceptions import InvalidTickerError


@dataclass(frozen=True)
class Asset:
    """A financial asset (stock, ETF, ...).

    The instance is immutable (``frozen=True``), which makes it hashable and
    safe to use as a dictionary key or in a set.

    Attributes:
        ticker: Market symbol, normalised to upper case (e.g. ``"AAPL"``).
        name: Optional human-readable name.
        currency: Quotation currency, normalised to upper case.

    Raises:
        InvalidTickerError: If the ticker is not a non-empty string.
    """

    ticker: str
    name: str = ""
    currency: str = "USD"

    def __post_init__(self) -> None:
        """Validate and normalise the fields right after initialisation."""
        if not isinstance(self.ticker, str) or not self.ticker.strip():
            raise InvalidTickerError("Ticker must be a non-empty string")
        # A frozen dataclass forbids normal assignment, so we bypass it here.
        object.__setattr__(self, "ticker", self.ticker.strip().upper())
        object.__setattr__(self, "currency", self.currency.strip().upper())

    def __str__(self) -> str:
        return self.ticker