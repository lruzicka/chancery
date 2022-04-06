#!/usr/bin/python3

import io
import json
import libvirt
import os
import multiprocessing
import re
import sys
import subprocess
import webbrowser
import idlelib.colorizer as colorizer
from idlelib.percolator import Percolator as percolator
from needly import needly
from tkinter import *
from tkinter import ttk
from tkinter import scrolledtext, filedialog, messagebox, font
from chancery.testapi import Definition as df
from chancery.testapi import testAPI as api
from chancery.needler import Application as needler
from PIL import Image

class Application:
    def __init__(self, master=None, filename=None):
        # Set up the main application window
        self.toplevel = Tk() if master is None else Toplevel(master)
        # Configure rows and columns for resizing
        self.toplevel.rowconfigure(0, weight=1)
        self.toplevel.columnconfigure(0, weight=1)
        # Do not tear off menus.
        self.toplevel.option_add('*tearOff', FALSE)
        self.toplevel.configure(takefocus=False)
        self.toplevel.protocol("WM_DELETE_WINDOW", self.close_application)
        # Set the appname and update the application title
        self.appname = "Chancery - an openQA script editor"
        self.toplevel.title(self.appname)
        # Configure the main application frame
        self.mainframe = ttk.Frame(self.toplevel)
        self.mainframe.configure(borderwidth='2', relief='ridge', takefocus=True)
        self.mainframe.rowconfigure(0, weight=1)
        self.mainframe.columnconfigure(0, weight=1)
        self.mainframe.columnconfigure(1, weight=5)
        self.mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        # Set up status variables
        self.db = api.show_definitions() # Snippets from the testapi database
        self.filetosave = None # A filename to save the content into.
        self.is_saved = True # If the file is saved
        self.comments_on = IntVar() # Comments are switched on
        self.args_on = IntVar() # Arguments are switched on
        self.kvm = None # Connection to KVM
        self.virtual_machine = None # Holds the name of the connected virtual machine.
        self.latest_needle_taken = None

        # Set up the Syntax Highlighting
        self.scheme = colorizer.ColorDelegator()
        self.pattern = colorizer.make_pat().pattern
        self.scheme.tagdefs['COMMANDS'] = {'foreground': 'blue', 'background': 'white'}
        self.scheme.tagdefs['COMMENT'] = {'foreground': 'grey', 'background': 'white'}
        self.scheme.tagdefs['KEYWORD'] = {'foreground': 'red', 'background': 'white'}
        self.scheme.tagdefs['PERL'] = {'foreground': 'red', 'background': 'white'}
        self.scheme.tagdefs['BUILTIN'] = {'foreground': 'orange', 'background': 'white'}
        self.scheme.tagdefs['STRING'] = {'foreground': 'green', 'background': 'white'}
        self.scheme.tagdefs['DEFINITION'] = {'foreground': 'yellow', 'background': 'white'}

        # Run the construction methods to build the UI
        self.create_menu_bar()
        self.create_quick_menu()
        self.create_text()
        self.bind_accelerators()

        if filename:
            self.open_file(filename)

    def create_menu_bar(self):
        """ Creates the application menu """
        self.menubar = Menu(self.toplevel)
        self.menu_file = Menu(self.menubar)
        # Create the File submenu.
        self.menubar.add_cascade(menu=self.menu_file, label='File')
        self.menu_file.add_command(label='New', accelerator='Ctrl-N', command=self.new_file)
        self.menu_file.add_command(label='Open', accelerator='Ctrl-O', command=self.open_file)
        self.menu_file.add_separator()
        self.menu_file.add_command(label='Save', accelerator='Ctrl-S', command=self.save_file)
        self.menu_file.add_command(label='Save As', command=self.save_as_file)
        self.menu_file.add_separator()
        self.menu_file.add_command(label='Exit', accelerator='Ctrl-Q', command=self.close_application)
        # Create the Video submenu
        self.menu_video = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_video, label='Video')
        self.menu_video.add_command(label="Assert and click match", accelerator="Alt-V-C", command=lambda: self.database('video', 'Assert and click match'))
        self.menu_video.add_command(label="Assert and doubleclick match", accelerator="Alt-V-D", command=lambda: self.database('video', 'Assert and doubleclick match'))
        self.menu_video.add_command(label="Click last match", accelerator="Alt-V-L", command=lambda: self.database('video', 'Click last match'))
        self.menu_video.add_separator()
        self.menu_video.add_command(label="Assert screen for match", accelerator="Alt-V-M", command=lambda: self.database('video', 'Assert screen for match'))
        self.menu_video.add_command(label="Check screen for match", accelerator="Alt-V-H", command=lambda: self.database('video', 'Check screen for match'))
        self.menu_video.add_command(label="Check if match has tag", accelerator="Alt-V-G", command=lambda: self.database('video', 'Check if match has tag'))
        self.menu_video.add_command(label="Assert that screen is still", accelerator="Alt-V-Q", command=lambda: self.database('video', 'Assert that screen is still'))
        self.menu_video.add_command(label="Assert that screen changes", accelerator="Alt-V-A", command=lambda: self.database('video', 'Assert that screen changes'))
        self.menu_video.add_command(label="Wait if screen changes", accelerator="Alt-V-E", command=lambda: self.database('video', 'Wait if screen changes'))
        self.menu_video.add_command(label="Wait until screen is still", accelerator="Alt-V-W", command=lambda: self.database('video','Wait until screen is still'))
        self.menu_video.add_separator()
        self.menu_video.add_command(label="Force soft failure", accelerator="Alt-V-U", command=lambda: self.database('video', 'Force soft failure'))
        self.menu_video.add_command(label="Record soft failure", accelerator="Alt-V-F", command=lambda: self.database('video','Record soft failure'))
        self.menu_video.add_command(label="Record info", accelerator="Alt-V-I", command=lambda: self.database('video','Record info'))
        self.menu_video.add_command(label="Take screenshot", accelerator="Alt-V-T", command=lambda: self.database('video', 'Take screenshot'))
        # Create the Audio submenu
        self.menu_audio = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_audio,label='Audio')
        self.menu_audio.add_command(label="Start audio recording", accelerator="Alt-A-R", command=lambda: self.database('audio', 'Start audio recording'))
        self.menu_audio.add_command(label="Assert recorded sound", accelerator="Alt-A-S", command=lambda: self.database('audio', 'Assert recorded sound'))
        self.menu_audio.add_command(label="Check recorded sound", accelerator="Alt-A-C", command=lambda: self.database('audio', 'Check recorded sound'))
        # Create the Keyboard submenu
        self.menu_keyboard = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_keyboard,label='Keyboard')
        self.menu_keyboard.add_command(label="Press key (combination)", accelerator="Alt-K-P", command=lambda: self.database('keyboard', 'Press key'))
        self.menu_keyboard.add_command(label="Hold key", accelerator="Alt-K-H", command=lambda: self.database('keyboard', 'Hold key'))
        self.menu_keyboard.add_command(label="Release key", accelerator="Alt-K-R", command=lambda: self.database('keyboard', 'Release key'))
        self.menu_keyboard.add_command(label="Press key until event", accelerator="Alt-K-E", command=lambda: self.database('keyboard', 'Press key until event'))
        self.menu_keyboard.add_separator()
        self.menu_keyboard.add_command(label="Type text", accelerator="Alt-K-T", command=lambda: self.database('keyboard', 'Type text'))
        self.menu_keyboard.add_command(label="Type text safely (Fedora)", accelerator="Alt-K-S", command=lambda: self.database('keyboard', 'Type text safely'))
        self.menu_keyboard.add_command(label="Type password", accelerator="Alt-K-W", command=lambda: self.database('keyboard', 'Type password'))
        self.menu_keyboard.add_command(label="Run command", accelerator="Alt-K-C", command=lambda: self.database('keyboard', 'Run command'))

        # Create the Mouse submenu
        self.menu_mouse = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_mouse,label='Mouse')
        self.menu_mouse.add_command(label="Click mouse at location", accelerator="Alt-M-C", command=lambda: self.database('mouse', 'Click mouse'))
        self.menu_mouse.add_command(label="Doubleclick mouse at location", accelerator="Alt-M-D", command=lambda: self.database('mouse', 'Doubleclick mouse'))
        self.menu_mouse.add_command(label="Tripleclick mouse at location", accelerator="Alt-M-T", command=lambda: self.database('mouse', 'Tripleclick mouse'))
        self.menu_mouse.add_command(label="Drag with mouse", accelerator="Alt-M-R", command=lambda: self.database('mouse', 'Drag mouse'))
        self.menu_mouse.add_separator()
        self.menu_mouse.add_command(label="Set mouse location", accelerator="Alt-M-P", command=lambda: self.database('mouse', 'Set mouse location'))
        self.menu_mouse.add_command(label="Hide mouse cursor", accelerator="Alt-M-H", command=lambda: self.database('mouse', 'Hide mouse'))
        
        # Create the Variable submenu
        self.menu_variable = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_variable,label='Variables')
        self.menu_variable.add_command(label="Read variable", accelerator="Alt-R-G", command=lambda: self.database('variable', 'Read variable'))
        self.menu_variable.add_command(label="Read variable (strict)", accelerator="Alt-R-D", command=lambda: self.database('variable', 'Read strict variable'))
        self.menu_variable.add_command(label="Set variable", accelerator="Alt-R-S", command=lambda: self.database('variable', 'Set variable'))
        self.menu_variable.add_command(label="Check variable value", accelerator="Alt-R-C", command=lambda: self.database('variable', 'Check variable'))
        self.menu_variable.add_command(label="Read variable as list", accelerator="Alt-R-L", command=lambda: self.database('variable', 'Read variable as list'))
        self.menu_variable.add_command(label="Check value in list of variables", accelerator="Alt-R-O", command=lambda: self.database('variable', 'Check value in list of variables'))
        
        # Create the Script submenu
        self.menu_script = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_script,label='Scripts')
        self.menu_script.add_command(label="Run script and assert", accelerator="Alt-S-A", command=lambda: self.database('script', 'Run script and assert'))
        self.menu_script.add_command(label="Run script", accelerator="Alt-S-R", command=lambda: self.database('script', 'Run script'))
        self.menu_script.add_command(label="Run script in background", accelerator="Alt-S-B", command=lambda: self.database('script', 'Run script in background'))
        self.menu_script.add_command(label="Run sudo script and assert", accelerator="Alt-S-U", command=lambda: self.database('script', 'Run sudo script and assert'))
        self.menu_script.add_command(label="Run sudo script", accelerator="Alt-S-D", command=lambda: self.database('script', 'Run sudo script'))
        self.menu_script.add_command(label="Collect script output", accelerator="Alt-S-C", command=lambda: self.database('script', 'Collect script output'))
        self.menu_script.add_command(label="Collect script output and validate", accelerator="Alt-S-V", command=lambda: self.database('script', 'Collect script output and validate'))
        self.menu_script.add_command(label="Check if terminal is serial", accelerator="Alt-S-T", command=lambda: self.database('script', 'Check if terminal is serial'))
        self.menu_script.add_command(label="Wait for serial output", accelerator="Alt-S-W", command=lambda: self.database('script', 'Wait for serial output'))
        self.menu_script.add_separator()
        self.menu_script.add_command(label="Read test data from file", accelerator="Alt-S-F", command=lambda: self.database('script', 'Read test data from file'))
        self.menu_script.add_command(label="Save temp file", accelerator="Alt-S-E", command=lambda: self.database('script', 'Save temp file'))
        self.menu_script.add_command(label="Become root", accelerator="Alt-S-O", command=lambda: self.database('script', 'Become root'))
        self.menu_script.add_command(label="Make sure package is installed", accelerator="Alt-S-I", command=lambda: self.database('script', 'Make sure package is installed'))
        self.menu_script.add_command(label="Hash the string with MD5", accelerator="Alt-S-M", command=lambda: self.database('script', 'Hash the string with MD5'))
        self.menu_script.add_separator()
        self.menu_script.add_command(label="Start GUI application", accelerator="Alt-S-X", command=lambda: self.database('script', 'Start GUI application'))
        
        # Create the Log submenu
        self.menu_log = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_log,label='Logs')
        self.menu_log.add_command(label="Log a diagnostic message", accelerator="Alt-L-M", command=lambda: self.database('logs', 'Log a message'))
        self.menu_log.add_command(label="Upload logs", accelerator="Alt-L-U", command=lambda: self.database('logs', 'Upload logs'))
        self.menu_log.add_command(label="Upload asset", accelerator="Alt-L-A", command=lambda: self.database('logs', 'Upload asset'))
        
        # Create the Helpers submenu
        self.menu_helpers = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_helpers,label='Helpers')
        self.menu_helpers.add_command(label="Get host's IP address", accelerator="Alt-H-I", command=lambda: self.database('helper', 'Get host ip'))
        self.menu_helpers.add_command(label="Get the base URL of local os-autoinst", accelerator="Alt-H-U", command=lambda: self.database('helper', 'Get base url'))
        self.menu_helpers.add_command(label="Get the data asset URL", accelerator="Alt-H-D", command=lambda: self.database('helper', 'Get data asset url'))
        self.menu_helpers.add_command(label="Make arguments compatible", accelerator="Alt-H-C", command=lambda: self.database('helper', 'Make arguments compatible'))
        self.menu_helpers.add_command(label="Show Curl progress meter", accelerator="Alt-H-P", command=lambda: self.database('helper', 'Show curl progress'))
        
        # Create the Misc submenu
        self.menu_misc = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_misc,label='Misc')
        self.menu_misc.add_command(label="Send power signal to machine", accelerator="Alt-M-P", command=lambda: self.database('misc', 'Send power signal'))
        self.menu_misc.add_command(label="Check machine shut down", accelerator="Alt-M-C", command=lambda: self.database('misc', 'Check machine shut down'))
        self.menu_misc.add_command(label="Assert machine shut down", accelerator="Alt-M-A", command=lambda: self.database('misc', 'Assert machine shut down'))
        self.menu_misc.add_command(label="Eject machine CD", accelerator="Alt-M-E", command=lambda: self.database('misc', 'Eject machine CD'))
        self.menu_misc.add_command(label="Save memory dump", accelerator="Alt-M-D", command=lambda: self.database('misc', 'Save memory dump'))
        self.menu_misc.add_command(label="Save storage drives", accelerator="Alt-M-S", command=lambda: self.database('misc', 'Save storage drives'))
        self.menu_misc.add_command(label="Freeze the VM", accelerator="Alt-M-F", command=lambda: self.database('misc', 'Freeze the VM'))
        self.menu_misc.add_command(label="Resume the VM", accelerator="Alt-M-R", command=lambda: self.database('misc', 'Resume the VM'))
        self.menu_misc.add_command(label="Parse jUnit log", accelerator="Alt-M-J", command=lambda: self.database('misc', 'Parse junit log'))
        self.menu_misc.add_command(label="Parse extra log", accelerator="Alt-M-L", command=lambda: self.database('misc', 'Parse extra log'))
        
        # Create the Perl submenu
        self.menu_perl = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_perl,label='Perl')
        self.menu_perl.add_command(label="IF clause", accelerator="Alt-P-I", command=lambda: self.perl_snippets('if'))
        self.menu_perl.add_command(label="IF ELSE clause", accelerator="Alt-P-E", command=lambda: self.perl_snippets('if_else'))
        self.menu_perl.add_command(label="IF ELSIF ELSE clause", accelerator="Alt-P-L", command=lambda: self.perl_snippets('if_elsif'))
        self.menu_perl.add_command(label="FOR clause", accelerator="Alt-P-F", command=lambda: self.perl_snippets('for'))
        self.menu_perl.add_command(label="FOREACH clause", accelerator="Alt-P-C", command=lambda: self.perl_snippets('foreach'))
        self.menu_perl.add_command(label="Assign VAR", accelerator="Alt-P-V", command=lambda: self.perl_snippets('var'))
        self.menu_perl.add_command(label="SUB take single argument", accelerator="Alt-P-R", command=lambda: self.perl_snippets('arg'))
        self.menu_perl.add_command(label="SUB take multiple arguments", accelerator="Alt-P-M", command=lambda: self.perl_snippets('args'))
        self.menu_perl.add_command(label="UNLESS clause", accelerator="Alt-P-U", command=lambda: self.perl_snippets('unless'))
        
        # Create the Virtual submenu
        self.menu_vm = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_vm, label='VirtMachine')
        self.menu_vm.add_command(label="Connect to VM", accelerator="Alt-X-C", command=lambda: self.show_connect_vm())
        self.menu_vm.add_command(label="Create needle", accelerator="Alt-X-T", command=lambda: self.show_create_needle()) 
        self.menu_vm.add_command(label="Edit needle", accelerator="Alt-X-E", command=lambda: self.edit_needle())

        # Create the Help
        self.menu_help = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_help,label='Help')
        self.menu_help.add_command(label="Help", accelerator="F1", command=lambda: self.show_docs('help'))
        self.menu_help.add_command(label="openQA TestApi Documentation", command=lambda: self.show_docs('testapi'))
        self.menu_help.add_command(label="openQA Documentation", command=lambda: self.show_docs('docs'))
        self.menu_help.add_separator()
        self.menu_help.add_command(label="About", command=lambda: show_about(self.toplevel))
         
        # Register the menubar with the main application
        self.toplevel['menu'] = self.menubar

    def create_quick_menu(self):
        """ Create widgets for the Quick menu. """
        self.buttons = ttk.Labelframe(self.mainframe, text="Quick actions")
        self.buttons.grid(column=0, row=0, sticky=(N,S,E,W), ipady=5)
        # Configure rows for the application to scale.
        self.buttons.rowconfigure(0, weight=2)
        self.buttons.rowconfigure(1, weight=1)
        self.buttons.rowconfigure(2, weight=1)
        self.buttons.rowconfigure(3, weight=1)
        self.buttons.rowconfigure(4, weight=1)
        self.buttons.rowconfigure(5, weight=1)
        self.buttons.rowconfigure(6, weight=1)
        self.buttons.rowconfigure(7, weight=1)
        self.buttons.rowconfigure(8, weight=1)
        self.buttons.rowconfigure(9, weight=1)
        self.buttons.rowconfigure(10, weight=1)
        self.buttons.rowconfigure(11, weight=1)
        self.buttons.rowconfigure(12, weight=1)
        self.buttons.columnconfigure(0, weight=1)

        # Define buttons
        self.skel_button = ttk.Button(self.buttons, text='Create file layout', command=self.create_layout)
        self.skel_button.grid(column=0, row=1, sticky=(N,S,E,W), pady='1')

        self.aclick_button = ttk.Button(self.buttons, text='Assert and click match', command=lambda: self.database('video', 'Assert and click match'))
        self.aclick_button.grid(column=0, row=2, sticky=(N,S,E,W), pady='1')

        self.ascreen_button = ttk.Button(self.buttons, text='Assert screen for match', command=lambda: self.database('video', 'Assert screen for match'))
        self.ascreen_button.grid(column=0, row=3, sticky=(N,S,E,W), pady='1')

        self.check_button = ttk.Button(self.buttons, text='Check screen for match', command=lambda: self.database('video', 'Check screen for match'))
        self.check_button.grid(column=0, row=4, sticky=(N,S,E,W), pady='1')

        self.type_button = ttk.Button(self.buttons, text='Type text', command=lambda: self.database('keyboard', 'Type text'))
        self.type_button.grid(column=0, row=5, sticky=(N,S,E,W), pady='1')

        self.stype_button = ttk.Button(self.buttons, text='Type text safely (Fedora)', command=lambda: self.database('keyboard', 'Type text safely'))
        self.stype_button.grid(column=0, row=6, sticky=(N,S,E,W), pady='1')

        self.press_button = ttk.Button(self.buttons, text='Press key (combination)', command=lambda: self.database('keyboard', 'Press key'))
        self.press_button.grid(column=0, row=7, sticky=(N,S,E,W), pady='1')

        self.wait_button = ttk.Button(self.buttons, text='Wait until screen is still', command=lambda: self.database('video', 'Wait until screen is still'))
        self.wait_button.grid(column=0, row=8, sticky=(N,S,E,W), pady='1')

        self.if_button = ttk.Button(self.buttons, text='IF statement layout', command=lambda: self.perl_snippets('if'))
        self.if_button.grid(column=0, row=9, sticky=(N,S,E,W), pady='1')

        self.for_button = ttk.Button(self.buttons, text='FOR statement layout', command=lambda: self.perl_snippets('for'))
        self.for_button.grid(column=0, row=10, sticky=(N,S,E,W), pady='1')

        self.flags_button = ttk.Button(self.buttons, text='Set test flags', command=self.set_test_flags)
        self.flags_button.grid(column=0, row=11, sticky=(N,S,E,W), pady='1')

        self.comments = ttk.Checkbutton(self.buttons, text="Include comments", variable=self.comments_on, onvalue=1, offvalue=0)
        self.comments.grid(column=0, row=12, sticky=(N,S,E,W), pady='1')
        self.comments_on.set(True)

        self.args = ttk.Checkbutton(self.buttons, text="Include arguments", variable=self.args_on, onvalue=1, offvalue=0)
        self.args.grid(column=0, row=13, sticky=(N,S,E,W), pady='1')
        self.args_on.set(True)
    

    def regex_api_commands(self):
        """ Walk over the database and pick commands to list
        the into the tag database for syntax highlighting. """
        # Iterate over all openqa commands in the test api 
        # and add them to the lexer.
        commands = []
        for family in self.db:
            for name in self.db[family]:
                commands.append(name.command)
        begin = r'\b(?P<COMMANDS>'
        end = r')\b|'
        mid = '|'.join(commands)
        # Also add selected Perl keywords because the lexer is based
        # on Python and therefore lacks the Perl stuff.
        # If more Perl keyboards should be recognized, they can be added here.
        # Alternatively, there might be some external tool to cover in one 
        # of the future versions.
        perl = r'\b(?P<PERL>sub|use|my|run|unless|until|qx|qw|qr|qq|no|ne|foreach|elsif)\b|'
        return begin + mid + end + perl
            

    def colorize(self):
        """ Update the lexer database with new items. """
        # Take the regex expression needed to be added and add it to the scheme.
        openqa_keywords = self.regex_api_commands()
        self.scheme.prog = re.compile(openqa_keywords + self.pattern, re.S)
        self.scheme.idprog = re.compile(r'\s+(\w+)', re.S)
        
    def create_text(self):
        """ Create the text widget. """
        self.text = scrolledtext.ScrolledText(self.mainframe)
        fnt = font.Font(font=self.text['font'])
        tab_size = fnt.measure('    ')
        self.text.configure(height='20', maxundo='100', width='120', tabs=tab_size)
        self.text.grid(column='1', row='0', sticky='nsew')
        # Add Syntax highlighting to the text widget
        self.colorize()
        percolator(self.text).insertfilter(self.scheme)

    def bind_accelerators(self):
        """ Bind accelerators (shortcuts) to the main application. """
        # Accelerators for the Video menu items.
        self.toplevel.bind("<Alt-v><c>", lambda x: self.database('video', 'Assert and click match'))
        self.toplevel.bind("<Alt-v><d>", lambda x: self.database('video', 'Assert and doubleclick match'))
        self.toplevel.bind("<Alt-v><m>", lambda x: self.database('video', 'Assert screen for match'))
        self.toplevel.bind("<Alt-v><h>", lambda x: self.database('video', 'Check screen for match'))
        self.toplevel.bind("<Alt-v><w>", lambda x: self.database('video', 'Wait until screen is still'))
        self.toplevel.bind("<Alt-v><f>", lambda x: self.database('video','Record soft failure'))
        self.toplevel.bind("<Alt-v><l>", lambda x: self.database('video','Click last match'))
        self.toplevel.bind("<Alt-v><g>", lambda x: self.database('video','Check if match has tag'))
        self.toplevel.bind("<Alt-v><q>", lambda x: self.database('video','Assert that screen is still'))
        self.toplevel.bind("<Alt-v><a>", lambda x: self.database('video','Assert that screen changes'))
        self.toplevel.bind("<Alt-v><e>", lambda x: self.database('video','Wait if screen changes'))
        self.toplevel.bind("<Alt-v><u>", lambda x: self.database('video','Force soft failure'))
        self.toplevel.bind("<Alt-v><i>", lambda x: self.database('video','Record info'))
        self.toplevel.bind("<Alt-v><t>", lambda x: self.database('video','Take screenshot'))
        # Accelerators for the Audio menu items.
        self.toplevel.bind("<Alt-a><r>", lambda x: self.database('audio', 'Start audio recording'))
        self.toplevel.bind("<Alt-a><s>", lambda x: self.database('audio', 'Assert recorded sound'))
        self.toplevel.bind("<Alt-a><c>", lambda x: self.database('audio', 'Check recorded sound'))
        # Accelerators for the Keyboard menu items.
        self.toplevel.bind("<Alt-k><p>", lambda x: self.database('keyboard','Press key'))
        self.toplevel.bind("<Alt-k><h>", lambda x: self.database('keyboard','Hold key'))
        self.toplevel.bind("<Alt-k><r>", lambda x: self.database('keyboard','Release key'))
        self.toplevel.bind("<Alt-k><t>", lambda x: self.database('keyboard','Type text'))
        self.toplevel.bind("<Alt-k><s>", lambda x: self.database('keyboard','Type text safely'))
        self.toplevel.bind("<Alt-k><w>", lambda x: self.database('keyboard','Type password'))
        self.toplevel.bind("<Alt-k><c>", lambda x: self.database('keyboard','Run command'))
        self.toplevel.bind("<Alt-k><e>", lambda x: self.database('keyboard','Press key until event'))
        # Accelerators for the Mouse menu items.
        self.toplevel.bind("<Alt-m><c>", lambda x: self.database('mouse','Click mouse'))
        self.toplevel.bind("<Alt-m><d>", lambda x: self.database('mouse','Doubleclick mouse'))
        self.toplevel.bind("<Alt-m><t>", lambda x: self.database('mouse','Tripleclick mouse'))
        self.toplevel.bind("<Alt-m><r>", lambda x: self.database('mouse','Drag mouse'))
        self.toplevel.bind("<Alt-m><p>", lambda x: self.database('mouse','Set mouse location'))
        self.toplevel.bind("<Alt-m><h>", lambda x: self.database('mouse','Hide mouse'))
        # Accelerators for the Variables menu items.
        self.toplevel.bind("<Alt-r><g>", lambda x: self.database('variable','Read variable'))
        self.toplevel.bind("<Alt-r><d>", lambda x: self.database('variable','Read strict variable'))
        self.toplevel.bind("<Alt-r><s>", lambda x: self.database('variable','Set variable'))
        self.toplevel.bind("<Alt-r><c>", lambda x: self.database('variable','Check variable'))
        self.toplevel.bind("<Alt-r><l>", lambda x: self.database('variable','Read variable as list'))
        self.toplevel.bind("<Alt-r><o>", lambda x: self.database('variable','Check value in list of variables'))
        # Accelerators for the Script menu items.
        self.toplevel.bind("<Alt-s><a>", lambda x: self.database('script','Run script and assert'))
        self.toplevel.bind("<Alt-s><r>", lambda x: self.database('script','Run script'))
        self.toplevel.bind("<Alt-s><b>", lambda x: self.database('script','Run script in background'))
        self.toplevel.bind("<Alt-s><u>", lambda x: self.database('script','Run sudo script and assert'))
        self.toplevel.bind("<Alt-s><d>", lambda x: self.database('script','Run sudo script'))
        self.toplevel.bind("<Alt-s><c>", lambda x: self.database('script','Collect script output'))
        self.toplevel.bind("<Alt-s><v>", lambda x: self.database('script','Collect script output and validate'))
        self.toplevel.bind("<Alt-s><t>", lambda x: self.database('script','Check if terminal is serial'))
        self.toplevel.bind("<Alt-s><w>", lambda x: self.database('script','Wait for serial output'))
        self.toplevel.bind("<Alt-s><f>", lambda x: self.database('script','Read test data from file'))
        self.toplevel.bind("<Alt-s><e>", lambda x: self.database('script','Save temp file'))
        self.toplevel.bind("<Alt-s><o>", lambda x: self.database('script','Become root'))
        self.toplevel.bind("<Alt-s><i>", lambda x: self.database('script','Make sure package is installed'))
        self.toplevel.bind("<Alt-s><m>", lambda x: self.database('script','Hash the string with MD5'))
        self.toplevel.bind("<Alt-s><x>", lambda x: self.database('script','Start GUI application'))
        # Accelerators for the Log menu items.
        self.toplevel.bind("<Alt-l><m>", lambda x: self.database('logs','Log a message'))
        self.toplevel.bind("<Alt-l><u>", lambda x: self.database('logs','Upload logs'))
        self.toplevel.bind("<Alt-l><a>", lambda x: self.database('logs','Upload asset'))
        # Accelerators for the Helpers menu items.
        self.toplevel.bind("<Alt-h><i>", lambda x: self.database('helper','Get host ip'))
        self.toplevel.bind("<Alt-h><u>", lambda x: self.database('helper','Get base url'))
        self.toplevel.bind("<Alt-h><d>", lambda x: self.database('helper','Get data asset url'))
        self.toplevel.bind("<Alt-h><c>", lambda x: self.database('helper','Make arguments compatible'))
        self.toplevel.bind("<Alt-h><p>", lambda x: self.database('helper','Show curl progress'))
        # Accelerators for the Misc menu
        self.toplevel.bind("<Alt-m><p>", lambda x: self.database('misc','Send power signal'))
        self.toplevel.bind("<Alt-m><c>", lambda x: self.database('misc','Check machine shut down'))
        self.toplevel.bind("<Alt-m><a>", lambda x: self.database('misc','Assert machine shut down'))
        self.toplevel.bind("<Alt-m><e>", lambda x: self.database('misc','Eject machine CD'))
        self.toplevel.bind("<Alt-m><d>", lambda x: self.database('misc','Save memory dump'))
        self.toplevel.bind("<Alt-m><s>", lambda x: self.database('misc','Save storage drives'))
        self.toplevel.bind("<Alt-m><f>", lambda x: self.database('misc','Freeze the VM'))
        self.toplevel.bind("<Alt-m><r>", lambda x: self.database('misc','Resume the VM'))
        self.toplevel.bind("<Alt-m><j>", lambda x: self.database('misc','Parse junit log'))
        self.toplevel.bind("<Alt-m><l>", lambda x: self.database('misc','Parse extra log'))
        # Accelerators for the Perl menu items.
        self.toplevel.bind("<Alt-p><i>", lambda x: self.perl_snippets('if'))
        self.toplevel.bind("<Alt-p><l>", lambda x: self.perl_snippets('if_elsif'))
        self.toplevel.bind("<Alt-p><e>", lambda x: self.perl_snippets('if_else'))
        self.toplevel.bind("<Alt-p><f>", lambda x: self.perl_snippets('for'))
        self.toplevel.bind("<Alt-p><c>", lambda x: self.perl_snippets('foreach'))
        self.toplevel.bind("<Alt-p><v>", lambda x: self.perl_snippets('var'))
        self.toplevel.bind("<Alt-p><r>", lambda x: self.perl_snippets('arg'))
        self.toplevel.bind("<Alt-p><m>", lambda x: self.perl_snippets('args'))
        self.toplevel.bind("<Alt-p><u>", lambda x: self.perl_snippets('unless'))
        # Accelerators for the Virtual menu
        self.toplevel.bind("<Alt-x><v>", lambda x: self.show_connect_vm())
        self.toplevel.bind("<Alt-x><t>", lambda x: self.show_create_needle())
        # Accelerators for the About menu
        self.toplevel.bind("<F1>", lambda x: self.show_docs('help'))
        # Accelerators for usual application stuff
        self.toplevel.bind("<Control-q>", lambda x: self.close_application())
        self.toplevel.bind("<Control-s>", lambda x: self.save_file())
        self.toplevel.bind("<Control-n>", lambda x: self.new_file())
        self.toplevel.bind("<Control-o>", lambda x: self.open_file())
        self.toplevel.bind("<Control-a>", lambda x: self.select_all())
        # Binds some keys in the text widget
        self.text.bind('<Tab>', lambda x: self.insert_tab())
        self.text.bind('<Key>', self.text_edited)

    def run(self):
        """ Run the application """
        self.toplevel.mainloop()

    def close_application(self):
        """ Work around the destroy method to close the application properly. """
        # If the content is not saved ask to save or close anyway.
        if self.is_saved == False:
            closefile = messagebox.askyesno('File not saved', 'The current file has not been saved yet. Do you still want to close the file?')
        # If the content is saved, then we act as if Yes was chosen in the dialogue.
        else:
            closefile = True
        # If closing was confirmed, then destroy the application or do nothing.
        if closefile:
            self.toplevel.destroy()
        else:
            pass

###############################  Below this line, we will define other useful methods for the application.
    
    def update_title(self, status):
        """ Prepare a title string to reflect if file is saved or not 
        and show it in the title bar. """
        # If not saved, then produce * before the file name.
        if status == 'unsave':
            s = "*"
        else:
            s = ""
        # If we have the opened file, then let's get its base name and
        # put it in the title string as well.
        if not self.filetosave:
            base = ""
        else:
            base = os.path.basename(self.filetosave)
        # Update the application title
        self.toplevel.title(f"{s} {base} - {self.appname}")

    def put_into_text(self, text):
        """ Puts a string into the text widget and set the status to 'no saved'. """
        # Read the cursor position
        idx = self.text.index('insert')
        # Place the text on that position
        self.text.insert(idx, text)
        # Set the document to unsaved and update the title string.
        self.is_saved = False
        self.update_title('unsave')

    def database(self, family, record):
        """ Get a snippet to from a database of snippets located in the testapi.py module. """
        # The database is a dictionary where keys are "families" and values are lists of definitions.
        # So we pick up the family of definitions
        chapter = self.db[family]
        data = None
        # Iterate over the definitions and find the one that matches the selection.
        for c in chapter:
            if c.name == record:
                data = c
        # When the data is found it is placed into the text widget.
        if data and self.comments_on.get() == 0 and self.args_on.get() == 0:
            self.put_into_text(data.display_command())
        elif data and self.args_on.get() == 0:
            self.put_into_text(data.describe())
            self.put_into_text(data.display_command())
        elif data and self.comments_on.get() == 0:
            self.put_into_text(data.display_syntax())
        elif data:
            self.put_into_text(data.all())
        # This should actually never happen, unless there is an error in the code.
        else:
            messagebox.showerror('Unknown request','It seems that a menu item or a keyboard shortcut require a non-existing snippet. Please, report a bug.')

    def perl_snippets(self, snippet):
        """ Return a perl snippet. """
        # The perl snippets have a different structure and they are not as numerous as openqa snippets. 
        # Therefore we only have them in a separate routine. 
        if snippet == 'if':
            self.put_into_text("if (condition) {\n   # Put some code here;\n}\n")
        elif snippet == 'unless':
            self.put_into_text("unless (condition) {\n   # Put some code here;\n}\n")
        elif snippet == 'if_else':
            self.put_into_text("if (condition) {\n   # Put some code here;\n}\nelse {\n    # Some alternative code;\n}\n")
        elif snippet == 'if_elsif':
            self.put_into_text("if (condition) {\n   # Put some code here;\n}\nelsif (other condition) {\n    # Some alternative code;\n}\nelse {\n    # Fallback code;\n}\n")
        elif snippet == 'for':
            self.put_into_text("for my $i (@array) {\n    # Put some code here;\n}\n")
        elif snippet == 'foreach':
            self.put_into_text("foreach (@array) {\n    # Put some code here;\n}\n")
        elif snippet == 'var':
            self.put_into_text('my $variable = value;\n')
        elif snippet == 'arg':
            self.put_into_text("my $variable = shift;\n")
        elif snippet == 'args':
            self.put_into_text("my ($var1, $var2, ...) = @_;\n")
        else:
            messagebox.showerror('Unknown request','It seems that a menu item or a keyboard shortcut calls for a non-existing snippet. Please, report a bug.')

    def set_test_flags(self):
        """ Insert test flag snippet into the text field. """
        lines = [
            'sub test_flags {',
            '    return {fatal => 0, ignore_failure => 0, milestone => 0, no_rollback => 0, always_rollback => 0};',
            '}'
        ]
        snippet = '\n'.join(lines)
        self.put_into_text(snippet)

    def create_layout(self):
        """ Insert the file layout into the text field. """
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
        """ Opens a file. """
        # First, let's make sure the document is saved, or the user does not want to save it. The dialog sets the $closefile
        # to True if the user does not want to save the current buffer.
        if self.is_saved == False:
            closefile = messagebox.askyesno('File not saved', 'The file has not been saved yet, do you want to open another file?')
        # Else it means, that the document is saved so we can proceed with closing the current buffer.
        else:
            closefile = True
        # If closefile is True from the decision above, we will throw away the unsaved buffer
        if closefile:
            # We will use a dialogue to open the file, so only existing files will be visible.
            if not filename:
                self.filetosave = filedialog.askopenfilename(filetypes=[('openQA script','*.pm')])
            else:
                self.filetosave = os.path.abspath(filename)
            # Get the filename
            base = os.path.basename(self.filetosave)
            # Read the data from the file
            with open(self.filetosave, 'r') as inputfile:
                data = inputfile.readlines()
            # Delete the content of the text widget.
            self.text.delete('1.0', 'end')
            # Fill the text widget with data
            for line in data:
                self.put_into_text(line)
            # Update the status to "saved"
            self.update_title('save')

    def save_file(self):
        """ Save the file """
        # If there is no file opened to save the buffer, use the "Save as" routine.
        if not self.filetosave:
            self.save_as_file()
        else:
            # Get the content of the text widget
            data = self.text.get('1.0','end')
            # Write it into the file.
            with open(self.filetosave, 'w') as outputfile:
                outputfile.write(data)
            # Get the file name and update the title bar.
            base = os.path.basename(self.filetosave)
            self.update_title('save')
            self.is_saved = True

    def save_as_file(self):
        # Use the dialogue to save as into a file.
        self.filetosave = filedialog.asksaveasfilename(filetypes=[('openQA script','*.pm')])
        # Get the content of the text widget
        data = self.text.get('1.0', 'end')
        # Save it into the file
        with open(self.filetosave, 'w') as outputfile:
            outputfile.write(data)
        # Get the file name and update the title bar.    
        base = os.path.basename(self.filetosave)
        self.update_title('save')

    def new_file(self):
        """ Create a new file. """
        # If the current buffer is not saved, ask if user wants to save it, for details see the open_file routine.
        if self.is_saved == False:
            closefile = messagebox.askyesno('File not saved', 'The file has not been saved yet, do you still want to open new file?')
        else:
            closefile = True
        # Discard the content of the text widget and set the status variables as they were in the beginning.
        if closefile:
            self.text.delete('1.0','end')
            self.filetosave = None
            self.toplevel.title(self.appname)
        else:
            pass

    def text_edited(self, e):
        """ Trigger the status to unsave whenever an keyboard event happens in the test widget. """
        pass_keys = ['Left', 'Up', 'Right', 'Down', 'Control_L', 'Alt_L', 'ISO_Level3_Shift', 
                     'Shift_R', 'Shift_L', 'Caps_Lock', 'Insert', 'Home', 'End', 'Next', 
                     'Prior', 'Num_Lock', 'Scroll_Lock']
        if e.keysym in pass_keys:
            pass
        else:
            self.is_saved = False
            self.update_title('unsave')

    def select_all(self):
        """ Select the content of the text widget. """
        # This methods supplies the Ctrl-A combination that is not supported by the Text widget per se.
        self.text.tag_add('sel', '1.0', 'end')


    def show_docs(self, doctype):
        """ Open external web resources to cover for Help and Documentation. """
        if doctype == 'testapi':
            url = 'http://open.qa/api/testapi/'
        elif doctype == 'docs':
            url = 'http://open.qa/documentation/'
        elif doctype == 'help':
            url = 'https://lruzicka.github.io/chancery/'
        webbrowser.open_new(url)

    def insert_tab(self):
        """ Inserts four spaces into the text, when tab is pressed. """
        self.put_into_text("   ")


    def show_connect_vm(self):
        """ Show a dialogue to connect to a VM """
        # Create the basic GUI for the dialogue
        self.connect_dialogue = Toplevel(self.toplevel)
        self.connect_dialogue.title('Connect to a VM')
        self.cd_layout = Frame(self.connect_dialogue)
        self.cd_layout.grid()
        self.cd_label = Label(self.cd_layout, text='Choose a VM:', padx=10, pady=5)
        self.cd_label.grid(row=0, column=0)
        choices = StringVar()
        self.cd_choose_box = ttk.Combobox(self.cd_layout, textvariable=choices, height=3)
        self.cd_choose_box.grid(row=0, column=1)
        self.cd_connect = Button(self.cd_layout, text="Connect", width=10, command=lambda: self.connect_vm())
        self.cd_connect.grid(row=1, column=1)
        # Get the domain names from the kvm hypervisor
        try:
            self.kvm = libvirt.open("qemu:///session")
            # Get the names of all running domains in the hypervisor.
            domains = [x.name() for x in self.kvm.listAllDomains()]
            if len(domains) == 0:
                messagebox.showerror("No domains found", "Either the hypervisor is not running or no VMs available in the qemu:///session.")
            self.cd_choose_box['values'] = domains
        except libvirt.libvirtError:
            messagebox.showerror("Error", "Failed to open connection to the hypervisor.")
            self.cd_choose_box['values'] = []

    def connect_vm(self):
        """ Updates the status variable with the correct KVM entry. """
        selected = self.cd_choose_box.get()
        if not selected:
            messagebox.showerror("No VM selected", "Please, select one of the available VMs.")
        else:
            self.virtual_machine = selected
            self.connect_dialogue.destroy()
            messagebox.showinfo("Connected successfully", f"The application is now able to take pictures from the {selected} virtual machine.")

    def show_create_needle(self):
        """ Show a dialogue to create a needle. """
        # Create the basic GUI for the dialogue if the file is saved.
        if self.filetosave:
            self.dneedle = Toplevel(self.toplevel)
            self.dneedle.title('Take a VM screenshot.')
            self.dframe = ttk.Frame(self.dneedle)
            self.dframe.grid()
            self.dlabel = ttk.Label(self.dframe, text='Set the primary tag:')
            self.dlabel.grid(row=0, column=0)
            self.dentry = ttk.Entry(self.dframe, width=30)
            self.dentry.grid(row=1, column=0)
            self.dtake = ttk.Button(self.dframe, text="Create needle", command=lambda: self.create_needle())
            self.dtake.grid(row=2, column=0)
        else:
            messagebox.showerror("File not saved", "Save the file before you attempt to create needles.")
            

    def create_needle(self):
        needlename = self.dentry.get()
        # Take the screenshot from the virtual machine.
        path = f"{os.path.dirname(self.filetosave)}/{needlename}"
        self.last_needle_taken = path
        screen = take_screenshot(self.virtual_machine, self.kvm, path)
        # Close the window
        self.dneedle.destroy()
        self.put_into_text(f'"{needlename}"')

    def edit_needle(self):
        screenshot = f"{self.last_needle_taken}.png"
        subprocess.run(["needly", screenshot])

###############################################################################################
## Here, methods not dependent on the main application window are defined.

def show_about(topwindow):
    """ Displays the About window. The method takes the toplevel widget
    under which it should display. """
    # Define the GUI of the dialogue
    titlefont = font.Font(size=14, weight="bold")
    title = "Chancery (0.9)"
    lines = [
        'a basic text editor with pre-created openQA snippets that enables developing openQA test scripts more rapidly.',
        '',
        'This tool is open software developed under the GPL license.',
        '',
        'Created by Lukáš Růžička (lruzicka@redhat.com)',
        'Red Hat (2022)'
    ]
    text = '\n'.join(lines)
    about = Toplevel(topwindow)
    about.wm_title('About')
    about.columnconfigure(0, weight=1)
    about.rowconfigure(0, weight=1)
    ttk.Label(about, text=title, font=titlefont).grid(column=0, row=0, sticky='nsew', pady=20, padx=10)
    ttk.Label(about, text=text, wraplength=200).grid(column=0, row=1, sticky='nsew', pady=20, padx=10)
    ttk.Button(about, text="Close", command=about.destroy).grid(column=0,row=2)
    
def take_screenshot(virtual_machine, hypervisor, tagfilename="screenshot.png"):
    """ Take the screenshot from the running virtual machine. As only .ppm files
    are possible, use imagemagick to convert the shot into a .png file and save
    it. 
    It takes the virtual_machine's name, the hypervisor connection, and the tagfilename
    as arguments. 
    """

    # When no VM has been previously selected, there is no need 
    # to try and take screenshots.
    # Use the domain name to get the domain object
    domain = hypervisor.lookupByName(virtual_machine)
    # Create a stream to the hypervisor
    stream = hypervisor.newStream()
    # Collect the available image type of the first screen
    # On a VM usually only one screen is available, 
    # so we will take the first one and will not bother
    # about others.
    image_type = domain.screenshot(stream, 0)
    # The stream will be caught in an envelope
    image_data = io.BytesIO()
    # Now, let's take the data from the stream
    part_stream = stream.recv(8192)
    while part_stream != b'':
        image_data.write(part_stream)
        part_stream = stream.recv(8192)
    # Convert and save the image
    image_data.seek(0)
    image = Image.open(image_data)
    path = ""
    save_as_name = f"{tagfilename}.png"
    image.save(save_as_name, 'PNG')
    image_data.close()
    stream.finish()
    # Update the status variable to have that last image available
    path = os.path.join(os.path.abspath('.'), save_as_name)
    # Return the path to the saved image
    return path

def main():
    # Read the arguments if there is a file name on the CLI.
    try:
        filename = sys.argv[1]
    except IndexError:
        filename = None
    # Start the application and open the file, if there is one.
    app = Application(filename=filename)
    app.run()
        
################################################################################################


if __name__ == '__main__':
    main()


