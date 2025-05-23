# Log Monitoring Application

import csv # For more robust CSV line parsing, though simple split works for the given format
from datetime import datetime, timedelta # Not strictly used in this version after switching to seconds, but good for time manipulation

# --- Helper Functions ---

def parse_timestamp_to_seconds(timestamp_str):
    """Converts a HH:MM:SS timestamp string to total seconds from midnight."""
    try:
        parts = list(map(int, timestamp_str.split(':')))
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        else:
            # Handle cases where timestamp might be malformed but still parsable by datetime
            # For simplicity here, we stick to strict HH:MM:SS
            raise ValueError("Timestamp not in HH:MM:SS format")
    except ValueError as e:
        # print(f"Debug: Error parsing timestamp '{timestamp_str}': {e}") # Optional debug
        raise ValueError(f"Invalid timestamp format: '{timestamp_str}'. Expected HH:MM:SS.") from e

def format_duration_from_seconds(total_seconds):
    """Formats total seconds into a readable string 'X minutes, Y seconds'."""
    if total_seconds < 0:
        return "Invalid (negative) duration"
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes} minutes, {seconds} seconds"

# --- Constants ---
LOG_FILE_PATH = "./log/logs.log" # Make sure the logs.log file is in the same directory or specify the correct path
WARNING_THRESHOLD_SECONDS = 5 * 60  # 5 minutes
ERROR_THRESHOLD_SECONDS = 10 * 60   # 10 minutes

# --- Main Program Logic ---
def main():
    report_list = []
    active_jobs = {}  # key: PID, value: {start_time_seconds, description, start_timestamp_string, start_line_number}
    lines_processed_count = 0
    current_line_number = 0

    print(f"Starting log monitoring for file: {LOG_FILE_PATH}\n")

    try:
        with open(LOG_FILE_PATH, 'r') as log_file:
            for line in log_file:
                current_line_number += 1
                line = line.strip() # Remove leading/trailing whitespace

                if not line: # Skip empty lines
                    continue

                lines_processed_count += 1

                # 1. Parse the CSV log file line
                try:
                    parts = line.split(',')
                    if len(parts) != 4:
                        raise ValueError(f"Line does not contain exactly 4 comma-separated values. Content: '{line}'")

                    timestamp_str = parts[0].strip()
                    job_description = parts[1].strip()
                    status_str = parts[2].strip()
                    pid_str = parts[3].strip()

                    pid = int(pid_str)
                    current_timestamp_seconds = parse_timestamp_to_seconds(timestamp_str)
                    status = status_str.upper() # Normalize status to uppercase

                except ValueError as e: # Includes errors from int(), parse_timestamp_to_seconds(), or non-compliant split
                    report_list.append(f"ANOMALY: Line {current_line_number}: Malformed log entry. Error: {e}. Line content: '{line}'")
                    continue # Skip this malformed line

                # 2. Identify each job or task and track its start and finish times.
                if status == "START":
                    if pid in active_jobs:
                        previous_job_info = active_jobs[pid]
                        report_list.append(
                            f"ANOMALY: Line {current_line_number}: Job '{job_description}' (PID: {pid}) "
                            f"received a new START at {timestamp_str} but was already running since "
                            f"{previous_job_info['start_timestamp_string']} (Line: {previous_job_info['start_line_number']}). "
                            f"Overwriting previous start."
                        )
                    active_jobs[pid] = {
                        "start_time_seconds": current_timestamp_seconds,
                        "description": job_description,
                        "start_timestamp_string": timestamp_str,
                        "start_line_number": current_line_number
                    }
                elif status == "END":
                    if pid in active_jobs:
                        job_info = active_jobs[pid]
                        start_time_seconds = job_info["start_time_seconds"]
                        original_job_description = job_info["description"]
                        start_timestamp_str = job_info["start_timestamp_string"]
                        start_line = job_info["start_line_number"]

                        # 3. Calculate the duration of each job
                        duration_seconds = current_timestamp_seconds - start_time_seconds

                        if duration_seconds < 0:
                            report_list.append(
                                f"ANOMALY: Line {current_line_number}: Job '{original_job_description}' (PID: {pid}) "
                                f"END event at {timestamp_str} is before its START event at {start_timestamp_str} (Line: {start_line}). "
                                f"Log data may be inconsistent."
                            )
                        else:
                            formatted_duration = format_duration_from_seconds(duration_seconds)
                            
                            # Info message (optional, can be commented out if too verbose)
                            # report_list.append(
                            #     f"INFO: Line {current_line_number}: Job '{original_job_description}' (PID: {pid}) completed. "
                            #     f"Duration: {formatted_duration}. Started: {start_timestamp_str} (Line: {start_line}), Ended: {timestamp_str}"
                            # )

                            # 4. Produce a report or output that:
                            if duration_seconds > ERROR_THRESHOLD_SECONDS:
                                report_list.append(
                                    f"ERROR: Job '{original_job_description}' (PID: {pid}) "
                                    f"exceeded {ERROR_THRESHOLD_SECONDS // 60} minutes. Actual duration: {formatted_duration}. "
                                    f"Started: {start_timestamp_str} (Line: {start_line}), Ended: {timestamp_str} (Line: {current_line_number})"
                                )
                            elif duration_seconds > WARNING_THRESHOLD_SECONDS:
                                report_list.append(
                                    f"WARNING: Job '{original_job_description}' (PID: {pid}) "
                                    f"exceeded {WARNING_THRESHOLD_SECONDS // 60} minutes. Actual duration: {formatted_duration}. "
                                    f"Started: {start_timestamp_str} (Line: {start_line}), Ended: {timestamp_str} (Line: {current_line_number})"
                                )
                        
                        del active_jobs[pid] # Remove PID from active_jobs
                    else:
                        report_list.append(
                            f"ANOMALY: Line {current_line_number}: Job '{job_description}' (PID: {pid}) "
                            f"has an END event at {timestamp_str} but no corresponding START event was found or it was already processed."
                        )
                else:
                    report_list.append(
                        f"ANOMALY: Line {current_line_number}: Invalid status '{status_str}' "
                        f"for job '{job_description}' (PID: {pid}) at {timestamp_str}."
                    )

    except FileNotFoundError:
        report_list.append(f"CRITICAL ERROR: The log file '{LOG_FILE_PATH}' was not found.")
    except Exception as e: # Generic error handler for unexpected issues during file processing
        report_list.append(f"CRITICAL ERROR: An unexpected error occurred: {e}")


    # After processing all lines, check for jobs in active_jobs (started but not ended)
    if lines_processed_count == 0 and not any("CRITICAL ERROR" in msg for msg in report_list): # Don't add this if file not found
        report_list.append("ANOMALY: The log file is empty or contains no processable log entries.")
    
    if active_jobs: # Only iterate if there are remaining jobs
        report_list.append("\n--- Unfinished Jobs (Started but no END event) ---")
        for pid, job_info in active_jobs.items():
            report_list.append(
                f"WARNING: Job '{job_info['description']}' (PID: {pid}) "
                f"started at {job_info['start_timestamp_string']} (Line: {job_info['start_line_number']}) "
                f"but did not have an END event in the log."
            )

    # Output the generated report
    print("\n--- Log Monitoring Report ---")
    if not report_list:
        if lines_processed_count > 0 :
             print("No significant events, warnings, or errors found requiring reporting.")
             print(f"All {lines_processed_count} processed log entries for jobs were within defined thresholds.")
        # If lines_processed_count is 0 and report_list is empty, it means the file was empty and handled above
    else:
        for message in report_list:
            print(message)
    print("--- End of Report ---")

if __name__ == "__main__":
    main()