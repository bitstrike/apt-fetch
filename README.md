 ## apt-fetch

 `apt-fetch` is a tool designed for automating the scheduled download of pending updates for Debian-based systems. The project consists of a cron job, and bash script, for scheduling downloads via apt and a Cinnamon applet for monitoring the status of these scheduled downloads. The bash script creates log files in `/var/log/` as well as a lock file in `/var/lock` to indicate if another instance of the script is in process. If the system is rebooted while apt-fetch is active, the lock file will likely persist preventing apt-fetch from running again. 

 ### Features

 - **Scheduled Downloads:** `apt-fetch` utilizes a cron job to automatically schedule the download of pending updates at specified intervals.

 - **Rate Limiting:** Downloads are throttled at a default rate of 56K, ensuring minimal interference with modern broadband and preventing substantial disruptions during the update process.

 - **Logging:** Detailed logs are maintained, providing insights into the update process. Log files are organized by date, making it easy to review historical information.

 - **Lock Mechanism:** `apt-fetch` employs a lock mechanism to prevent multiple instances from running concurrently. This ensures the integrity of the update process and prevents potential conflicts.

 ### Installation

 1. **Clone the Repository:**
     ```bash
     git clone https://github.com/bitstrike/apt-fetch.git
     ```

 2. **Install the Script:**
     ```bash
     sudo cp apt-fetch/apt-fetch.sh /usr/local/bin/apt-fetch
     sudo chmod +x /usr/local/bin/apt-fetch
     ```

 3. **Configure the Cron Job:**
    Add a cron job entry to your crontab for automated scheduling.
     ```bash
     # Example crontab entry for running apt-fetch daily at 2 AM
     0 2 * * * /usr/local/bin/apt-fetch
     ```

 4. **Install the Cinnamon Applet:**
    Install the Cinnamon applet to monitor the status of scheduled downloads.

 ### Usage

 - **Manual Run:**
   You can manually run `apt-fetch` to initiate an immediate check for updates.
     ```bash
     sudo apt-fetch
     ```

 - **Monitoring Applet:**
   The Cinnamon applet provides a visual indicator of the download status, allowing you to monitor the progress conveniently.

 ### Log Files

 Log files are stored in the `/tmp/` directory with filenames following the pattern `apt-fetch-{day}.log`.

 ### Contributing

 Contributions are welcome! Feel free to open issues, submit pull requests, or provide feedback to improve the functionality and usability of `apt-fetch`.

