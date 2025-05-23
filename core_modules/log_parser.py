# log_parser.py
"""
Handles parsing of individual log lines.
"""
from .utils import parse_timestamp_to_seconds

class LogParsingError(Exception):
    """Custom exception for errors during log line parsing."""
    pass

def parse_log_line(line_content, line_number):
    """
    Parses a single log line string into a structured dictionary.

    Args:
        line_content (str): The raw string content of the log line.
        line_number (int): The line number in the log file.

    Returns:
        dict: A dictionary containing parsed data:
              {
                  "timestamp_seconds": int,
                  "description": str,
                  "status": str (uppercase),
                  "pid": int,
                  "original_timestamp_str": str,
                  "line_number": int
              }

    Raises:
        LogParsingError: If the line cannot be parsed according to the expected format.
    """
    original_line = line_content # For error messages
    try:
        parts = line_content.split(',')
        if len(parts) != 4:
            raise LogParsingError(
                f"Line {line_number}: Malformed log entry. Expected 4 comma-separated values. "
                f"Content: '{original_line}'"
            )

        timestamp_str = parts[0].strip()
        job_description = parts[1].strip()
        status_str = parts[2].strip()
        pid_str = parts[3].strip()

        if not all([timestamp_str, job_description, status_str, pid_str]):
             raise LogParsingError(
                f"Line {line_number}: Malformed log entry. One or more fields are empty. "
                f"Content: '{original_line}'"
            )

        pid = int(pid_str) # Can raise ValueError
        timestamp_seconds = parse_timestamp_to_seconds(timestamp_str) # Can raise ValueError
        status = status_str.upper()

        return {
            "timestamp_seconds": timestamp_seconds,
            "description": job_description,
            "status": status,
            "pid": pid,
            "original_timestamp_str": timestamp_str, # Keep original for messages
            "line_number": line_number
        }
    except ValueError as e: # Catches errors from int() or parse_timestamp_to_seconds()
        raise LogParsingError(
            f"Line {line_number}: Error converting data. {e}. "
            f"Content: '{original_line}'"
        ) from e
    except LogParsingError: # Re-raise LogParsingErrors directly
        raise
    except Exception as e: # Catch any other unexpected error during parsing
        raise LogParsingError(
            f"Line {line_number}: Unexpected error parsing line. {e}. "
            f"Content: '{original_line}'"
        ) from e