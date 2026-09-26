class QuotexError(Exception):
    """Base exception for Quotex client errors."""
    pass


class QuotexConnectionError(QuotexError):
    """Raised when connection to Quotex fails."""
    pass


class QuotexAuthenticationError(QuotexError):
    """Raised when authentication fails."""
    pass


class QuotexTimeoutError(QuotexError):
    """Raised when a Quotex request times out."""
    pass


class QuotexDataError(QuotexError):
    """Raised when received market data is invalid."""
    pass
