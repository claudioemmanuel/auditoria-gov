import logging

import structlog

from shared.config import settings

_NAME_TO_LEVEL = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def setup_logging() -> None:
    level = _NAME_TO_LEVEL.get(settings.LOG_LEVEL.lower(), logging.INFO)
    use_console = settings.LOG_FORMAT == "console"

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    logging.basicConfig(
        format="%(message)s",
        level=level,
        force=True,
    )

    processor_formatter = structlog.stdlib.ProcessorFormatter(
        processor=(
            structlog.dev.ConsoleRenderer()
            if use_console
            else structlog.processors.JSONRenderer()
        ),
        foreign_pre_chain=shared_processors,
    )

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.setFormatter(processor_formatter)

    # Route stdlib loggers into structlog so Celery/SQLAlchemy logs are consistent.
    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


log = structlog.get_logger()
