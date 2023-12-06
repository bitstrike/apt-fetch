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

let RunsToday = 0;
let CompleteRuns = 0;
let CurrentLogFileName = "none"
let LastRun = "none";


function db (s)
{
    global.log (`apt-fetch: ${s}`);
}



class AptFetchApplet extends Applet.IconApplet {
    constructor(metadata, orientation, panel_height, instance_id) {
        super(orientation, panel_height, instance_id);

        // tray icon
        this.set_applet_icon_symbolic_name("inactive");
        
        // tray popup label
        this.set_applet_tooltip("Applet Label");

        // menu popup when icon clicked
        this.menuManager = new PopupMenu.PopupMenuManager(this);
        this.menu = new Applet.AppletPopupMenu(this, orientation);
        this.menuManager.addMenu(this.menu);

        this._onStatusClick = this._onStatusClick.bind(this);
        this.menuItem = new PopupMenu.PopupMenuItem("Status");
        this.menuItem.connect('activate', this._onStatusClick);
        this.menu.addMenuItem(this.menuItem);
        
        this._onMintUpdateClick = this._onMintUpdateClick.bind(this);
        this.menuItem = new PopupMenu.PopupMenuItem("Update Manager");
        this.menuItem.connect('activate', this._onMintUpdateClick);
        this.menu.addMenuItem(this.menuItem);

        this._onAboutClick = this._onAboutClick.bind(this);
        this.menuItem = new PopupMenu.PopupMenuItem("About");
        this.menuItem.connect('activate', this._onAboutClick);
        this.menu.addMenuItem(this.menuItem);
        
        LastRun = '{ "last_run" : "pending" }';
        Util.spawnCommandLineAsyncIO("apt-fetch.py -j", (stdout) => {LastRun = stdout})

        this._iconTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 60, () => {
            Util.spawnCommandLineAsyncIO("apt-fetch.py -j", (stdout) => {LastRun = stdout})
            return true;  // Repeat the timer
        });
        
        // Schedule state check every 5 seconds
        this._iconTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 5, () => {
            // Update the icon and tooltip based on the state of /tmp/apt-lock
            this.set_applet_icon_symbolic_name(this._stateCheck() ? "active" : "inactive");
            this.set_applet_tooltip(this._stateCheck() ? "apt-fetch is downloading updates" : "apt-fetch is idle");
            return true;  // Repeat the timer
        });

        // blink icon while downloading
        this._iconTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, () => {
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

    _showNotification()
    {
        let source = new MessageTray.SystemNotificationSource();
        Main.messageTray.add(source);
        let notification = new MessageTray.Notification(source, _("Timer"), _("Time's up!"));
        notification.setTransient(false);
        notification.setUrgency(MessageTray.Urgency.NORMAL);
        source.notify(notification);
    }

    _onStatusClick() {
        var parsedData = JSON.parse(LastRun);
        if (parsedData.last_run.toLowerCase() === "pending") 
        {
            Util.spawnCommandLine(`zenity --info --text="No status avaialable yet, apt-fetch is pending."`);
        }
        else
            Util.spawnCommandLine(`zenity --info --text="apt-fetch was last run at ${parsedData.last_run}\n${parsedData.runs_today} fetches have been done today\n${parsedData.runs_complete} fetches have completed.\n${parsedData.fetch_errors} errors were encountered.\n${parsedData.num_archived} packages are awaiting installation."`);


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

   
    _onMintUpdateClick() {
        // item clicked
        Util.spawnCommandLine("mintupdate");
    }

    _onAboutClick() {
        
        let appletUUID = this.metadata.uuid;
        let applet = Cinnamon.AppSystem.get_default().get_app(appletUUID);
        let aboutText = "Your applet name\nVersion: \n\nCopyright © Your Name";
        Util.spawnCommandLine("testapp_applet.sh");
        Cinnamon.AppletAbout.show(appletUUID, applet.metadata.name, applet.version, aboutText);
    }

    // make applet menu visible
    on_applet_clicked(event) {
        this.menu.toggle();
    }

    on_applet_removed_from_panel() {
        // Cleanup logic if needed
        if (this._iconTimer) {
            GLib.source_remove(this._iconTimer);  // Remove the timer when the applet is removed
        }        
    }

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
