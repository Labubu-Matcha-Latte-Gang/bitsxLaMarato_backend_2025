from __future__ import annotations
from abc import ABC, abstractmethod
import datetime
import json
import traceback
from typing import Any
from helpers.enums.log_type import LogType

class AbstractLogger(ABC):
    __instance: 'AbstractLogger' | None = None

    @abstractmethod
    def log(self, message: str, level: LogType = LogType.INFO, module: str | None = None, metadata: dict[str, Any] | None = None, error: Exception | None = None):
        """
        Logs a message with the given level, module, metadata, and optional error.
        Args:
            message (str): The log message.
            level (LogType, optional): The log level. Defaults to LogType.INFO.
            module (str | None, optional): The module where the log is generated. Defaults to None.
            metadata (dict[str, Any] | None, optional): Additional metadata for the log. Defaults to None.
            error (Exception | None, optional): An optional exception to log. Defaults to None.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def info(self, message: str, module: str | None = None, metadata: dict[str, Any] | None = None):
        """
        Logs an informational message.
        Args:
            message (str): The log message.
            module (str | None, optional): The module where the log is generated. Defaults to None.
            metadata (dict[str, Any] | None, optional): Additional metadata for the log. Defaults to None.
        """
        return self.log(message, LogType.INFO, module, metadata)
    
    def warning(self, message: str, module: str | None = None, metadata: dict[str, Any] | None = None):
        """
        Logs a warning message.
        Args:
            message (str): The log message.
            module (str | None, optional): The module where the log is generated. Defaults to None.
            metadata (dict[str, Any] | None, optional): Additional metadata for the log. Defaults to None.
        """
        return self.log(message, LogType.WARNING, module, metadata)
    
    def error(self, message: str, module: str | None = None, metadata: dict[str, Any] | None = None, error: Exception | None = None):
        """
        Logs an error message.
        Args:
            message (str): The log message.
            module (str | None, optional): The module where the log is generated. Defaults to None.
            metadata (dict[str, Any] | None, optional): Additional metadata for the log. Defaults to None.
            error (Exception | None, optional): An optional exception to log. Defaults to None.
        """
        return self.log(message, LogType.ERROR, module, metadata, error)
    
    def debug(self, message: str, module: str | None = None, metadata: dict[str, Any] | None = None):
        """
        Logs a debug message.
        Args:
            message (str): The log message.
            module (str | None, optional): The module where the log is generated. Defaults to None.
            metadata (dict[str, Any] | None, optional): Additional metadata for the log. Defaults to None.
        """
        return self.log(message, LogType.DEBUG, module, metadata)
    
    def __call__(self, message: str, level: LogType = LogType.INFO, module: str | None = None, metadata: dict[str, Any] | None = None, error: Exception | None = None):
        """
        Allows the logger instance to be called like a function to log messages.
        Args:
            message (str): The log message.
            level (LogType, optional): The log level. Defaults to LogType.INFO.
            module (str | None, optional): The module where the log is generated. Defaults to None.
            metadata (dict[str, Any] | None, optional): Additional metadata for the log. Defaults to None.
            error (Exception | None, optional): An optional exception to log. Defaults to None.
        """
        return self.log(message, level, module, metadata, error)
    
    @classmethod
    def get_instance(cls) -> 'AbstractLogger':
        """
        Returns the singleton instance of the logger.
        Returns:
            AbstractLogger: The singleton logger instance.
        """
        if cls.__instance is None:
            cls.__instance = Logger()
        return cls.__instance

class Logger(AbstractLogger):
    def log(self, message: str, level: LogType = LogType.INFO, module: str | None = None, metadata: dict[str, Any] | None = None, error: Exception | None = None):
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        module_part = f"{module} | " if module else ""
        log_entry = f"[{timestamp}] [{level.name}] {module_part}{message}"

        if metadata:
            try:
                metadata_str = json.dumps(metadata, default=str, ensure_ascii=False)
            except Exception:
                metadata_str = str(metadata)
                
            log_entry += f" | Metadata: {metadata_str}"

        if level == LogType.ERROR and error is not None:
            tb_obj = error.__traceback__
            tb_formatted = traceback.format_exception(
                type(error), error, tb_obj
            )
            tb_string = "".join(tb_formatted)
            log_entry += f"\nTraceback for exception ({str(error)}):\n{tb_string}"

        print(log_entry, flush=True)