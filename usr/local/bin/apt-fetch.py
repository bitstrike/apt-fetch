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

# info about apt-fetch execution
class STATS:
    def __init__(self):
        self.num_runs = 0
        self.num_complete = 0
        self.last_run = None
        self.packages_queued = 0
        self.archives_path = "/var/cache/apt/archives"
        self.num_archived = 0
        self.num_partial = 0
        self.fetch_errors = 0

    def update(self, timestamp):
        self.num_runs += 1
        self.last_run = timestamp

    def update_complete(self, timestamp):
        self.num_complete += 1
        self.last_run = timestamp

# info about deb packages
class DEB_PKG:
    def __init__(self, filename, version, name):
        self.filename = filename
        self.version = version
        self.name = name
        
# build list of packages in /var/cache/apt/archives and return it
def get_pkgs():
    deb_packages = []
    archives_path = "/var/cache/apt/archives"
    
    try:
        if os.path.exists(archives_path) and os.path.isdir(archives_path):
            for root, dirs, files in os.walk(archives_path):
                deb_files = [file for file in files if file.endswith(".deb")]
                for deb_file in deb_files:
                    deb_file_path = os.path.join(root, deb_file)
                    package = get_package_info(deb_file_path)
                    deb_packages.append(package)
    except Exception as e:
        print(f"{RED_COLOR}Error reading .DEB packages in {archives_path}: {e}{RESET_COLOR}")
    
    return deb_packages
        

# check if a given DEB_PKG object is installed on the system
def get_installed(deb_package):
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
            print(f"Error checking installation status for {deb_package.name}: {e}")
            return False
    


# remove packages which have already been installed
def cleanup_cache(deb_package):
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

  
# get the number of packages waiting to be applied        
def count_deb_packages(directory_path):
    deb_count = 0
    try:
        if os.path.exists(directory_path) and os.path.isdir(directory_path):
            for root, dirs, files in os.walk(directory_path):
                deb_count += len([file for file in files if file.endswith(".deb")])
    except Exception as e:
        print(f"Error counting .deb packages in {directory_path}: {e}")
    
    return deb_count


# check log file for statistics
def get_status(stats):
    today = datetime.now().strftime("%Y-%m-%d")
    stats = STATS()
    try:
        with open(log_filename, "r") as f:
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
        print(f"Error reading: {e}")
    
    # get number of packages staged
    stats.num_archived = count_deb_packages(stats.archives_path)
    # needs root - stats.num_partial = count_deb_packages(stats.partial_path)

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


# remove apt-fetch lock file if found to be from an old run
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



# run apt to fetch all updates and cache them in /var/cache/apt
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

# check APT cache and remove packages which have already been installed by comparing the name and version in the .deb with the version installed
# on the system - if it's installed at all.
def manage_apt_cache(deb_packages):
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
        print (f"trying {log_filename}")
        stats = get_status(stats)
        print(f"Number of runs today: {stats.num_runs}")
        print(f"Number of complete runs: {stats.num_complete}")
        print(f"Number of Errors encountered: {stats.fetch_errors}")
        print(f"{stats.num_archived} archived .deb packages queued and {stats.num_partial} partially downloaded")

        if stats.last_run:
            print(f"Last run timestamp: {stats.last_run}")
    else:
        try:
            handler = TimedRotatingFileHandler(log_filename, when='midnight', backupCount=6, interval=1, utc=True)

            # Add the formatter to the handler
            handler.setFormatter(formatter)

            # Add the handler to the logger
            logger.addHandler(handler)

            fetch_updates(stats)
        except PermissionError as e:
            print(f"{RED_COLOR}Error: {e}. Elevated permissions are required for log rotation.{RESET_COLOR}")
        
       



if __name__ == "__main__":
    main()
