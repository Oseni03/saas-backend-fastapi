import logging
import sys

import structlog

from app.config import settings


def configure_logging() -> None:
    """Configure structlog + standard logging."""
    
    # Processors used by structlog.get_logger() (for manual logging)
    structlog_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_production:
        structlog_processors.extend([
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ])
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),   # Only renderer here
        )
    else:
        structlog_processors.append(
            structlog.dev.ConsoleRenderer(colors=True)
        )
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True),
        )

    # Set up standard library logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Remove any existing handlers to prevent duplication
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Configure structlog
    structlog.configure(
        processors=[
            *structlog_processors[:-1],           # All processors except the final renderer
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()