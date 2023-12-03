#!/usr/bin/env python3

import os
import subprocess
from datetime import datetime, timedelta
import argparse
import logging
from logging.handlers import TimedRotatingFileHandler

lock_file           = "/var/lock/apt-fetch"
rate_limit          = "56K"
lock_file_max_age   = 86400  # in seconds

# Set up the logger
logger = logging.getLogger('daily_logger')
logger.setLevel(logging.INFO)

# Set up the formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Set up the TimedRotatingFileHandler
log_filename = "/var/log/apt-fetch-{}.log".format(datetime.now().strftime("%A").lower())
handler = TimedRotatingFileHandler(log_filename, when='midnight', backupCount=6, interval=1, utc=True)

# Add the formatter to the handler
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)

class STATS:
    def __init__(self):
        self.num_runs = 0
        self.num_complete = 0
        self.last_run = None

    def update(self, timestamp):
        self.num_runs += 1
        self.last_run = timestamp

    def update_complete(self, timestamp):
        self.num_complete += 1
        self.last_run = timestamp


def get_status(stats):
    today = datetime.now().strftime("%Y-%m-%d")
    stats = STATS()
    print (f"trying {log_filename}")
    try:
        with open(log_filename, "r") as f:
            lines = f.readlines()
            for line in lines:
                if "Checking latest apt" in line and today in line:
                    stats.update (line.split("]")[0][1:])
                if "apt-fetch complete" in line and today in line:
                    stats.update_complete(line.split("]")[0][1:])
                    stats.last_run = line.split("]")[0][1:]
    
    except (FileNotFoundError, PermissionError) as e:
        print(f"Error reading: {e}")
    
    return stats

# write/create a log file 
def db(*args):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Try to open the file in append mode
        with open(log_filename, "a") as f:
            print(f"[{timestamp}]", *args, file=f)
    except FileNotFoundError:
        # If the file does not exist, create it and append to it
        with open(log_filename, "w") as f:
            print(f"[{timestamp}]", *args, file=f)
    except Exception as e:
        print(f"Error accessing the file: {e}")


def remove_stale_lock(lock_file_path, threshold):
    do_remove = False
    if os.path.exists(lock_file_path):
        db("Found a lock file")
        file_timestamp = os.path.getmtime(lock_file_path)
        current_time = datetime.now().timestamp()
        age = current_time - file_timestamp
        db(f"Found a lock file {age} seconds old")

        # Read PID from the lock file
        try:
            with open(lock_file_path, "r") as lock_file:
                pid = int(lock_file.read().strip())
        except (ValueError, FileNotFoundError):
            pid = None

        if age > threshold:
            db(f"The file {lock_file_path} appears to be stale. Removing it.")
            do_remove = True

        # Check if the PID is a valid number
        if isinstance(pid, int):
            # Check if the process with the PID is running
            try:
                subprocess.check_output(["ps", "-p", str(pid), "-o", "pid="])
                db(f"Another instance of the script is already running with PID {pid}. Exiting.")
                exit(1)
            except subprocess.CalledProcessError:
                do_remove = True

        if do_remove:
            db(f"Stale lock file found for PID {pid}. Removing.")
            os.remove(lock_file_path)


def fetch_updates(stats):
    remove_stale_lock(lock_file, lock_file_max_age)

    # Write the current PID to the lock file
    with open(lock_file, "w") as lock_file_handle:
        lock_file_handle.write(str(os.getpid()))

    # Run apt-get update and apt-get dist-upgrade download only with rate limit
    db("Checking latest apt..")
    with open(log_filename, "a") as log:
        subprocess.run(
            ["apt-get", "update"],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
        subprocess.run(
            [
                "apt-get",
                "dist-upgrade",
                "-y",
                "--quiet",
                "--download-only",
                f"-oAcquire::http::Dl-Limit={rate_limit}",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )

    # Remove the lock file after completing the update and upgrade
    os.remove(lock_file)
    db("apt-fetch complete.")


def main():
    parser = argparse.ArgumentParser(description='Fetch updates and display status.')
    parser.add_argument('-s', '--status', action='store_true', help='Display status')
    stats = STATS()
    args = parser.parse_args()

    if args.status:
        stats = get_status(stats)
        
        print(f"Number of runs today: {stats.num_runs}")
        print(f"Number of complete runs: {stats.num_complete}")

        if stats.last_run:
            print(f"Last run timestamp: {stats.last_run}")
    else:
        fetch_updates(stats)

    


if __name__ == "__main__":
    main()
