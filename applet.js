/*
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
 */


const Applet = imports.ui.applet;
const PopupMenu = imports.ui.popupMenu;
const St = imports.gi.St;
const Gio = imports.gi.Gio;
const Util = imports.misc.util;
const MessageTray = imports.ui.messageTray;
const Main = imports.ui.main;
const GLib      = imports.gi.GLib;
const Mainloop  = imports.mainloop;
const Lang      = imports.lang;
const Settings = imports.ui.settings;

let LastRun = '{"last_run": "none"}';
let lastNotificationTime = 0;
const OneHourInSeconds = 60 * 60
const OneDayInSeconds = 24 * OneHourInSeconds;
const NotifcationInterval = OneHourInSeconds * 4;
const UUID = "apt-fetch@bitcrash"; // Applet UUID

// write something to LookingGlass log
function db (s)
{
    global.log (`apt-fetch: ${s}`);
}


class AptFetchApplet extends Applet.IconApplet {
    constructor(metadata, orientation, panel_height, instance_id) {
        super(orientation, panel_height, instance_id);
        this._notifications = true;

        // tray icon
        this.set_applet_icon_symbolic_name("inactive");
        
        // tray popup label
        this.set_applet_tooltip("Applet Label");

        // menu popup when tray icon clicked
        this.menuManager = new PopupMenu.PopupMenuManager(this);
        this.menu = new Applet.AppletPopupMenu(this, orientation);
        this.menuManager.addMenu(this.menu);

        // status menu item
        this._onStatusClick = this._onStatusClick.bind(this);
        this.menuItem = new PopupMenu.PopupMenuItem("Status");
        this.menuItem.connect('activate', this._onStatusClick);
        this.menu.addMenuItem(this.menuItem);

        // notification toggle
        let iconName = this._notifications ? "aptdaemon-upgrade" : "aptdaemon-delete";
        this.notification_toggle = new PopupMenu.PopupSwitchIconMenuItem( _("Notifications"), this._notifications, iconName, St.IconType.SYMBOLIC);
        this.notification_toggle.connect('toggled', Lang.bind(this, this._launch_after_toggle));
        this.menu.addMenuItem(this.notification_toggle);
  
        // update manager item
        this._onMintUpdateClick = this._onMintUpdateClick.bind(this);
        this.menuItem = new PopupMenu.PopupMenuItem("Update Manager");
        this.menuItem.connect('activate', this._onMintUpdateClick);
        this.menu.addMenuItem(this.menuItem);

        // seed LastRun with something usable and call apt-fetch
        LastRun = '{ "last_run" : "pending" }';
        Util.spawnCommandLineAsyncIO("apt-fetch.py -j", (stdout) => {LastRun = stdout})

        // run apt-fetch regularly to monitor status 
        this._iconTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 60, () => {
            Util.spawnCommandLineAsyncIO("apt-fetch.py -j", (stdout) => {LastRun = stdout})
            return true;  // Repeat the timer
        });
        
        // Schedule state check of lock file every 5 seconds and update tooltip
        this._iconTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 5, () => {
            // Update the icon and tooltip based on the state of /tmp/apt-lock
            this.set_applet_icon_symbolic_name(this._stateCheck() ? "active" : "inactive");
            this.set_applet_tooltip(this._stateCheck() ? "apt-fetch is downloading updates" : "apt-fetch is idle");
            return true;  // Repeat the timer
        });

        // update the tray icon while apt-fetch is downloading packages
        this._iconTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, () => {
            
            // check for daily notification
            if (this._checkNotificationTimeout() == true)
            {
                this._showNotification ("(apt-fetch) Updates Are Available", "Updates are available to be applied to your system.\nOpen Update Manager to apply them.\n")
            }
                
            if (this._stateCheck() == true) 
            {
                // Toggle the icon between "inactive" and the original symbolic name
                if (this._isIconInactive) 
                {
                    this.set_applet_icon_symbolic_name("transferring");
                } 
                else 
                {
                    this.set_applet_icon_symbolic_name("active");
                }
                
                this._isIconInactive = !this._isIconInactive;
            }

            return true;  // Repeat the timer
        });
    }

    // check if it's time to display the notification message again
    _checkNotificationTimeout()
    {
        // Check if a day has passed since the last notification
        const currentTime = Math.floor(Date.now() / 1000); // current time in seconds

        try {
            // Attempt to parse LastRun
            var parsedData = JSON.parse(LastRun);
            
            // Handle parsed data
            // ...
            // if updates have been downloaded and desktop has just been logged into
            if (parsedData.num_archived > 0)
            {
                if (lastNotificationTime == 0)
                {
                    lastNotificationTime = currentTime;
                    return true;
                }
            }

            // if time since last notification has expired, and updates are available, notify again
            if (currentTime - lastNotificationTime >= NotifcationInterval) 
            {
                // don't notify if nothing to update
                if (parsedData.num_archived > 0)
                {
                    // Update the last notification time
                    db ("_checkNotificationTimeout:parseddata is > 0");
                    lastNotificationTime = currentTime;
                    return true
                }
            }            
        }
        catch (error) {
            // Handle parsing error
            console.error("Error parsing LastRun:", error);
            console.log("LastRun JSON data:", JSON.stringify(JSON.parse(LastRun), null, 2));
            this._showNotification ("(apt-fetch) JSON error", "The apt-fetch.py command produced unexpected output. This is likely due to an error message related to a system issue.\nCheck /var/log/ for more info.\n")
        }

        return false
    }
    
    // add a notification message to the Cinnamon notification system
    // also this way: GLib.spawn_command_line_async('notify-send "Something" --icon=dialog-information'); 
    _showNotification(title, message) 
    {
        // don't display notifications if toggled off in menu
        if (this._notifications == false)
        {
            db ("notifications are toggled off");
            return;
        }

        let source = new MessageTray.SystemNotificationSource();
        Main.messageTray.add(source);
    
        let notification = new MessageTray.Notification(source, title, message);
        notification.setTransient(false);
        notification.setUrgency(MessageTray.Urgency.NORMAL);
        source.notify(notification);
    }

    // use Zenity to show the runtime stats for apt-fetch
    _onStatusClick() {
        try 
        {
            db(`Launching zenity dialog: LastRun ${JSON.stringify(LastRun, null, 2)}`);
            
            // Separate the error message, if there is one, and JSON data
            let errorMessage = '';
            let jsonData = null;
            const errorIndex = LastRun.indexOf('{');

            if (errorIndex !== -1) 
            {
                errorMessage = LastRun.substring(0, errorIndex).trim();
                jsonData = JSON.parse(LastRun.substring(errorIndex));
            } 
            else 
            {
                jsonData = JSON.parse(LastRun);
            }
    
            // Log the parsed data
            db(`Error Message: ${errorMessage}`);
            db(`Parsed Data: ${JSON.stringify(jsonData, null, 2)}`);
            db(`logfile_writeable: ${jsonData.logfile_writeable}`);
            
            // Check if jsonData.last_run exists before accessing its properties
            if (jsonData && jsonData.last_run && jsonData.last_run.toLowerCase() === "pending") 
            {
                Util.spawnCommandLine(`zenity --info --text="No status available yet, apt-fetch is pending."`);
            } 
            else 
            {
                Util.spawnCommandLine(`zenity --info --text="apt-fetch was last run at ${jsonData.last_run}\n${jsonData.runs_today} fetches have been done today\n${jsonData.runs_complete} fetches have completed.\n${jsonData.fetch_errors} errors were encountered.\n${jsonData.num_archived} packages are awaiting installation. \napt-fetch logfile exists:${jsonData.logfile_exists}\napt-fetch logfile is writeable: ${jsonData.logfile_writeable}.\n"`);
            }
        } 
        catch (error) 
        {
            // Handle parsing error
            db(`Error during _onStatusClick: ${error}`);
            this._showNotification("(apt-fetch) Zenity error", "The apt-fetch applet was not able to run the zenity command to display the status.\nMore info may be available in /var/log or by running apt-fetch.py -s\n");
            // Optionally, you can display an error message using Zenity or another method.
        }
    }

    
    // Check the existence of /var/lock/apt-fetch which signals that apt-fetch.py is currently running
    _stateCheck() {
        try 
        {
            let file = Gio.file_new_for_path("/var/lock/apt-fetch");
            return file.query_exists(null);
        } 
        catch (e) 
        {
            return false;
        }

    }
   
    // launch the mint update tool
    _onMintUpdateClick() {
        // item clicked
        Util.spawnCommandLine("mintupdate");
    }


    // make applet menu visible
    on_applet_clicked(event) {
        this.menu.toggle();
    }
  
    // pop-down menu after toggle selected
    _launch_after_toggle() {  
        this._notifications ^= true;      
        this.menu.toggle(); // Hide popup menu
        db ("notifications are " + this._notifications);
    }

    // cleanup
    on_applet_removed_from_panel() {
        // Cleanup logic if needed
        if (this._iconTimer) {
            GLib.source_remove(this._iconTimer);  // Remove the timer when the applet is removed
        }        
    }

    // cleanup
    destroy() {
        // Cleanup logic if needed
        super.destroy();        
        
        if (this._iconTimer) {
            GLib.source_remove(this._iconTimer);  // Remove the timer when the applet is destroyed
        }
    }
}

function main(metadata, orientation, panel_height, instance_id) {
    return new AptFetchApplet(metadata, orientation, panel_height, instance_id);
}
