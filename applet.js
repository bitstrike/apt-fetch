const Applet = imports.ui.applet;
const PopupMenu = imports.ui.popupMenu;
const St = imports.gi.St;
const Gio = imports.gi.Gio;
const Util = imports.misc.util;

const GLib      = imports.gi.GLib;
const Mainloop  = imports.mainloop;
const Lang      = imports.lang;

const Settings = imports.ui.settings;



class TestAppApplet extends Applet.IconApplet {
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

        this._onItem1Click = this._onItem1Click.bind(this);
        this.menuItem = new PopupMenu.PopupMenuItem("Status");
        this.menuItem.connect('activate', this._onItem1Click);
        this.menu.addMenuItem(this.menuItem);
        
        this._onItem2Click = this._onItem2Click.bind(this);
        this.menuItem = new PopupMenu.PopupMenuItem("Update Manager");
        this.menuItem.connect('activate', this._onItem2Click);
        this.menu.addMenuItem(this.menuItem);

        this._onItem3Click = this._onItem3Click.bind(this);
        this.menuItem = new PopupMenu.PopupMenuItem("About");
        this.menuItem.connect('activate', this._onItem3Click);
        this.menu.addMenuItem(this.menuItem);
        
        // Schedule state check every 5 seconds
        this._iconTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 5, () => {
            // Update the icon and tooltip based on the state of /tmp/apt-lock
            this.set_applet_icon_symbolic_name(this._stateCheck() ? "active" : "inactive");
            this.set_applet_tooltip(this._stateCheck() ? "apt-fetch is downloading updates" : "apt-fetch is idle");
            return true;  // Repeat the timer
        });
    }

    _stateCheck() {
        // Check the existence of /tmp/apt-lock
        try 
        {
            let file = Gio.file_new_for_path("/tmp/apt-lock");
            return file.query_exists(null);
        } 
        catch (e) 
        {
            return false;
        }
    }

    _onItem1Click() {
        // item clicked
        Util.spawnCommandLine("testapp_applet.sh");
    }    
    
    _onItem2Click() {
        // item clicked
        Util.spawnCommandLine("mintupdate");
    }
    _onItem3Click() {
        // "About" item clicked
        let appletUUID = this.metadata.uuid;
        Util.spawnCommandLine(`zenity --info --text="Applet UUID: ${appletUUID}"`);
        let applet = Cinnamon.AppSystem.get_default().get_app(appletUUID);
        let aboutText = "apt-fetch\nVersion: " + applet.version + "\n\nCopyright ©bitstrike";
        Cinnamon.AppletAbout.show(appletUUID, applet.metadata.name, applet.version, aboutText);
    }
    
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
    return new TestAppApplet(metadata, orientation, panel_height, instance_id);
}
