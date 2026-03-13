# Chancery Codebase Overview

## Project Summary

**Chancery** is a specialized text editor designed for creating openQA test scripts. It's written in Python using Tkinter for the GUI and provides quick access to openQA test API commands through menus, buttons, and keyboard shortcuts.

**License**: GPL-2.0-or-later
**Author**: Lukáš Růžička (lruzicka@redhat.com)
**Organization**: Red Hat
**Version**: 0.9.6
**Python Version**: ^3.10

## What is openQA?

OpenQA is an automated testing framework used primarily for Linux distribution testing. Tests are written in Perl and use a specialized API for interacting with virtual machines through screen matching, keyboard/mouse input, and command execution.

## Architecture

### File Structure

```
chancery/
├── chancery/
│   ├── __init__.py
│   ├── chancery.py      # Main editor application
│   ├── needler.py       # Needle editor for visual testing
│   └── testapi.py       # Database of 69 openQA command definitions
├── tests/
│   ├── __init__.py
│   └── test_chancery.py
├── pyproject.toml       # Poetry configuration
└── README.rst
```

### Main Components

#### 1. chancery.py (Main Application)

The core text editor with integrated openQA functionality.

**Key Classes:**
- `Application`: Main application window and logic

**Features:**
- **Syntax Highlighting**: Custom lexer combining Python's IDLE colorizer with openQA/Perl keywords
- **Command Insertion**: 69 pre-defined openQA commands insertable via menus or shortcuts
- **File Management**: New, Open, Save, Save As with unsaved changes tracking
- **VM Integration**: Connect to libvirt VMs for screenshot capture
- **Needle Creation**: Integrated workflow for creating visual test needles
- **Template Generation**: Quick file layouts and Perl code snippets

**UI Layout:**
```
┌─────────────────────────────────────────────────┐
│ Menu Bar (File, Video, Audio, Keyboard, ...)   │
├──────────────┬──────────────────────────────────┤
│ Quick Actions│                                  │
│ Panel        │  Syntax-Highlighted              │
│ (Buttons)    │  Text Editor                     │
│              │  (Scrolled Text Widget)          │
│              │                                  │
└──────────────┴──────────────────────────────────┘
```

**Menu Categories:**

1. **File**: Basic file operations (New, Open, Save, Exit)
2. **Video** (14 commands): Screen assertions, needle matching, clicks
3. **Audio** (3 commands): Audio recording and verification
4. **Keyboard** (8 commands): Key presses, text typing, command execution
5. **Mouse** (6 commands): Clicks, drags, positioning
6. **Variables** (6 commands): Reading/setting test variables
7. **Scripts** (14 commands): Command execution, validation, output collection
8. **Logs** (3 commands): Diagnostic messages, file uploads
9. **Helpers** (5 commands): Utility functions (URLs, compatibility)
10. **Misc** (10 commands): Power control, VM operations, log parsing
11. **Perl**: Code structure snippets (if/else, loops, variables)
12. **VirtMachine**: VM connection and needle creation
13. **Help**: Documentation links and About dialog

**Keyboard Shortcuts:**
- Standard: Ctrl-N (New), Ctrl-O (Open), Ctrl-S (Save), Ctrl-Q (Quit)
- Command insertion: Alt-based combinations (e.g., Alt-V-C for "Assert and click match")
- Tab key: Inserts 4 spaces instead of tab character

**Configuration Options:**
- Include/exclude comments when inserting commands
- Include/exclude argument examples when inserting commands

#### 2. needler.py (Needle Editor)

A simplified needle editor bundled with Chancery for creating and editing visual test reference images.

**What are Needles?**
Needles are JSON files paired with PNG screenshots that define what openQA should look for on screen. Each needle contains:
- Tags (identifiers)
- Properties (metadata)
- Areas (rectangular regions to match, with types: match/ocr/exclude)

**Features:**
- Canvas-based image display with scrollbars
- Mouse-driven rectangle drawing for defining match areas
- Coordinate display and manual adjustment
- Arrow key resizing (with Shift/Ctrl modifiers for larger steps)
- Multiple areas per needle
- JSON metadata editing in-place
- VM screenshot capture integration
- Area types: match, ocr, exclude

**Key Classes:**
- `Application`: Main needle editor window
- `fileHandler`: JSON file read/write operations
- `needleData`: Needle data structure management

**Workflow:**
1. Load a PNG image (or capture from VM)
2. Draw rectangle(s) around areas of interest
3. Set area type (match/ocr/exclude)
4. Add tags and properties
5. Save as JSON file alongside PNG

#### 3. testapi.py (Command Definitions Database)

Contains structured definitions of all 69 openQA test API commands.

**Key Classes:**
- `Definition`: Individual command definition with metadata
- `testAPI`: Database container for all definitions

**Definition Structure:**
```python
Definition(
    name="Command Name",           # Display name in menus
    desc="Description",             # Help text
    command="command_name",         # Actual Perl function name
    default="$default_args",        # Default argument example
    options={'key': 'value', ...}   # Optional parameters
)
```

**Command Categories:**
- `video`: Screen and visual testing commands
- `audio`: Audio recording and verification
- `keyboard`: Keyboard input commands
- `mouse`: Mouse control commands
- `variable`: Environment variable operations
- `script`: Command execution and validation
- `logs`: Logging and file upload
- `helper`: Utility functions
- `misc`: Power control and VM management

**Output Formats:**
- `describe()`: Returns comment with description
- `display_command()`: Returns bare command with default args
- `display_syntax()`: Returns full command with all options
- `all()`: Returns description + full syntax

## Key Features

### 1. Syntax Highlighting

Custom regex-based syntax highlighting using IDLE's colorizer:
- **COMMANDS**: openQA API functions (blue)
- **COMMENT**: Code comments (grey)
- **KEYWORD**: Python keywords (red)
- **PERL**: Perl-specific keywords (red): `sub`, `use`, `my`, `foreach`, `elsif`, etc.
- **BUILTIN**: Built-in functions (orange)
- **STRING**: String literals (green)

### 2. Virtual Machine Integration

Uses `libvirt` to connect to QEMU/KVM virtual machines:

```python
# Connection
self.kvm = libvirt.open("qemu:///session")

# Screenshot capture
domain = hypervisor.lookupByName(vm_name)
stream = hypervisor.newStream()
image_type = domain.screenshot(stream, 0)
# Convert PPM to PNG using PIL
```

**Workflow:**
1. Connect to VM via VirtMachine → Connect to VM
2. Create needle: VirtMachine → Create needle
3. Takes screenshot from VM
4. Saves as PNG with chosen tag name
5. Inserts tag name into editor at cursor
6. Edit needle: VirtMachine → Edit needle (launches `needly` external tool)

### 3. Snippet Insertion System

Commands are inserted at cursor position with configurable verbosity:

**Options:**
- Comments OFF, Args OFF: `command("$default");`
- Comments ON, Args OFF: `# Description\ncommand("$default");`
- Comments OFF, Args ON: `command($default, key => 'value', ...);`
- Comments ON, Args ON: `# Description\ncommand($default, key => 'value', ...);`

### 4. File Templates

**Test File Layout** (Create file layout button):
```perl
use base "installedtest";
use strict;
use testapi;
use utils;

sub run {


}
```

**Test Flags** (Set test flags button):
```perl
sub test_flags {
    return {fatal => 0, ignore_failure => 0, milestone => 0, no_rollback => 0, always_rollback => 0};
}
```

### 5. Unsaved Changes Tracking

Monitors keyboard events in text widget and updates title bar:
- Unsaved: `* filename.pm - Chancery - an openQA script editor`
- Saved: `filename.pm - Chancery - an openQA script editor`

Prompts user before:
- Closing application
- Opening new file
- Creating new file

## Dependencies

From `pyproject.toml`:

**Runtime:**
- `python ^3.10`
- `needly ^2.5.61` (external needle editor)

**System Libraries** (imported but not in pyproject.toml):
- `tkinter` (standard library)
- `libvirt-python` (for VM integration)
- `Pillow` (PIL - for image handling)

**Dev Dependencies:**
- `pytest ^6.2`

## Command Examples

### Video Commands

```perl
# Wait for needle with $needlematch tag to appear on screen. Then click left at the "click_point" position.
assert_and_click("$needlematch", timeout => '30', button => 'left', mousehide => '1');

# Find $needle on the screen. If needle not found, fail immediately.
assert_screen("$needlematch", timeout => '30', no_wait => '0');

# Check that the screen does not change for $seconds. If this does not happen in the $timeout frame, return 'undef'.
wait_still_screen("$seconds", timeout => '30', similarity_level => '90', no_wait => '0');
```

### Keyboard Commands

```perl
# Type a text (string). The Enter key will not be sent as part of this command unless you provide it.
type_string("$text", max_interval => '125', wait_still_change => '3', wait_still_screen => '2', similarity_level => '45', secret => '0', lf => '0');

# Type a string and also send the "Enter" key to execute the command.
enter_cmd("$text", max_interval => '125', wait_still_change => '3', wait_still_screen => '2', similarity_level => '45');
```

### Script Commands

```perl
# Run script and check that it ran successfully (with exit code 0). If not, fail the test.
assert_script_run("$command", timeout => '60', fail_message => 'some explanatory message', quiet => '0');

# Run script and return its output.
script_output("$command", wait => '2', type_command => '1', proceed_on_failure => '1', quiet => '0');
```

## Known Issues

1. **Fixed Typo**: Line 281 in needler.py had `irint` instead of `print` (now corrected)

## Usage

### Command Line

```bash
# Start editor
chancery

# Open specific file
chancery /path/to/test.pm
```

### Entry Point

Defined in `pyproject.toml`:
```toml
[tool.poetry.scripts]
chancery = 'chancery.chancery:main'
```

## External Resources

The application provides links to:
- **Help**: https://lruzicka.github.io/chancery/
- **openQA TestAPI Documentation**: http://open.qa/api/testapi/
- **openQA Documentation**: http://open.qa/documentation/

## Code Quality Notes

**Strengths:**
- Clear separation of concerns (UI, data, helpers)
- Comprehensive command coverage
- User-friendly quick access to common operations
- Good keyboard shortcut coverage
- Proper file handling with unsaved changes warnings

**Areas for Consideration:**
- No explicit error handling in some VM operations
- Hard-coded paths in some places
- Limited test coverage (test file exists but content unknown)
- Some commented-out code in needler.py (old menu system)

## Future Enhancement Possibilities

Based on code structure, potential areas for expansion:
1. Additional Perl snippet templates
2. More sophisticated syntax highlighting
3. Auto-completion for command parameters
4. Test runner integration
5. Needle management (browse, search existing needles)
6. Integration with openQA worker/scheduler
7. Multi-file project support

## Conclusion

Chancery is a focused, practical tool that significantly accelerates openQA test development by providing quick access to the extensive test API through an intuitive GUI. Its integration with VM screenshot capture and needle creation makes it particularly valuable for visual testing workflows.
