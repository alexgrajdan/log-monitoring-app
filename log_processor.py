# log_processor.py
"""
Core logic for processing parsed log events, managing job states,
and generating report entries.
"""
from config import WARNING_THRESHOLD_SECONDS, ERROR_THRESHOLD_SECONDS
from utils import format_duration_from_seconds

class LogProcessor:
    """Processes log events and maintains the state of active jobs."""

    def __init__(self):
        self.active_jobs = {}  # Stores info about jobs that have started but not ended
        # Key: PID, Value: {start_time_seconds, description, start_timestamp_string, start_line_number}
        self.report_entries = [] # Accumulates messages for the final report

    def process_event(self, parsed_data):
        """
        Processes a single parsed log event.
        Updates active_jobs and appends messages to report_entries.
        """
        status = parsed_data["status"]
        pid = parsed_data["pid"]
        job_description = parsed_data["description"]
        current_timestamp_seconds = parsed_data["timestamp_seconds"]
        timestamp_str = parsed_data["original_timestamp_str"]
        line_number = parsed_data["line_number"]

        if status == "START":
            if pid in self.active_jobs:
                prev_job_info = self.active_jobs[pid]
                self.report_entries.append(
                    f"ANOMALY: Line {line_number}: Job '{job_description}' (PID: {pid}) "
                    f"received a new START at {timestamp_str} but was already running since "
                    f"{prev_job_info['start_timestamp_string']} (Line: {prev_job_info['start_line_number']}). "
                    f"Overwriting previous start."
                )
            self.active_jobs[pid] = {
                "start_time_seconds": current_timestamp_seconds,
                "description": job_description, # Use description from this START event
                "start_timestamp_string": timestamp_str,
                "start_line_number": line_number
            }
        elif status == "END":
            if pid in self.active_jobs:
                job_info = self.active_jobs[pid]
                start_time_seconds = job_info["start_time_seconds"]
                # Use description from the START event for consistency in reporting
                original_job_description = job_info["description"]
                start_timestamp_str = job_info["start_timestamp_string"]
                start_line = job_info["start_line_number"]

                duration_seconds = current_timestamp_seconds - start_time_seconds

                if duration_seconds < 0:
                    self.report_entries.append(
                        f"ANOMALY: Line {line_number}: Job '{original_job_description}' (PID: {pid}) "
                        f"END event at {timestamp_str} is before its START event at {start_timestamp_str} (Line: {start_line}). "
                        f"Log data may be inconsistent."
                    )
                else:
                    formatted_duration = format_duration_from_seconds(duration_seconds)
                    # Optional: Add an INFO line for every completed job
                    # self.report_entries.append(
                    #     f"INFO: Job '{original_job_description}' (PID: {pid}) completed. "
                    #     f"Duration: {formatted_duration}. Started: {start_timestamp_str} (Line {start_line}), "
                    #     f"Ended: {timestamp_str} (Line {line_number})"
                    # )

                    if duration_seconds > ERROR_THRESHOLD_SECONDS:
                        self.report_entries.append(
                            f"ERROR: Job '{original_job_description}' (PID: {pid}) "
                            f"exceeded {ERROR_THRESHOLD_SECONDS // 60} minutes. Actual duration: {formatted_duration}. "
                            f"Started: {start_timestamp_str} (Line: {start_line}), Ended: {timestamp_str} (Line: {line_number})"
                        )
                    elif duration_seconds > WARNING_THRESHOLD_SECONDS:
                        self.report_entries.append(
                            f"WARNING: Job '{original_job_description}' (PID: {pid}) "
                            f"exceeded {WARNING_THRESHOLD_SECONDS // 60} minutes. Actual duration: {formatted_duration}. "
                            f"Started: {start_timestamp_str} (Line: {start_line}), Ended: {timestamp_str} (Line: {line_number})"
                        )
                del self.active_jobs[pid]
            else:
                self.report_entries.append(
                    f"ANOMALY: Line {line_number}: Job '{job_description}' (PID: {pid}) "
                    f"has an END event at {timestamp_str} but no corresponding START event was found or it was already processed."
                )
        else: # Invalid status
            self.report_entries.append(
                f"ANOMALY: Line {line_number}: Invalid status '{parsed_data['status']}' " # Use status from parsed_data
                f"for job '{job_description}' (PID: {pid}) at {timestamp_str}."
            )

    def finalize_report_for_unfinished_jobs(self):
        """Adds warning messages to report_entries for jobs that started but didn't end."""
        if self.active_jobs:
            self.report_entries.append("\n--- Unfinished Jobs (Started but no END event) ---")
            for pid, job_info in self.active_jobs.items():
                self.report_entries.append(
                    f"WARNING: Job '{job_info['description']}' (PID: {pid}) "
                    f"started at {job_info['start_timestamp_string']} (Line: {job_info['start_line_number']}) "
                    f"but did not have an END event in the log."
                )