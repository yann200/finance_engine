"""finance-engine: portfolio analysis and strategy backtesting toolkit."""

import logging

__version__ = "0.1.0"

# Library best practice: never configure logging on import. The NullHandler
# avoids "no handler found" warnings when the application has not called
# setup_logging(); the application (CLI) decides where logs actually go.
logging.getLogger(__name__).addHandler(logging.NullHandler())