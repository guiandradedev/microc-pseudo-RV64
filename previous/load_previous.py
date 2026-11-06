"""Compatibilidade para executar módulos anteriores com o frontend plano."""
from pathlib import Path
import sys


PROJECT_DIR = str(Path(__file__).resolve().parent)
PREVIOUS_DIR = str(Path(PROJECT_DIR) / "previous")
sys.path[:] = [PROJECT_DIR, PREVIOUS_DIR] + [
    directory for directory in sys.path
    if directory not in {PROJECT_DIR, PREVIOUS_DIR}
]
