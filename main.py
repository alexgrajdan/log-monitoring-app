# main.py
"""
Main entry point for the log monitoring application.
Orchestrates the parsing, processing, and reporting of log data.
"""
# Change imports to reflect the new package structure
import config
from log_parser import parse_log_line, LogParsingError
from log_processor import LogProcessor
from reporter import print_final_report

def run_monitor():
    """
    Runs the entire log monitoring process.
    """
    lines_processed_count = 0
    current_line_number = 0
    processor = LogProcessor() # This instantiation remains the same

    print(f"Starting log monitoring for file: {config.LOG_FILE_PATH}\n") # config is now from the package

    try:
        with open(config.LOG_FILE_PATH, 'r') as log_file:
            for line_content in log_file:
                current_line_number += 1
                line_content = line_content.strip()

                if not line_content:  # Skip empty lines
                    continue
                
                lines_processed_count +=1

                try:
                    parsed_data = parse_log_line(line_content, current_line_number) # parse_log_line from package
                    processor.process_event(parsed_data)
                except LogParsingError as lpe:
                    processor.report_entries.append(str(lpe))

    except FileNotFoundError:
        processor.report_entries.append(
            f"CRITICAL ERROR: The log file '{config.LOG_FILE_PATH}' was not found."
        )
    except Exception as e:
        processor.report_entries.append(
            f"CRITICAL ERROR: An unexpected error occurred during file processing: {e}"
        )

    if lines_processed_count == 0 and not any("CRITICAL ERROR" in msg for msg in processor.report_entries):
        processor.report_entries.append(
            "ANOMALY: The log file is empty or contains no processable log entries."
        )

    processor.finalize_report_for_unfinished_jobs()
    print_final_report(processor.report_entries, lines_processed_count) # print_final_report from package

if __name__ == "__main__":
    run_monitor()