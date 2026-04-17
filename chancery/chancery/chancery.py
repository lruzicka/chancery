#!/usr/bin/python3

# Copyright 2022, Red Hat, Inc
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Authors:
#   Lukáš Růžička <lruzicka@redhat.com>

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('GtkSource', '5')
from gi.repository import Gtk, Gdk, Gio, GLib, Pango, GtkSource

import io
import json
import libvirt
import os
import multiprocessing
import re
import sys
import subprocess
import webbrowser
from chancery.testapi import Definition as df
from chancery.testapi import testAPI as api
from chancery.needler import Application as needler
from PIL import Image


class Application:
    def __init__(self, filename=None):
        # Set up the main application
        self.app = Gtk.Application(application_id='org.chancery.editor')
        self.app.connect('activate', self.on_activate)

        # Set the appname
        self.appname = "Chancery - an openQA script editor"

        # Set up status variables
        self.db = api.show_definitions()  # Snippets from the testapi database
        self.filetosave = None  # A filename to save the content into.
        self.is_saved = True  # If the file is saved
        self.comments_on = True  # Comments are switched on
        self.args_on = True  # Arguments are switched on
        self.kvm = None  # Connection to KVM
        self.virtual_machine = None  # Holds the name of the connected virtual machine.
        self.latest_needle_taken = None
        self.filename = filename
        self.window = None

    def on_activate(self, app):
        """Create the main window when the application is activated."""
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title(self.appname)
        self.window.set_default_size(1200, 700)
        self.window.connect('close-request', self.on_close_request)

        # Set up key event controller for accelerators
        key_controller = Gtk.EventControllerKey()
        key_controller.connect('key-pressed', self.on_key_pressed)
        self.window.add_controller(key_controller)

        # Build UI
        self.create_ui()

        self.window.present()

        # Load file if provided
        if self.filename:
            self.open_file(self.filename)

    def create_ui(self):
        """Create the user interface."""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.set_child(main_box)

        # Create menu bar
        menu_model = self.create_menu_bar()
        menubar = Gtk.PopoverMenuBar.new_from_model(menu_model)
        main_box.append(menubar)

        # Content area (horizontal split)
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        content_box.set_margin_start(5)
        content_box.set_margin_end(5)
        content_box.set_margin_top(5)
        content_box.set_margin_bottom(5)
        content_box.set_hexpand(True)
        content_box.set_vexpand(True)
        main_box.append(content_box)

        # Quick menu on the left
        self.create_quick_menu(content_box)

        # Text editor on the right
        self.create_text(content_box)

    def create_menu_bar(self):
        """Creates the application menu using GMenu."""
        menubar = Gio.Menu()

        # File menu
        file_menu = Gio.Menu()
        file_menu.append("New", "app.new")
        file_menu.append("Open", "app.open")
        file_menu.append("Save", "app.save")
        file_menu.append("Save As", "app.saveas")
        file_menu.append("Exit", "app.quit")
        menubar.append_submenu("File", file_menu)

        # Video menu
        video_menu = Gio.Menu()
        video_menu.append("Assert and click match", "app.video-click")
        video_menu.append("Assert and doubleclick match", "app.video-dclick")
        video_menu.append("Click last match", "app.video-lastclick")
        video_menu.append("Assert screen for match", "app.video-assert")
        video_menu.append("Check screen for match", "app.video-check")
        video_menu.append("Check if match has tag", "app.video-tag")
        video_menu.append("Assert that screen is still", "app.video-still")
        video_menu.append("Assert that screen changes", "app.video-changes")
        video_menu.append("Wait if screen changes", "app.video-wait-changes")
        video_menu.append("Wait until screen is still", "app.video-wait-still")
        video_menu.append("Force soft failure", "app.video-force-fail")
        video_menu.append("Record soft failure", "app.video-soft-fail")
        video_menu.append("Record info", "app.video-info")
        video_menu.append("Take screenshot", "app.video-screenshot")
        menubar.append_submenu("Video", video_menu)

        # Audio menu
        audio_menu = Gio.Menu()
        audio_menu.append("Start audio recording", "app.audio-record")
        audio_menu.append("Assert recorded sound", "app.audio-assert")
        audio_menu.append("Check recorded sound", "app.audio-check")
        menubar.append_submenu("Audio", audio_menu)

        # Keyboard menu
        keyboard_menu = Gio.Menu()
        keyboard_menu.append("Press key (combination)", "app.kbd-press")
        keyboard_menu.append("Hold key", "app.kbd-hold")
        keyboard_menu.append("Release key", "app.kbd-release")
        keyboard_menu.append("Press key until event", "app.kbd-until")
        keyboard_menu.append("Type text", "app.kbd-type")
        keyboard_menu.append("Type text safely (Fedora)", "app.kbd-safe")
        keyboard_menu.append("Type password", "app.kbd-password")
        keyboard_menu.append("Run command", "app.kbd-command")
        menubar.append_submenu("Keyboard", keyboard_menu)

        # Mouse menu
        mouse_menu = Gio.Menu()
        mouse_menu.append("Click mouse at location", "app.mouse-click")
        mouse_menu.append("Doubleclick mouse at location", "app.mouse-dclick")
        mouse_menu.append("Tripleclick mouse at location", "app.mouse-tclick")
        mouse_menu.append("Drag with mouse", "app.mouse-drag")
        mouse_menu.append("Set mouse location", "app.mouse-pos")
        mouse_menu.append("Hide mouse cursor", "app.mouse-hide")
        menubar.append_submenu("Mouse", mouse_menu)

        # Variable menu
        variable_menu = Gio.Menu()
        variable_menu.append("Read variable", "app.var-read")
        variable_menu.append("Read variable (strict)", "app.var-strict")
        variable_menu.append("Set variable", "app.var-set")
        variable_menu.append("Check variable value", "app.var-check")
        variable_menu.append("Read variable as list", "app.var-list")
        variable_menu.append("Check value in list of variables", "app.var-check-list")
        menubar.append_submenu("Variables", variable_menu)

        # Scripts menu
        script_menu = Gio.Menu()
        script_menu.append("Run script and assert", "app.script-assert")
        script_menu.append("Run script", "app.script-run")
        script_menu.append("Run script in background", "app.script-bg")
        script_menu.append("Run sudo script and assert", "app.script-sudo-assert")
        script_menu.append("Run sudo script", "app.script-sudo")
        script_menu.append("Collect script output", "app.script-output")
        script_menu.append("Collect script output and validate", "app.script-validate")
        script_menu.append("Check if terminal is serial", "app.script-serial")
        script_menu.append("Wait for serial output", "app.script-wait")
        script_menu.append("Read test data from file", "app.script-file")
        script_menu.append("Save temp file", "app.script-temp")
        script_menu.append("Become root", "app.script-root")
        script_menu.append("Make sure package is installed", "app.script-package")
        script_menu.append("Hash the string with MD5", "app.script-md5")
        script_menu.append("Start GUI application", "app.script-gui")
        menubar.append_submenu("Scripts", script_menu)

        # Log menu
        log_menu = Gio.Menu()
        log_menu.append("Log a diagnostic message", "app.log-message")
        log_menu.append("Upload logs", "app.log-upload")
        log_menu.append("Upload asset", "app.log-asset")
        menubar.append_submenu("Logs", log_menu)

        # Helpers menu
        helper_menu = Gio.Menu()
        helper_menu.append("Get host's IP address", "app.helper-ip")
        helper_menu.append("Get the base URL of local os-autoinst", "app.helper-url")
        helper_menu.append("Get the data asset URL", "app.helper-asset")
        helper_menu.append("Make arguments compatible", "app.helper-compat")
        helper_menu.append("Show Curl progress meter", "app.helper-curl")
        menubar.append_submenu("Helpers", helper_menu)

        # Misc menu
        misc_menu = Gio.Menu()
        misc_menu.append("Send power signal to machine", "app.misc-power")
        misc_menu.append("Check machine shut down", "app.misc-check")
        misc_menu.append("Assert machine shut down", "app.misc-assert")
        misc_menu.append("Eject machine CD", "app.misc-eject")
        misc_menu.append("Save memory dump", "app.misc-dump")
        misc_menu.append("Save storage drives", "app.misc-storage")
        misc_menu.append("Freeze the VM", "app.misc-freeze")
        misc_menu.append("Resume the VM", "app.misc-resume")
        misc_menu.append("Parse jUnit log", "app.misc-junit")
        misc_menu.append("Parse extra log", "app.misc-extra")
        menubar.append_submenu("Misc", misc_menu)

        # Perl menu
        perl_menu = Gio.Menu()
        perl_menu.append("IF clause", "app.perl-if")
        perl_menu.append("IF ELSE clause", "app.perl-ifelse")
        perl_menu.append("IF ELSIF ELSE clause", "app.perl-ifelif")
        perl_menu.append("FOR clause", "app.perl-for")
        perl_menu.append("FOREACH clause", "app.perl-foreach")
        perl_menu.append("Assign VAR", "app.perl-var")
        perl_menu.append("SUB take single argument", "app.perl-arg")
        perl_menu.append("SUB take multiple arguments", "app.perl-args")
        perl_menu.append("UNLESS clause", "app.perl-unless")
        menubar.append_submenu("Perl", perl_menu)

        # Virtual machine menu
        vm_menu = Gio.Menu()
        vm_menu.append("Connect to VM", "app.vm-connect")
        vm_menu.append("Create needle", "app.vm-create")
        vm_menu.append("Edit needle", "app.vm-edit")
        menubar.append_submenu("VirtMachine", vm_menu)

        # Help menu
        help_menu = Gio.Menu()
        help_menu.append("Help", "app.help")
        help_menu.append("openQA TestApi Documentation", "app.help-testapi")
        help_menu.append("openQA Documentation", "app.help-docs")
        help_menu.append("About", "app.about")
        menubar.append_submenu("Help", help_menu)

        # Register all actions
        self.register_actions()

        return menubar

    def register_actions(self):
        """Register all menu actions."""
        # File actions
        action = Gio.SimpleAction.new("new", None)
        action.connect("activate", lambda a, p: self.new_file())
        self.app.add_action(action)

        action = Gio.SimpleAction.new("open", None)
        action.connect("activate", lambda a, p: self.open_file())
        self.app.add_action(action)

        action = Gio.SimpleAction.new("save", None)
        action.connect("activate", lambda a, p: self.save_file())
        self.app.add_action(action)

        action = Gio.SimpleAction.new("saveas", None)
        action.connect("activate", lambda a, p: self.save_as_file())
        self.app.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", lambda a, p: self.close_application())
        self.app.add_action(action)

        # Video actions
        self.add_action("video-click", lambda: self.database('video', 'Assert and click match'))
        self.add_action("video-dclick", lambda: self.database('video', 'Assert and doubleclick match'))
        self.add_action("video-lastclick", lambda: self.database('video', 'Click last match'))
        self.add_action("video-assert", lambda: self.database('video', 'Assert screen for match'))
        self.add_action("video-check", lambda: self.database('video', 'Check screen for match'))
        self.add_action("video-tag", lambda: self.database('video', 'Check if match has tag'))
        self.add_action("video-still", lambda: self.database('video', 'Assert that screen is still'))
        self.add_action("video-changes", lambda: self.database('video', 'Assert that screen changes'))
        self.add_action("video-wait-changes", lambda: self.database('video', 'Wait if screen changes'))
        self.add_action("video-wait-still", lambda: self.database('video', 'Wait until screen is still'))
        self.add_action("video-force-fail", lambda: self.database('video', 'Force soft failure'))
        self.add_action("video-soft-fail", lambda: self.database('video', 'Record soft failure'))
        self.add_action("video-info", lambda: self.database('video', 'Record info'))
        self.add_action("video-screenshot", lambda: self.database('video', 'Take screenshot'))

        # Audio actions
        self.add_action("audio-record", lambda: self.database('audio', 'Start audio recording'))
        self.add_action("audio-assert", lambda: self.database('audio', 'Assert recorded sound'))
        self.add_action("audio-check", lambda: self.database('audio', 'Check recorded sound'))

        # Keyboard actions
        self.add_action("kbd-press", lambda: self.database('keyboard', 'Press key'))
        self.add_action("kbd-hold", lambda: self.database('keyboard', 'Hold key'))
        self.add_action("kbd-release", lambda: self.database('keyboard', 'Release key'))
        self.add_action("kbd-until", lambda: self.database('keyboard', 'Press key until event'))
        self.add_action("kbd-type", lambda: self.database('keyboard', 'Type text'))
        self.add_action("kbd-safe", lambda: self.database('keyboard', 'Type text safely'))
        self.add_action("kbd-password", lambda: self.database('keyboard', 'Type password'))
        self.add_action("kbd-command", lambda: self.database('keyboard', 'Run command'))

        # Mouse actions
        self.add_action("mouse-click", lambda: self.database('mouse', 'Click mouse'))
        self.add_action("mouse-dclick", lambda: self.database('mouse', 'Doubleclick mouse'))
        self.add_action("mouse-tclick", lambda: self.database('mouse', 'Tripleclick mouse'))
        self.add_action("mouse-drag", lambda: self.database('mouse', 'Drag mouse'))
        self.add_action("mouse-pos", lambda: self.database('mouse', 'Set mouse location'))
        self.add_action("mouse-hide", lambda: self.database('mouse', 'Hide mouse'))

        # Variable actions
        self.add_action("var-read", lambda: self.database('variable', 'Read variable'))
        self.add_action("var-strict", lambda: self.database('variable', 'Read strict variable'))
        self.add_action("var-set", lambda: self.database('variable', 'Set variable'))
        self.add_action("var-check", lambda: self.database('variable', 'Check variable'))
        self.add_action("var-list", lambda: self.database('variable', 'Read variable as list'))
        self.add_action("var-check-list", lambda: self.database('variable', 'Check value in list of variables'))

        # Script actions
        self.add_action("script-assert", lambda: self.database('script', 'Run script and assert'))
        self.add_action("script-run", lambda: self.database('script', 'Run script'))
        self.add_action("script-bg", lambda: self.database('script', 'Run script in background'))
        self.add_action("script-sudo-assert", lambda: self.database('script', 'Run sudo script and assert'))
        self.add_action("script-sudo", lambda: self.database('script', 'Run sudo script'))
        self.add_action("script-output", lambda: self.database('script', 'Collect script output'))
        self.add_action("script-validate", lambda: self.database('script', 'Collect script output and validate'))
        self.add_action("script-serial", lambda: self.database('script', 'Check if terminal is serial'))
        self.add_action("script-wait", lambda: self.database('script', 'Wait for serial output'))
        self.add_action("script-file", lambda: self.database('script', 'Read test data from file'))
        self.add_action("script-temp", lambda: self.database('script', 'Save temp file'))
        self.add_action("script-root", lambda: self.database('script', 'Become root'))
        self.add_action("script-package", lambda: self.database('script', 'Make sure package is installed'))
        self.add_action("script-md5", lambda: self.database('script', 'Hash the string with MD5'))
        self.add_action("script-gui", lambda: self.database('script', 'Start GUI application'))

        # Log actions
        self.add_action("log-message", lambda: self.database('logs', 'Log a message'))
        self.add_action("log-upload", lambda: self.database('logs', 'Upload logs'))
        self.add_action("log-asset", lambda: self.database('logs', 'Upload asset'))

        # Helper actions
        self.add_action("helper-ip", lambda: self.database('helper', 'Get host ip'))
        self.add_action("helper-url", lambda: self.database('helper', 'Get base url'))
        self.add_action("helper-asset", lambda: self.database('helper', 'Get data asset url'))
        self.add_action("helper-compat", lambda: self.database('helper', 'Make arguments compatible'))
        self.add_action("helper-curl", lambda: self.database('helper', 'Show curl progress'))

        # Misc actions
        self.add_action("misc-power", lambda: self.database('misc', 'Send power signal'))
        self.add_action("misc-check", lambda: self.database('misc', 'Check machine shut down'))
        self.add_action("misc-assert", lambda: self.database('misc', 'Assert machine shut down'))
        self.add_action("misc-eject", lambda: self.database('misc', 'Eject machine CD'))
        self.add_action("misc-dump", lambda: self.database('misc', 'Save memory dump'))
        self.add_action("misc-storage", lambda: self.database('misc', 'Save storage drives'))
        self.add_action("misc-freeze", lambda: self.database('misc', 'Freeze the VM'))
        self.add_action("misc-resume", lambda: self.database('misc', 'Resume the VM'))
        self.add_action("misc-junit", lambda: self.database('misc', 'Parse junit log'))
        self.add_action("misc-extra", lambda: self.database('misc', 'Parse extra log'))

        # Perl actions
        self.add_action("perl-if", lambda: self.perl_snippets('if'))
        self.add_action("perl-ifelse", lambda: self.perl_snippets('if_else'))
        self.add_action("perl-ifelif", lambda: self.perl_snippets('if_elsif'))
        self.add_action("perl-for", lambda: self.perl_snippets('for'))
        self.add_action("perl-foreach", lambda: self.perl_snippets('foreach'))
        self.add_action("perl-var", lambda: self.perl_snippets('var'))
        self.add_action("perl-arg", lambda: self.perl_snippets('arg'))
        self.add_action("perl-args", lambda: self.perl_snippets('args'))
        self.add_action("perl-unless", lambda: self.perl_snippets('unless'))

        # VM actions
        self.add_action("vm-connect", lambda: self.show_connect_vm())
        self.add_action("vm-create", lambda: self.show_create_needle())
        self.add_action("vm-edit", lambda: self.edit_needle())

        # Help actions
        self.add_action("help", lambda: self.show_docs('help'))
        self.add_action("help-testapi", lambda: self.show_docs('testapi'))
        self.add_action("help-docs", lambda: self.show_docs('docs'))
        self.add_action("about", lambda: show_about(self.window))

    def add_action(self, name, callback):
        """Helper to add a simple action."""
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", lambda a, p: callback())
        self.app.add_action(action)

    def create_quick_menu(self, parent):
        """Create widgets for the Quick menu."""
        buttons_frame = Gtk.Frame()
        buttons_frame.set_label("Quick actions")
        buttons_frame.set_size_request(200, -1)

        buttons_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        buttons_box.set_margin_start(5)
        buttons_box.set_margin_end(5)
        buttons_box.set_margin_top(5)
        buttons_box.set_margin_bottom(5)
        buttons_frame.set_child(buttons_box)

        # Define buttons
        btn = Gtk.Button(label='Create file layout')
        btn.connect('clicked', lambda b: self.create_layout())
        buttons_box.append(btn)

        btn = Gtk.Button(label='Assert and click match')
        btn.connect('clicked', lambda b: self.database('video', 'Assert and click match'))
        buttons_box.append(btn)

        btn = Gtk.Button(label='Assert screen for match')
        btn.connect('clicked', lambda b: self.database('video', 'Assert screen for match'))
        buttons_box.append(btn)

        btn = Gtk.Button(label='Check screen for match')
        btn.connect('clicked', lambda b: self.database('video', 'Check screen for match'))
        buttons_box.append(btn)

        btn = Gtk.Button(label='Type text')
        btn.connect('clicked', lambda b: self.database('keyboard', 'Type text'))
        buttons_box.append(btn)

        btn = Gtk.Button(label='Type text safely (Fedora)')
        btn.connect('clicked', lambda b: self.database('keyboard', 'Type text safely'))
        buttons_box.append(btn)

        btn = Gtk.Button(label='Press key (combination)')
        btn.connect('clicked', lambda b: self.database('keyboard', 'Press key'))
        buttons_box.append(btn)

        btn = Gtk.Button(label='Wait until screen is still')
        btn.connect('clicked', lambda b: self.database('video', 'Wait until screen is still'))
        buttons_box.append(btn)

        btn = Gtk.Button(label='IF statement layout')
        btn.connect('clicked', lambda b: self.perl_snippets('if'))
        buttons_box.append(btn)

        btn = Gtk.Button(label='FOR statement layout')
        btn.connect('clicked', lambda b: self.perl_snippets('for'))
        buttons_box.append(btn)

        btn = Gtk.Button(label='Set test flags')
        btn.connect('clicked', lambda b: self.set_test_flags())
        buttons_box.append(btn)

        # Checkbuttons
        self.comments_check = Gtk.CheckButton(label="Include comments")
        self.comments_check.set_active(True)
        self.comments_check.connect('toggled', lambda b: self.toggle_comments())
        buttons_box.append(self.comments_check)

        self.args_check = Gtk.CheckButton(label="Include arguments")
        self.args_check.set_active(True)
        self.args_check.connect('toggled', lambda b: self.toggle_args())
        buttons_box.append(self.args_check)

        parent.append(buttons_frame)

    def toggle_comments(self):
        """Toggle comments option."""
        self.comments_on = self.comments_check.get_active()

    def toggle_args(self):
        """Toggle arguments option."""
        self.args_on = self.args_check.get_active()

    def create_text(self, parent):
        """Create the text widget with syntax highlighting."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_width(600)

        # Create source view with syntax highlighting
        self.text = GtkSource.View()
        self.text.set_wrap_mode(Gtk.WrapMode.NONE)
        self.text.set_monospace(True)
        self.text.set_show_line_numbers(True)
        self.text.set_highlight_current_line(True)
        self.text.set_auto_indent(True)
        self.text.set_indent_width(4)
        self.text.set_tab_width(4)

        # Set up syntax highlighting for Perl
        buffer = GtkSource.Buffer()
        lang_manager = GtkSource.LanguageManager.get_default()
        perl_lang = lang_manager.get_language('perl')
        if perl_lang:
            buffer.set_language(perl_lang)
            buffer.set_highlight_syntax(True)

        # Set color scheme
        style_manager = GtkSource.StyleSchemeManager.get_default()
        scheme = style_manager.get_scheme('classic')
        if scheme:
            buffer.set_style_scheme(scheme)

        self.text.set_buffer(buffer)

        # Connect text change signal
        buffer.connect('changed', self.on_text_changed)

        scrolled.set_child(self.text)
        parent.append(scrolled)

    def on_text_changed(self, buffer):
        """Handle text changes to update save status."""
        if self.is_saved:
            self.is_saved = False
            self.update_title('unsave')

    def on_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard shortcuts."""
        ctrl = state & Gdk.ModifierType.CONTROL_MASK

        if ctrl:
            if keyval == Gdk.KEY_q:
                self.close_application()
                return True
            elif keyval == Gdk.KEY_s:
                self.save_file()
                return True
            elif keyval == Gdk.KEY_n:
                self.new_file()
                return True
            elif keyval == Gdk.KEY_o:
                self.open_file()
                return True
            elif keyval == Gdk.KEY_a:
                self.select_all()
                return True
        elif keyval == Gdk.KEY_F1:
            self.show_docs('help')
            return True

        return False

    def on_close_request(self, window):
        """Handle window close request."""
        if not self.is_saved:
            dialog = Gtk.AlertDialog()
            dialog.set_message("File not saved")
            dialog.set_detail("The current file has not been saved yet. Do you still want to close the file?")
            dialog.set_buttons(["Cancel", "Close Anyway"])
            dialog.set_cancel_button(0)
            dialog.set_default_button(0)
            dialog.choose(window, None, self.on_close_confirm)
            return True  # Prevent closing
        return False  # Allow closing

    def on_close_confirm(self, dialog, result):
        """Handle close confirmation dialog response."""
        try:
            response = dialog.choose_finish(result)
            if response == 1:  # Close Anyway
                self.window.destroy()
        except:
            pass

    def run(self):
        """Run the application"""
        self.app.run(None)

    def close_application(self):
        """Close the application properly."""
        if not self.is_saved:
            dialog = Gtk.AlertDialog()
            dialog.set_message("File not saved")
            dialog.set_detail("The current file has not been saved yet. Do you still want to close the file?")
            dialog.set_buttons(["Cancel", "Close Anyway"])
            dialog.set_cancel_button(0)
            dialog.set_default_button(0)
            dialog.choose(self.window, None, self.on_close_confirm)
        else:
            self.window.destroy()

    def update_title(self, status):
        """Update the window title to reflect save status."""
        s = "*" if status == 'unsave' else ""

        if not self.filetosave:
            base = ""
        else:
            base = os.path.basename(self.filetosave)

        self.window.set_title(f"{s} {base} - {self.appname}")

    def put_into_text(self, text):
        """Insert text at cursor position."""
        buffer = self.text.get_buffer()
        buffer.insert_at_cursor(text)
        self.is_saved = False
        self.update_title('unsave')

    def database(self, family, record):
        """Get a snippet from the testapi database."""
        chapter = self.db[family]
        data = None

        for c in chapter:
            if c.name == record:
                data = c

        if data and not self.comments_on and not self.args_on:
            self.put_into_text(data.display_command())
        elif data and not self.args_on:
            self.put_into_text(data.describe())
            self.put_into_text(data.display_command())
        elif data and not self.comments_on:
            self.put_into_text(data.display_syntax())
        elif data:
            self.put_into_text(data.all())
        else:
            self.show_error("Unknown request",
                          "It seems that a menu item or a keyboard shortcut require a non-existing snippet. Please, report a bug.")

    def perl_snippets(self, snippet):
        """Return a perl snippet."""
        snippets = {
            'if': "if (condition) {\n   # Put some code here;\n}\n",
            'unless': "unless (condition) {\n   # Put some code here;\n}\n",
            'if_else': "if (condition) {\n   # Put some code here;\n}\nelse {\n    # Some alternative code;\n}\n",
            'if_elsif': "if (condition) {\n   # Put some code here;\n}\nelsif (other condition) {\n    # Some alternative code;\n}\nelse {\n    # Fallback code;\n}\n",
            'for': "for my $i (@array) {\n    # Put some code here;\n}\n",
            'foreach': "foreach (@array) {\n    # Put some code here;\n}\n",
            'var': 'my $variable = value;\n',
            'arg': "my $variable = shift;\n",
            'args': "my ($var1, $var2, ...) = @_;\n"
        }

        if snippet in snippets:
            self.put_into_text(snippets[snippet])
        else:
            self.show_error('Unknown request',
                          'It seems that a menu item or a keyboard shortcut calls for a non-existing snippet. Please, report a bug.')

    def set_test_flags(self):
        """Insert test flag snippet."""
        lines = [
            'sub test_flags {',
            '    return {fatal => 0, ignore_failure => 0, milestone => 0, no_rollback => 0, always_rollback => 0};',
            '}'
        ]
        snippet = '\n'.join(lines)
        self.put_into_text(snippet)

    def create_layout(self):
        """Insert the file layout."""
        lines = [
            'use base "installedtest";',
            'use strict;',
            'use testapi;',
            'use utils;',
            '',
            'sub run {',
            '',
            '',
            '}'
        ]
        snippet = '\n'.join(lines)
        self.put_into_text(snippet)

    def open_file(self, filename=None):
        """Open a file."""
        if not self.is_saved:
            dialog = Gtk.AlertDialog()
            dialog.set_message("File not saved")
            dialog.set_detail("The file has not been saved yet, do you want to open another file?")
            dialog.set_buttons(["Cancel", "Open Anyway"])
            dialog.set_cancel_button(0)
            dialog.set_default_button(0)
            dialog.choose(self.window, None, lambda d, r: self.on_open_confirm(d, r, filename))
            return

        self.do_open_file(filename)

    def on_open_confirm(self, dialog, result, filename):
        """Handle open file confirmation."""
        try:
            response = dialog.choose_finish(result)
            if response == 1:  # Open Anyway
                self.do_open_file(filename)
        except:
            pass

    def do_open_file(self, filename=None):
        """Actually open the file."""
        if not filename:
            file_dialog = Gtk.FileDialog()
            file_filter = Gtk.FileFilter()
            file_filter.set_name("openQA script")
            file_filter.add_pattern("*.pm")
            filters = Gio.ListStore.new(Gtk.FileFilter)
            filters.append(file_filter)
            file_dialog.set_filters(filters)
            file_dialog.open(self.window, None, self.on_file_open_response)
        else:
            self.load_file(filename)

    def on_file_open_response(self, dialog, result):
        """Handle file dialog response."""
        try:
            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                self.load_file(path)
        except:
            pass

    def load_file(self, filepath):
        """Load file content into text widget."""
        self.filetosave = os.path.abspath(filepath)

        try:
            with open(self.filetosave, 'r') as inputfile:
                data = inputfile.read()

            buffer = self.text.get_buffer()
            buffer.set_text(data)

            self.is_saved = True
            self.update_title('save')
        except Exception as e:
            self.show_error("Error opening file", str(e))

    def save_file(self):
        """Save the file."""
        if not self.filetosave:
            self.save_as_file()
        else:
            self.do_save_file(self.filetosave)

    def save_as_file(self):
        """Save as dialog."""
        file_dialog = Gtk.FileDialog()
        file_filter = Gtk.FileFilter()
        file_filter.set_name("openQA script")
        file_filter.add_pattern("*.pm")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(file_filter)
        file_dialog.set_filters(filters)
        file_dialog.save(self.window, None, self.on_file_save_response)

    def on_file_save_response(self, dialog, result):
        """Handle save dialog response."""
        try:
            file = dialog.save_finish(result)
            if file:
                path = file.get_path()
                self.do_save_file(path)
        except:
            pass

    def do_save_file(self, filepath):
        """Actually save the file."""
        try:
            buffer = self.text.get_buffer()
            start = buffer.get_start_iter()
            end = buffer.get_end_iter()
            data = buffer.get_text(start, end, False)

            with open(filepath, 'w') as outputfile:
                outputfile.write(data)

            self.filetosave = filepath
            self.is_saved = True
            self.update_title('save')
        except Exception as e:
            self.show_error("Error saving file", str(e))

    def new_file(self):
        """Create a new file."""
        if not self.is_saved:
            dialog = Gtk.AlertDialog()
            dialog.set_message("File not saved")
            dialog.set_detail("The file has not been saved yet, do you still want to open new file?")
            dialog.set_buttons(["Cancel", "New File"])
            dialog.set_cancel_button(0)
            dialog.set_default_button(0)
            dialog.choose(self.window, None, self.on_new_confirm)
            return

        self.do_new_file()

    def on_new_confirm(self, dialog, result):
        """Handle new file confirmation."""
        try:
            response = dialog.choose_finish(result)
            if response == 1:  # New File
                self.do_new_file()
        except:
            pass

    def do_new_file(self):
        """Actually create new file."""
        buffer = self.text.get_buffer()
        buffer.set_text("")
        self.filetosave = None
        self.is_saved = True
        self.window.set_title(self.appname)

    def select_all(self):
        """Select all text."""
        buffer = self.text.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        buffer.select_range(start, end)

    def show_docs(self, doctype):
        """Open external web resources."""
        urls = {
            'testapi': 'http://open.qa/api/testapi/',
            'docs': 'http://open.qa/documentation/',
            'help': 'https://lruzicka.github.io/chancery/'
        }

        if doctype in urls:
            webbrowser.open_new(urls[doctype])

    def show_connect_vm(self):
        """Show dialog to connect to a VM."""
        dialog = Gtk.Window()
        dialog.set_title('Connect to a VM')
        dialog.set_transient_for(self.window)
        dialog.set_modal(True)
        dialog.set_default_size(300, 150)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        dialog.set_child(box)

        label = Gtk.Label(label='Choose a VM:')
        box.append(label)

        # Get domain names from KVM
        domains = []
        try:
            self.kvm = libvirt.open("qemu:///session")
            domains = [x.name() for x in self.kvm.listAllDomains()]
            if len(domains) == 0:
                self.show_error("No domains found",
                              "Either the hypervisor is not running or no VMs available in the qemu:///session.")
                domains = ["No VMs available"]
        except libvirt.libvirtError:
            self.show_error("Error", "Failed to open connection to the hypervisor.")
            domains = ["No VMs available"]

        combo = Gtk.DropDown.new_from_strings(domains if domains else ["No VMs available"])
        combo.set_selected(0)
        box.append(combo)

        connect_btn = Gtk.Button(label="Connect")
        connect_btn.connect('clicked', lambda b: self.connect_vm(combo, dialog, domains))
        box.append(connect_btn)

        dialog.present()

    def connect_vm(self, combo, dialog, domains):
        """Connect to selected VM."""
        selected_index = combo.get_selected()
        if selected_index < len(domains):
            selected = domains[selected_index]
            if selected != "No VMs available":
                self.virtual_machine = selected
                dialog.close()
                self.show_info("Connected successfully",
                             f"The application is now able to take pictures from the {selected} virtual machine.")
                return

        self.show_error("No VM selected", "Please, select one of the available VMs.")

    def show_create_needle(self):
        """Show dialog to create a needle."""
        if not self.filetosave:
            self.show_error("File not saved", "Save the file before you attempt to create needles.")
            return

        dialog = Gtk.Window()
        dialog.set_title('Take a VM screenshot')
        dialog.set_transient_for(self.window)
        dialog.set_modal(True)
        dialog.set_default_size(300, 120)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        dialog.set_child(box)

        label = Gtk.Label(label='Set the primary tag:')
        box.append(label)

        entry = Gtk.Entry()
        entry.set_size_request(250, -1)
        box.append(entry)

        btn = Gtk.Button(label="Create needle")
        btn.connect('clicked', lambda b: self.create_needle(entry, dialog))
        box.append(btn)

        dialog.present()

    def create_needle(self, entry, dialog):
        """Create a needle from VM screenshot."""
        needlename = entry.get_text()
        if not needlename:
            self.show_error("Error", "Please provide a tag name.")
            return

        path = f"{os.path.dirname(self.filetosave)}/{needlename}"
        self.latest_needle_taken = path

        try:
            screen = take_screenshot(self.virtual_machine, self.kvm, path)
            dialog.close()
            self.put_into_text(f'"{needlename}"')
        except Exception as e:
            self.show_error("Error taking screenshot", str(e))

    def edit_needle(self):
        """Edit the last taken needle."""
        if self.latest_needle_taken:
            screenshot = f"{self.latest_needle_taken}.png"
            subprocess.run(["needly", screenshot])
        else:
            self.show_error("No needle available", "Create a needle first before editing.")

    def show_error(self, title, message):
        """Show error dialog."""
        dialog = Gtk.AlertDialog()
        dialog.set_message(title)
        dialog.set_detail(message)
        dialog.show(self.window)

    def show_info(self, title, message):
        """Show info dialog."""
        dialog = Gtk.AlertDialog()
        dialog.set_message(title)
        dialog.set_detail(message)
        dialog.show(self.window)


def show_about(parent_window):
    """Display the About window."""
    dialog = Gtk.AboutDialog()
    dialog.set_transient_for(parent_window)
    dialog.set_modal(True)
    dialog.set_program_name("Chancery")
    dialog.set_version("0.9")
    dialog.set_comments(
        "a basic text editor with pre-created openQA snippets that enables "
        "developing openQA test scripts more rapidly."
    )
    dialog.set_license_type(Gtk.License.GPL_2_0)
    dialog.set_authors(["Lukáš Růžička <lruzicka@redhat.com>"])
    dialog.set_copyright("Copyright © 2022 Red Hat")
    dialog.set_website("https://lruzicka.github.io/chancery/")
    dialog.present()


def take_screenshot(virtual_machine, hypervisor, tagfilename="screenshot.png"):
    """Take screenshot from running virtual machine."""
    if not virtual_machine or not hypervisor:
        raise Exception("No VM connected")

    domain = hypervisor.lookupByName(virtual_machine)
    stream = hypervisor.newStream()
    image_type = domain.screenshot(stream, 0)

    image_data = io.BytesIO()
    part_stream = stream.recv(8192)
    while part_stream != b'':
        image_data.write(part_stream)
        part_stream = stream.recv(8192)

    image_data.seek(0)
    image = Image.open(image_data)
    save_as_name = f"{tagfilename}.png"
    image.save(save_as_name, 'PNG')
    image_data.close()
    stream.finish()

    path = os.path.join(os.path.abspath('.'), save_as_name)
    return path


def main():
    try:
        filename = sys.argv[1]
    except IndexError:
        filename = None

    app = Application(filename=filename)
    app.run()


if __name__ == '__main__':
    main()
