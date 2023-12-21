#!/usr/bin/env python3
"""
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
import argparse
import logging
from logging.handlers import TimedRotatingFileHandler
import apt

# ANSI escape codes for colors
RED_COLOR = '\033[91m'
RESET_COLOR = '\033[0m'

ARCHIVES_PATH       = "/var/cache/apt/archives"
LOCK_FILE           = "/var/lock/apt-fetch"
RATE_LIMIT          = "56K"
LOCK_FILE_MAX_AGE   = 86400  # in seconds

# Set up the logger
logger = logging.getLogger('daily_logger')
logger.setLevel(logging.INFO)

# Set up the formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Set up the TimedRotatingFileHandler
LOG_FILENAME = "/var/log/apt-fetch-{}.log".format(datetime.now().strftime("%A").lower())

class STATS:
    """
    A class to store statistics about apt-fetch execution.

    Attributes:
    - num_runs (int): The number of runs performed.
    - num_complete (int): The number of complete runs.
    - last_run (str): Timestamp of the last run.
    - packages_queued (int): Number of packages in the queue.
    - archives_path (str): Path to the APT archives.
    - num_archived (int): Number of archived packages.
    - num_partial (int): Number of partially downloaded packages.
    - fetch_errors (int): Number of fetch errors.
    """
    def __init__(self):
        self.num_runs = 0
        self.num_complete = 0
        self.last_run = None
        self.packages_queued = 0
        self.archives_path = ARCHIVES_PATH
        self.num_archived = 0
        self.num_partial = 0
        self.fetch_errors = 0

    def update(self, timestamp):
        self.num_runs += 1
        self.last_run = timestamp

    def update_complete(self, timestamp):
        self.num_complete += 1
        self.last_run = timestamp

class DEB_PKG:
    """
    A class to represent Debian packages.

    Attributes:
    - filename (str): The filename of the Debian package.
    - version (str): The version of the Debian package.
    - name (str): The name of the Debian package.
    """
    def __init__(self, filename, version, name):
        self.filename = filename
        self.version = version
        self.name = name
        

def get_pkgs():
    """
    Build a list of Debian package files in the /var/cache/apt/archives directory.

    Returns:
    - list: List of DEB_PKG objects representing Debian packages.
    """
    deb_packages = []
    
    try:
        if os.path.exists(ARCHIVES_PATH) and os.path.isdir(ARCHIVES_PATH):
            for root, dirs, files in os.walk(ARCHIVES_PATH):
                deb_files = [file for file in files if file.endswith(".deb")]
                for deb_file in deb_files:
                    deb_file_path = os.path.join(root, deb_file)
                    package = get_package_info(deb_file_path)
                    deb_packages.append(package)
    except Exception as e:
        print(f"{RED_COLOR}Error reading .DEB packages in {ARCHIVES_PATH}: {e}{RESET_COLOR}")
    
    return deb_packages
        

# check if a given DEB_PKG object is installed on the system
def get_installed(deb_package):
    """
    Check if a Debian package is installed on the system.

    Parameters:
    - deb_package (DEB_PKG): The Debian package to check.

    Returns:
    - bool: True if the package is installed and has the correct version, False otherwise.
    """
    try:
        # Run dpkg-query command to check if the package is installed
        output = subprocess.check_output(["dpkg-query", "--show", deb_package.name], text=True, stderr=subprocess.STDOUT)

        # Parse the version from the second column of the output
        installed_version = output.split('\t')[1].strip() if output else None

        # Check if the package is installed and has the correct version
        if installed_version == deb_package.version:
            return True
        else:
            return False

    except subprocess.CalledProcessError as e:
        # If the return status is 1, the package is not installed
        if e.returncode == 1:
            return False
        else:
            # If the return status is different, there might be another problem
            print(f"{RED_COLOR}Error checking installation status for {deb_package.name}: {e}{RESET_COLOR}")
            return False
    


# remove packages which have already been installed
def cleanup_cache(deb_package):
    """
    Remove a specified Debian package file from the /var/cache/apt/archives directory.

    Parameters:
    - deb_package (DEB_PKG): The Debian package to remove from the cache.

    Returns:
    - bool: True if the cleanup succeeds, False otherwise.
    """
    try:
        # Remove the package file from /var/cache/apt/archives
        package_file_path = os.path.join("/var/cache/apt/archives", deb_package.filename)
        os.remove(package_file_path)

        print(f"Package {deb_package.filename} removed from /var/cache/apt/archives.")
        return True
    except FileNotFoundError:
        # Handle the case where the file is not found
        print(f"{RED_COLOR}Error: Package file {deb_package.filename} not found in /var/cache/apt/archives.{RESET_COLOR}")
        return False
    except Exception as e:
        # Handle other exceptions
        print(f"{RED_COLOR}Error cleaning up cache for {deb_package.filename}: {e}{RESET_COLOR}")
        return False
    
    

# get info on packages in /var/cache/apt/archives
def get_package_info(package_file_path):
    """
    Retrieve information about a Debian package file using the dpkg --info command.

    Parameters:
    - package_file_path (str): The path to the Debian package file.

    Returns:
    - DEB_PKG: DEB_PKG object representing Debian package information.
    """
    package_name = os.path.basename(package_file_path)

    try:
        # Run dpkg --info command
        dpkg_info_output = subprocess.check_output(["dpkg", "--info", package_file_path], text=True)

        # Parse dpkg_info_output for Version and Package information
        version_line = next(line for line in dpkg_info_output.split('\n') if line.startswith(' Version:'))
        version = version_line.split(': ')[1].strip()

        name_line = next(line for line in dpkg_info_output.split('\n') if line.startswith(' Package:'))
        name = name_line.split(': ')[1].strip()

        return DEB_PKG(filename=package_name, version=version, name=name)

    except subprocess.CalledProcessError as e:
        print(f"{RED_COLOR}Error running dpkg --info for {package_file_path}: {e}{RESET_COLOR}")
        return DEB_PKG(filename=package_name, version="Not available", name="Not available")

  
def count_deb_packages(directory_path):
    """
    Count the number of Debian package files in a specified directory.

    Parameters:
    - directory_path (str): The path to the directory containing Debian packages.

    Returns:
    - int: The number of Debian package files.
    """
    deb_count = 0
    try:
        if os.path.exists(directory_path) and os.path.isdir(directory_path):
            for root, dirs, files in os.walk(directory_path):
                deb_count += len([file for file in files if file.endswith(".deb")])
    except Exception as e:
        print(f"{RED_COLOR}Error counting .deb packages in {directory_path}: {e}{RESET_COLOR}")
    
    return deb_count


def get_status(stats):
    """
    Retrieve status information from the log file.

    Parameters:
    - stats (STATS): STATS object to update with status information.

    Returns:
    - STATS: Updated STATS object.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    stats = STATS()
    try:
        with open(LOG_FILENAME, "r") as f:
            lines = f.readlines()
            for line in lines:
                if "Checking latest apt" in line and today in line:
                    stats.update (line.split("]")[0][1:])
                if "apt-fetch complete" in line and today in line:
                    stats.update_complete(line.split("]")[0][1:])
                    stats.last_run = line.split("]")[0][1:]
                if "Failed" in line:
                    stats.fetch_errors += 1

    except (FileNotFoundError, PermissionError) as e:
        print(f"{RED_COLOR}Error reading: {e}{RESET_COLOR}")
    
    # get number of packages staged
    stats.num_archived = count_deb_packages(stats.archives_path)
    # needs root - stats.num_partial = count_deb_packages(stats.partial_path)

    return stats


def db(*args):
    """
    Write log entries to the log file.

    Parameters:
    - args: Log entry components to be written to the log file.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Try to open the file in append mode
        with open(LOG_FILENAME, "a") as f:
            print(f"[{timestamp}]", *args, file=f)
    except FileNotFoundError:
        # If the file does not exist, create it and append to it
        with open(LOG_FILENAME, "w") as f:
            print(f"[{timestamp}]", *args, file=f)
    except Exception as e:
        print(f"{RED_COLOR}Error accessing {LOG_FILENAME}: {e}{RESET_COLOR}")


def remove_stale_lock(lock_file_path, threshold):
    """
    Remove a stale lock file if found.

    Parameters:
    - lock_file_path (str): The path to the lock file.
    - threshold (int): The maximum age (in seconds) for a lock file to be considered stale.
    """
    do_remove = False
    if os.path.exists(lock_file_path):
        db("Found a lock file")
        file_timestamp = os.path.getmtime(lock_file_path)
        current_time = datetime.now().timestamp()
        age = current_time - file_timestamp
        db(f"Found a lock file {age} seconds old")

        # Read PID from the lock file
        try:
            with open(lock_file_path, "r") as LOCK_FILE:
                pid = int(LOCK_FILE.read().strip())
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
    """
    Fetch updates and cache them in /var/cache/apt/.

    Parameters:
    - stats (STATS): STATS object to update during the update process.
    """
    remove_stale_lock(LOCK_FILE, LOCK_FILE_MAX_AGE)

    # Write the current PID to the lock file
    with open(LOCK_FILE, "w") as lock_file_handle:
        lock_file_handle.write(str(os.getpid()))

    # Run apt-get update and apt-get dist-upgrade download only with rate limit
    db("Checking latest apt..")
    with open(LOG_FILENAME, "a") as log:
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
                f"-oAcquire::http::Dl-Limit={RATE_LIMIT}",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )

    # Remove the lock file after completing the update and upgrade
    os.remove(LOCK_FILE)
    db("apt-fetch complete.")


def manage_apt_cache(deb_packages):
    """
    Manage the Apt cache, including checking package information, installation status,
    and cleaning up the cache based on command-line arguments.
    """
    for pkg in deb_packages:
        print(f"Filename: {pkg.filename}")
        print(f"Version: {pkg.version}")
        print(f"Name: {pkg.name}")

        try:
            # Check if the package is installed
            if get_installed(pkg):
                print("Installed: Yes")

                # Try to clean up the cache
                if cleanup_cache(pkg):
                    print("Cleanup succeeded")
                else:
                    print(f"{RED_COLOR}Cleanup failed{RESET_COLOR}")
            else:
                print("Installed: No")

        except Exception as e:
            print(f"{RED_COLOR}Error: {e}{RESET_COLOR}")
            
            

def main():
    """
    Fetch updates and display status based on command-line arguments.

    -s, --status: Display general status.
    -j, --json_status: Display status in JSON format.
    -p, --pkg_info: Display information about installed packages.
    """
    parser = argparse.ArgumentParser(description='Fetch updates and display status.')
    parser.add_argument('-s', '--status', action='store_true', help='Display status')
    parser.add_argument('-j', '--json_status', action='store_true', help='Display status as JSON')
    parser.add_argument('-p', '--pkg_info', action='store_true', help='Display information about installed packages')
    
    stats = STATS()
    args = parser.parse_args()
    
    if args.pkg_info:
        deb_packages = get_pkgs()
        manage_apt_cache(deb_packages)
                
    elif args.json_status:
        stats = get_status(stats)
        data = {"runs_today" : stats.num_runs, "runs_complete" : stats.num_complete, "last_run" : stats.last_run, "num_archived" : stats.num_archived, "fetch_errors" : stats.fetch_errors}
        print (json.dumps(data, indent=2))

    elif args.status:
        print (f"trying {LOG_FILENAME}")
        stats = get_status(stats)
        print(f"Number of runs today: {stats.num_runs}")
        print(f"Number of complete runs: {stats.num_complete}")
        print(f"Number of Errors encountered: {stats.fetch_errors}")
        print(f"{stats.num_archived} archived .deb packages queued and {stats.num_partial} partially downloaded")

        if stats.last_run:
            print(f"Last run timestamp: {stats.last_run}")
    else:
        try:
            handler = TimedRotatingFileHandler(LOG_FILENAME, when='midnight', backupCount=6, interval=1, utc=True)

            # Add the formatter to the handler
            handler.setFormatter(formatter)

            # Add the handler to the logger
            logger.addHandler(handler)

            fetch_updates(stats)
        except PermissionError as e:
            print(f"{RED_COLOR}Error: {e}. Elevated permissions are required for log rotation.{RESET_COLOR}")
        
       
if __name__ == "__main__":
    main()
