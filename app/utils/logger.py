import logging
from logging.handlers import RotatingFileHandler
from app.config import LOGS_DIR

_FMT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

def get_logger(name: str = "oie") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    fh = RotatingFileHandler(
        LOGS_DIR / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(logging.Formatter(_FMT))
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter(_FMT))
    logger.addHandler(sh)
    return logger
