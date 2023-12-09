 ## apt-fetch

 `apt-fetch` is a tool designed for automating the scheduled download of pending updates for Debian-based systems. The project consists of a cron job, and python script, for scheduling downloads via apt, and a Cinnamon applet for monitoring the status of these scheduled downloads. The script creates daily log files in `/var/log/` as well as a lock file in `/var/lock` to indicate if another instance of the script is in process. If the system is rebooted while apt-fetch is active, the lock file will likely persist preventing apt-fetch from running again. apt-fetch will attempt to remove this lock file if older than a certain amount of time.

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
     sudo cp apt-fetch/usr/local/bin/apt-fetch.py /usr/local/bin/
     sudo chmod +x /usr/local/bin/apt-fetch.py
     ```

 3. **Install the cron job:**
     ```bash
     sudo cp apt-fetch/etc/cron.d/apt-fetch /etc/cron.d/
     sudo chmod 0644 /etc/cron.d/apt-fetch
     ```

 4. **Install the Cinnamon Applet:**
    Install the Cinnamon applet to monitor the status of scheduled downloads. The applet directory has a specific location and naming convention for desktop applets and must be named correctly.
    ```bash
    cd ~/.local/share/cinnamon/applets/
    git clone https://github.com/bitstrike/apt-fetch.git
    mv apt-fetch apt-fetch@bitcrash
    ```
    After performing these steps, right click on the Cinnamon Panel and select the 'applets' item. If you've installed the applet correctly, it will appear as 'apt-fetch by bitstrike'. Toggle the checkmark to install it into the Cinnamon applet tray.

 ### Usage

 - **Manual Run:**
   You can manually run `apt-fetch` to initiate an immediate check for updates.
     ```bash
     sudo /usr/local/bin/apt-fetch.py
     ```
   Current status for apt-fetch can be displayed as a non-root user using the -s or -j flags
    ``` bash
    /usr/local/bin/apt-fetch.py -s
    ```

 - **Monitoring Applet:**
   The Cinnamon applet provides a visual indicator of the download status, allowing you to monitor the progress conveniently.

 ### Log Files

 Log files are stored in the `/var/log/` directory with filenames following the pattern `apt-fetch-{day}.log`.

 ### Contributing

 Contributions are welcome! Feel free to open issues, submit pull requests, or provide feedback to improve the functionality and usability of `apt-fetch`.

