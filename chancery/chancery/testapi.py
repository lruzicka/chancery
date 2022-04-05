#!/usr/bin/python3

class Definition:
    def __init__(self, name, desc, command, default, options):
        self.name = name
        self.description = desc
        self.command = command
        self.default = default
        self.options = options
    
    def describe(self, tagged=False):
        """ Format the description into a comment.  """
        text = f'# {self.description}'
        if tagged:
            length = len(text)
            tag = 'comment'
            return (tag, length, text)
        else:
            return text

    def display_command(self, tagged=False):
        """ Format the command. """
        o = f'{self.command}("{self.default}");'
        return o


    def display_options(self):
        """ Return the options made into a string. The options are divided using commas. If no options, return empty string.  """
        o = []
        for key in self.options.keys():
            o.append(f"{key} => '{self.options[key]}'")
        output = ', '.join(o)
        return output

    def display_syntax(self):
        """ Return the complete command syntax. """
        output = ''
        output = f"{self.command}("
        options = self.display_options()
        # Here we need to fix the commas. If no options, then there should not be a comma
        # in the command syntax. But if options, we need to divide the default argument from
        # the options using the comma.
        if options:
            output = output + f'{self.default}, '
            output = output + options
        else:
            output = output + f'{self.default}'
        output = output + ");"
        return output

    def all(self):
        """ Return all informations on a snippet. """
        output = ''
        output = f"{self.describe()}\n"
        output = output + f"{self.display_syntax()}\n"
        return output


class testAPI:
    def __init__(self):
        self.definitions = {}
        self.wrappers = []

    def add(self, classi, definition):
        if classi not in self.definitions.keys():
            self.definitions[classi] = [definition]
        else:
            self.definitions[classi].append(definition) 

    def show_definitions(self):
        return self.definitions


# Whenever a menu item or a quick button are accessed, a corresponding snippet will be placed on the cursor position.
# The following lines will create a testAPI instance and fill it with the snippets details, so that they can be 
# utilized in the main application.
# Maybe in the future an external source of definitions (such as JSON) will be used.

testAPI = testAPI()

# Video snippets definitions
# Assert and click match
helptext = """ Wait for needle with $needlematch tag to appear on screen. Then click $button at the "click_point" position. """
d = Definition( 
            "Assert and click match", 
            helptext, 
            "assert_and_click", 
            "$needlematch", 
            {'timeout':'30', 'button':'left', 'mousehide':'1'})
testAPI.add('video', d)

# Assert and doubleclick match
helptext = """ Wait for needle with $needlematch tag to appear on screen. Then doubleclick $button at the "click_point" position. """
d = Definition( 
            "Assert and doubleclick match", 
            helptext, 
            "assert_and_dclick", 
            "$needlematch", 
            {'timeout':'30', 'button':'left', 'mousehide':'1'})
testAPI.add('video', d)

# Click last match
helptext = """ Click on the last matched needle. Set $dclick for a double click. """
d = Definition( 
            "Click last match", 
            helptext, 
            "click_last_match", 
            "$needlematch", 
            {'timeout':'30', 'button':'left', 'dclick':'0', 'mousehide':'1'})
testAPI.add('video', d)

# Assert screen for match
d = Definition( 
            "Assert screen for match", 
            "Find $needle on the screen. If needle not found, fail immediately.", 
            "assert_screen", 
            "$needlematch", 
            {'timeout':'30', 'no_wait':'0'})
testAPI.add('video', d)

# Check screen for match
d = Definition( 
            "Check screen for match", 
            "Find $needle on the screen. If needle not found return 'undef' but don't fail the test.", 
            "check_screen", 
            "$needlematch", 
            {'timeout':'0', 'no_wait':'0'})
testAPI.add('video', d)

# Check if match has tag
d = Definition( 
            "Check if match has tag", 
            "Return True if last matched needle has $tag.", 
            "match_has_tag", 
            "$tag", 
            {})
testAPI.add('video', d)

# Assert that screen is still

d = Definition( 
            "Assert that screen is still", 
            "Check that the screen does not change for $seconds. If this does not happen in the $timeout frame, fail the test. ", 
            "assert_still_screen", 
            "$seconds", 
            {'timeout':'30', 'similarity_level':'90', 'no_wait':'0'})
testAPI.add('video', d)

# Wait until screen is still

d = Definition( 
            "Wait until screen is still", 
            "Check that the screen does not change for $seconds. If this does not happen in the $timeout frame, return 'undef'. ", 
            "wait_still_screen", 
            "$seconds", 
            {'timeout':'30', 'similarity_level':'90', 'no_wait':'0'})
testAPI.add('video', d)

# Wait if screen changes

d = Definition( 
            "Wait if screen changes", 
            "Use this to wrap around another function and check if the screen changes in the given $timeout. ", 
            "wait_screen_change", 
            "sub { put a function here }", 
            {'timeout':'30', 'similarity_level':'90', 'no_wait':'0'})
testAPI.add('video', d)

# Assert that screen changes

d = Definition( 
            "Assert that screen changes", 
            "Use this to wrap around another function to check if screen changes in the $timeout. Fail the test if not.", 
            "assert_screen_change", 
            " { put a function here } ", 
            {'timeout':'10'})
testAPI.add('video', d)

# Record soft failure
helptext = """ Record a soft failure on the current test modules result. """
d = Definition( 
            "Record soft failure", 
            helptext, 
            "record_soft_failure", 
            "$reason", 
            {})
testAPI.add('video', d)

# Force soft failure
helptext = """ Override the test module status to softfail. """
d = Definition( 
            "Force soft failure", 
            helptext, 
            "force_soft_failure", 
            "$reason", 
            {})
testAPI.add('video', d)
        
# Record info
helptext = """ Record a generic step result on the current test modules."""
d = Definition( 
            "Record info", 
            helptext, 
            "record_info", 
            "$title", 
            {'output':'some text', 'result':'ok', 'resultname':'some text' })
testAPI.add('video', d)

# Take screenshot
helptext = """ Saves screenshot of current screen. """
d = Definition( 
            "Take screenshot", 
            helptext, 
            "save_screenshot", 
            "", 
            {})
testAPI.add('video', d)

# Audio snippets definitions.

# Start audio recording
helptext = """ Tells the backend to record a .wav file of the sound card. """
d = Definition( 
            "Start audio recording", 
            helptext, 
            "start_audiocapture", 
            "", 
            {})
testAPI.add('audio', d)

# Assert recorded sound
helptext = """ Tells the backend to record a .wav file of the sound card and asserts if it matches expected audio. Comparison is performed after conversion to the image. """
d = Definition( 
            "Assert recorded sound", 
            helptext, 
            "assert_recorded_sound", 
            "$soundfile", 
            {})
testAPI.add('audio', d)

# Check recorded sound
helptext = """ Tells the backend to record a .wav file of the sound card and checks if it matches expected audio. Comparison is performed after conversion to the image. """
d = Definition( 
            "Check recorded sound", 
            helptext, 
            "check_recorded_sound", 
            "$soundfile", 
            {})
testAPI.add('audio', d)

# Keyboard snippets definitions

# Press key
helptext = """ Press a key or a key combination. """
d = Definition( 
            "Press key", 
            helptext, 
            "send_key", 
            "$keyname", 
            {'wait_screen_change':'0'})
testAPI.add('keyboard', d)

# Hold key
helptext = """ Hold a key or a key combination. """
d = Definition( 
            "Hold key", 
            helptext, 
            "hold_key", 
            "$keyname", 
            {})
testAPI.add('keyboard', d)

# Release key
helptext = """ Release a held key or a key combination. """
d = Definition( 
            "Release key", 
            helptext, 
            "release_key", 
            "$keyname", 
            {})
testAPI.add('keyboard', d)

# Press key until event
helptext = """ Press a key (or a combo) repetitiously until a $needle appears. """
d = Definition( 
            "Press key until event", 
            helptext, 
            "send_key_until_needlematch", 
            "$needle, $key, 20, 1 ",
            {})
testAPI.add('keyboard', d)

# Type text
helptext = """ Type a text (string). The Enter key will not be sent as part of this command unless you provide it. """
d = Definition( 
            "Type text", 
            helptext, 
            "type_string", 
            "$text", 
            {'max_interval':'125', 'wait_still_change':'3', 'wait_still_screen':'2', 'similarity_level':'45', 'secret':'0', 'lf':'0'})
testAPI.add('keyboard', d)

# Type text safely
helptext = """ Type a text in a safe way with confirmation of any typed character. The Enter key will not be sent as part of this command unless you provide it. This only works on Fedora openQA. """
d = Definition( 
            "Type text safely", 
            helptext, 
            "type_very_safely", 
            "$text", 
            {})
testAPI.add('keyboard', d)

# Type password
helptext = """ Type a password and do not log the text to protect it from being exposed. """
d = Definition( 
            "Type password", 
            helptext, 
            "type_password", 
            "$text", 
            {'max_interval':'125', 'wait_still_change':'3', 'wait_still_screen':'2', 'similarity_level':'45'})
testAPI.add('keyboard', d)

# Run command
helptext = """ Type a string and also send the "Enter" key to execute the command. """
d = Definition( 
            "Run command", 
            helptext, 
            "enter_cmd", 
            "$text", 
            {'max_interval':'125', 'wait_still_change':'3', 'wait_still_screen':'2', 'similarity_level':'45'})
testAPI.add('keyboard', d)


# Mouse snippets definitions
# Click mouse
helptext = """ Click mouse. """
d = Definition( 
            "Click mouse", 
            helptext, 
            "mouse_click", 
            "$button", 
            {'hold_time':'0.15'})
testAPI.add('mouse', d)


# Doubleclick mouse
helptext = """ Doubleclick mouse. """
d = Definition( 
            "Doubleclick mouse", 
            helptext, 
            "mouse_dclick", 
            "$button", 
            {'hold_time':'0.15'})
testAPI.add('mouse', d)

# Tripleclick mouse
helptext = """ Tripleclick mouse. """
d = Definition( 
            "Tripleclick mouse", 
            helptext, 
            "mouse_tclick", 
            "$button", 
            {'hold_time':'0.15'})
testAPI.add('mouse', d)

# Drag mouse
helptext = """ Drag the  mouse from a $startpoint to $endpoint. """
d = Definition( 
            "Drag mouse", 
            helptext, 
            "mouse_drag", 
            "$startpoint, $endpoint, $button", 
            {})
testAPI.add('mouse', d)


# Set mouse location
helptext = """ Set mouse cursor to X, Y coordinates. """
d = Definition( 
            "Set mouse location", 
            helptext, 
            "mouse_set", 
            "$x, $y", 
            {})
testAPI.add('mouse', d)

# Hide mouse
helptext = """ Hide the mouse cursos in order not to interfere with the needles. """
d = Definition( 
            "Hide mouse", 
            helptext, 
            "mouse_hide", 
            "$border_offset", 
            {})
testAPI.add('mouse', d)


# Variable snippets definitions
# Read variable 
helptext = """ Read a variable from the environment, but allow to assign a value if variable not found. """
d = Definition( 
            "Read variable", 
            helptext, 
            "get_var", 
            "$variable_name, $fallback_value", 
            {})
testAPI.add('variable', d)

# Read strict variable 
helptext = """ Read a variable from the environment, but fail if it does not exist. """
d = Definition( 
            "Read strict variable", 
            helptext, 
            "get_required_var", 
            "$variable_name", 
            {})
testAPI.add('variable', d)

# Set variable 
helptext = """ Set $variable to the $value. If variable start with _SECRET it will not be logged. """
d = Definition( 
            "Set variable", 
            helptext, 
            "set_var", 
            "$variable_name, $value", 
            {'reload_needles':'0'})
testAPI.add('variable', d)

# Check variable 
helptext = """ Check that $variable has $value. Return 'undef' if it does not.  """
d = Definition( 
            "Check variable", 
            helptext, 
            "check_var", 
            "$variable_name, $value", 
            {})
testAPI.add('variable', d)

# Read variables as list 
helptext = """ Return the given variable as array reference (split variable value by , | or ; )  """
d = Definition( 
            "Read variable as list", 
            helptext, 
            "get_var_array", 
            "$variable, [$default]", 
            {})
testAPI.add('variable', d)

# Check value in list of variables 
helptext = """ Checks that $value in in list $variable. """
d = Definition( 
            "Check value in list of variables", 
            helptext, 
            "check_var_array", 
            "$variable, $value", 
            {})
testAPI.add('variable', d)

# Snippets for Script
# Run script and assert 
helptext = """ Run script and check that it ran successfully (with exit code 0). If not, fail the test. """
d = Definition( 
            "Run script and assert", 
            helptext, 
            "assert_script_run", 
            "$command", 
            {'timeout':'60', 'fail_message':'some explanatory message', 'quiet':'0'})
testAPI.add('script', d)

# Run script
helptext = """ Run script.  """
d = Definition( 
            "Run script", 
            helptext, 
            "script_run", 
            "$command", 
            {'timeout':'60', 'output':'output_message', 'quiet':'0', 'die_on_timeout':'-1'})
testAPI.add('script', d)

# Run script in background
helptext = """ Run script in the background without waiting for it to finish. Remember to redirect output to
prevent PID marker from getting corrupted. """
d = Definition( 
            "Run script in background", 
            helptext, 
            "background_script_run", 
            "$command", 
            {'output':'output_message', 'quiet':'0'})
testAPI.add('script', d)

# Run sudo script
helptext = """ Run script with sudo.  """
d = Definition( 
            "Run sudo script", 
            helptext, 
            "script_sudo", 
            "$command", 
            {'wait':'2'})
testAPI.add('script', d)

# Run sudo script and assert
helptext = """ Run sudo script and check that it ran successfully.  """
d = Definition( 
            "Run sudo script and assert", 
            helptext, 
            "assert_script_sudo", 
            "$command", 
            {'wait':'2'})
testAPI.add('script', d)

# Collect script output
helptext = """ Run script and return its output.  """
d = Definition( 
            "Collect script output", 
            helptext, 
            "script_output", 
            "$command", 
            {'wait':'2', 'type_command':'1', 'proceed_on_failure':'1', 'quiet':'0'})
testAPI.add('script', d)

# Collect script output and validate
helptext = """ Run script and validate its output using $regexp.  """
d = Definition( 
            "Collect script output and validate", 
            helptext, 
            "validate_script_output", 
            "$command, $code | $regexp", 
            {'timeout':'30', 'quiet':'0'})
testAPI.add('script', d)

# Check if terminal is serial
helptext = """ Check if terminal is a serial console.  """
d = Definition( 
            "Check if terminal is serial", 
            helptext, 
            "is_serial_terminal", 
            "", 
            {})
testAPI.add('script', d)

# Wait for serial output
helptext = """ Wait until $regexp appears on the serial console.  """
d = Definition( 
            "Wait for serial output", 
            helptext, 
            "wait_serial", 
            "$regex", 
            {'timeout':'90', 'expect_not_found':'0'})
testAPI.add('script', d)

# Read test data from file
helptext = """ Return content of the file located in data directory at $relpath.  """
d = Definition( 
            "Read test data from file", 
            helptext, 
            "get_test_data", 
            "$relpath", 
            {})
testAPI.add('script', d)

# Save temp file
helptext = """ Save $content to the file at $relpath.  """
d = Definition( 
            "Save temp file", 
            helptext, 
            "save_tmp_file", 
            "$relpath, $content", 
            {})
testAPI.add('script', d)

# Become root
helptext = """ Open a root shell.  """
d = Definition( 
            "Become root", 
            helptext, 
            "become_root", 
            "", 
            {})
testAPI.add('script', d)

# Make sure package is installed
helptext = """ Check if package is installed and install it if it is not.  """
d = Definition( 
            "Make sure package is installed", 
            helptext, 
            "ensure_installed", 
            "$package", 
            {})
testAPI.add('script', d)

# Hash the string with MD5
helptext = """ Take the $string and return its MD5 hash.  """
d = Definition( 
            "Hash the string with MD5", 
            helptext, 
            "hashed_string", 
            "$string", 
            {})
testAPI.add('script', d)

# Start GUI application
helptext = """ Starts a GUI $application.  """
d = Definition( 
            "Start GUI application", 
            helptext, 
            "x11_start_program", 
            "$application", 
            {})
testAPI.add('script', d)

# Log snippets
# Log a message
helptext = """ Log a diagnostic $message to the autoinst output.  """
d = Definition( 
            "Log a message", 
            helptext, 
            "diag", 
            "$message", 
            {})
testAPI.add('logs', d)

# Upload logs
helptext = """ Upload $file to openQA WebUI as a log file.  """
d = Definition( 
            "Upload logs", 
            helptext, 
            "upload_logs", 
            "$file", 
            {'failok':'0', 'timeout':'90', 'log_name':'custom_name.log'})
testAPI.add('logs', d)

# Upload asset
helptext = """ Upload $file as asset to openQA WebUI.  """
d = Definition( 
            "Upload asset", 
            helptext, 
            "upload_asset", 
            "$file", 
            {'public':'0', 'nocheck':'0'})
testAPI.add('logs', d)

# Helpers menu snippets

# Get host IP
helptext = """ Return VM’s host IP. """
d = Definition( 
            "Get host ip", 
            helptext, 
            "host_ip", 
            "", 
            {})
testAPI.add('helper', d)

# Get base url
helptext = """ Returns the base URL to contact the local os-autoinst service. Optional $path argument is appended after base url. 
Optional HASHREF $query is converted to URL query and appended after path. Return VM’s host IP. """
d = Definition( 
            "Get base url", 
            helptext, 
            "autoinst_url", 
            "[$path, $query]", 
            {})
testAPI.add('helper', d)

# Get data asset url
helptext = """ Returns the URL to download data or asset file Special values REPO_\d and ASSET_\d points to the asset configured in the corresponding variable. """
d = Definition( 
            "Get data asset url", 
            helptext, 
            "data_url", 
            "$name", 
            {})
testAPI.add('helper', d)

# Make arguments compatible
helptext = """ Helper function to create backward compatible function arguments when moving from positional arguments to named one. """
d = Definition( 
            "Make arguments compatible", 
            helptext, 
            "compat_args", 
            "$hash_ref_defaults, $arrayref_old_fixed, [ $arg1, $arg2, ...]", 
            {})
testAPI.add('helper', d)

# Show curl arguments compatible
helptext = """ Helper function to alter the curl command to show progress meter. Progress meter is shown only when the server output is redirected. This works only when uploading where the output is not lately used. """
d = Definition( 
            "Show curl progress", 
            helptext, 
            "show_curl_progress_meter", 
            "$command", 
            {})
testAPI.add('helper', d)

# Misc helpers definitions

# Send power signal
helptext = """ Trigger backend specific power action, can be 'on', 'off', 'acpi' or 'reset' """
d = Definition( 
            "Send power signal", 
            helptext, 
            "power", 
            "$action", 
            {})
testAPI.add('misc', d)

# Check machine shut down
helptext = """ Periodically check backend for status until 'shutdown'. Does not' initiate shutdown. Returns true on success and false if $timeout timeout is hit. Default timeout is 60s. """
d = Definition( 
            "Check machine shut down", 
            helptext, 
            "check_shutdown", 
            "[$timeout]", 
            {})
testAPI.add('misc', d)

# Assert machine shut down
helptext = """ Periodically check backend for status until 'shutdown'. Does not' initiate shutdown. Returns true on success and false if $timeout timeout is hit. Default timeout is 60s. """
d = Definition( 
            "Assert machine shut down", 
            helptext, 
            "assert_shutdown", 
            "[$timeout]", 
            {})
testAPI.add('misc', d)

# Eject machine CD
helptext = """ If backend supports it, eject the CD. """
d = Definition( 
            "Eject machine CD", 
            helptext, 
            "eject_cd", 
            "", 
            {})
testAPI.add('misc', d)

# Save memory dump
helptext = """ Saves the SUT memory state using $filename as base for the memory dump filename, the default will be the current test’s name.
This method must be called within a post_fail_hook. """
d = Definition( 
            "Save memory dump", 
            helptext, 
            "save_memory_dump", 
            "[$filename]", 
            {})
testAPI.add('misc', d)

# Save storage drives
helptext = """ Saves all of the SUT drives using $filename as part of the final filename, the default will be the current test’s name. The disk number will be always present.  This method must be called within a post_fail_hook. """
d = Definition( 
            "Save storage drives", 
            helptext, 
            "save_storage_drives", 
            "[$filename]", 
            {})
testAPI.add('misc', d)

# Freeze the VM
helptext = """ If the backend supports it, freeze the virtual machine. This will allow the virtual machine to be paused/frozen within the test, it is recommended to call this within a post_fail_hook so that memory and disk dumps can be extracted without any risk of data changing, or in rare cases call it before the tests tests have already begun, to avoid unexpected behaviour. """
d = Definition( 
            "Freeze the VM", 
            helptext, 
            "freeze_vm", 
            "", 
            {})
testAPI.add('misc', d)

# Resume the VM
helptext = """ If the backend supports it, resume the virtual machine. Call this method to start virtual machine CPU explicitly if DELAYED_START is set. """
d = Definition( 
            "Resume the VM", 
            helptext, 
            "resume_vm", 
            "", 
            {})
testAPI.add('misc', d)

# Parse junit log
helptext = """ Upload log file from SUT (calls upload_logs internally). The uploaded file is then parsed as jUnit format and extra test results are created from it. """
d = Definition( 
            "Parse junit log", 
            helptext, 
            "parse_junit_log", 
            "$filename", 
            {})
testAPI.add('misc', d)


# Parse extra log
helptext = """ Upload log file from SUT (calls upload_logs internally). The uploaded file is then parsed as the format supplied, that can be understood by OpenQA::Parser and extra test results are created from it. """
d = Definition( 
            "Parse extra log", 
            helptext, 
            "parse_extra_log", 
            "", 
            {'Format':'report.xml'})

testAPI.add('misc', d)

#----------------------------------------------
if __name__ == '__main__':
    print('This is a script that creates the database of command definitions.')
    print('It is not designed to be run separately. Run the main application executable to use the application.')
   
