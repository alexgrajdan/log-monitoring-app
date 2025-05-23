# utils.py
"""
Utility functions for the log monitoring application.
"""

def parse_timestamp_to_seconds(timestamp_str):
    """
    Converts a HH:MM:SS timestamp string to total seconds from midnight.
    Raises ValueError if the format is incorrect.
    """
    try:
        parts = list(map(int, timestamp_str.split(':')))
        if len(parts) == 3:
            # Basic validation for time components
            if not (0 <= parts[0] <= 23 and 0 <= parts[1] <= 59 and 0 <= parts[2] <= 59):
                raise ValueError("Timestamp values out of range.")
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        else:
            raise ValueError("Timestamp not in HH:MM:SS format.")
    except ValueError as e:
        # Re-raise with a more specific message, or let the original ValueError propagate
        # For simplicity, we let the original propagate if it's informative enough,
        # or wrap it if we want to add more context.
        raise ValueError(f"Invalid timestamp format or value: '{timestamp_str}'. {e}") from e

def format_duration_from_seconds(total_seconds):
    """
    Formats total seconds into a readable string 'X minutes, Y seconds'.
    Returns a specific string for negative durations.
    """
    if total_seconds < 0:
        return "Invalid (negative) duration"
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes} minutes, {seconds} seconds"