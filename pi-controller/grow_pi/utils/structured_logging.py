#!/usr/bin/env python3
"""
Structured Logging Helper

Provides utilities for structured logging with context and operation timing.

Version: 6.22.5
"""

import logging
import time
from functools import wraps
from typing import Dict, Any, Callable


class StructuredLogAdapter(logging.LoggerAdapter):
    """
    Adapter for structured logging with context.

    Automatically adds context fields to all log messages.
    """

    def process(self, msg, kwargs):
        """
        Process log message with extra context.

        Args:
            msg: Log message
            kwargs: Keyword arguments for logging

        Returns:
            Tuple of (processed_message, processed_kwargs)
        """
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra

        # Add context to message if available
        if self.extra:
            context_str = ", ".join(f"{k}={v}" for k, v in self.extra.items())
            msg = f"[{context_str}] {msg}"

        return msg, kwargs


def get_structured_logger(name: str, **context) -> StructuredLogAdapter:
    """
    Get a logger with structured context.

    Args:
        name: Logger name (typically __name__)
        **context: Additional context fields to add to all log messages

    Returns:
        StructuredLogAdapter instance with context

    Example:
        logger = get_structured_logger(__name__, component="sensor", device="DHT22")
        logger.info("Reading sensor")  # Outputs: [component=sensor, device=DHT22] Reading sensor
    """
    logger = logging.getLogger(name)
    return StructuredLogAdapter(logger, context)


def log_operation(operation_name: str):
    """
    Decorator to log function entry/exit with timing.

    Args:
        operation_name: Name of the operation for logging

    Example:
        @log_operation("read_sensor")
        def read_dht22():
            # ... sensor reading logic
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            start = time.time()

            logger.debug(f"START {operation_name}")

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                logger.debug(f"END {operation_name} (duration={duration:.3f}s)")
                return result

            except Exception as e:
                duration = time.time() - start
                logger.error(
                    f"FAIL {operation_name} (duration={duration:.3f}s, error={type(e).__name__}: {e})"
                )
                raise

        return wrapper
    return decorator


def log_slow_operation(operation_name: str, threshold_seconds: float = 1.0):
    """
    Decorator to log slow operations (only if they exceed threshold).

    Args:
        operation_name: Name of the operation for logging
        threshold_seconds: Log warning if operation takes longer than this

    Example:
        @log_slow_operation("database_query", threshold_seconds=0.5)
        def query_data():
            # ... database query
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            start = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start

                if duration > threshold_seconds:
                    logger.warning(
                        f"SLOW {operation_name} (duration={duration:.3f}s, "
                        f"threshold={threshold_seconds}s)"
                    )

                return result

            except Exception as e:
                duration = time.time() - start
                logger.error(
                    f"FAIL {operation_name} (duration={duration:.3f}s, error={type(e).__name__}: {e})"
                )
                raise

        return wrapper
    return decorator


class LogContext:
    """
    Context manager for structured logging within a code block.

    Example:
        with LogContext("database_transaction", transaction_id=123):
            # All logs within this block will include transaction_id
            logger.info("Starting transaction")
            # ...
    """

    def __init__(self, operation_name: str, **context):
        """
        Initialize log context.

        Args:
            operation_name: Name of the operation
            **context: Additional context fields
        """
        self.operation_name = operation_name
        self.context = context
        self.logger = logging.getLogger(__name__)
        self.start_time = None

    def __enter__(self):
        """Enter context - log start."""
        self.start_time = time.time()
        context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
        self.logger.debug(f"START {self.operation_name} [{context_str}]")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - log end with duration."""
        duration = time.time() - self.start_time
        context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())

        if exc_type is None:
            self.logger.debug(
                f"END {self.operation_name} [{context_str}] (duration={duration:.3f}s)"
            )
        else:
            self.logger.error(
                f"FAIL {self.operation_name} [{context_str}] "
                f"(duration={duration:.3f}s, error={exc_type.__name__}: {exc_val})"
            )

        return False  # Don't suppress exceptions


def format_log_dict(data: Dict[str, Any]) -> str:
    """
    Format a dictionary for logging.

    Args:
        data: Dictionary to format

    Returns:
        Formatted string representation

    Example:
        logger.info(f"Config loaded: {format_log_dict(config)}")
    """
    items = [f"{k}={v}" for k, v in data.items()]
    return "{" + ", ".join(items) + "}"
