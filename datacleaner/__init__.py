"""DataCleaner: deterministic customer spreadsheet cleaning."""

from .engine import InputError, ProcessResult, process_file

__all__ = ["InputError", "ProcessResult", "process_file"]
