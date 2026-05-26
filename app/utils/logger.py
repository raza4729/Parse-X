# logger.py
import logging, sys, os

def get_logger(name: str,
               level: int | None = None,
               handler_level: int | None = None) -> logging.Logger:
    """
    Create/reuse a logger with a console handler.
    - level: logger threshold (default DEBUG)
    - handler_level: console handler threshold (default INFO; env DEBUG=1 bumps to DEBUG)
    """
    logger = logging.getLogger(name)
    if level is None:
        level = logging.DEBUG
    logger.setLevel(level)

    if not logger.handlers:
        if handler_level is None:
            handler_level = logging.DEBUG if os.getenv("DEBUG") == "1" else logging.INFO

        console = logging.StreamHandler(sys.stdout)
        console.setLevel(handler_level)
        console.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)s - %(name)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(console)
        logger.propagate = False  # avoid duplicate logs via root

    return logger
