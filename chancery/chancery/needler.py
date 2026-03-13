#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
needler.py

This is a simplified version of Needly that is bundled
with the Chancery editor for quicker addition of needle
files.

Created by Lukáš Růžička (lruzicka@redhat.com)

Red Hat, 2022
Migrated to GTK4, 2026
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio

import io
import os
import json
import re
import sys
import libvirt
from PIL import Image

class Application:
    """ Hold the GUI frames and widgets, as well as the handling in the GUI. """
    def __init__(self, master=None, cli_path=None):
        self.app = Gtk.Application(application_id='org.chancery.needler')
        self.app.connect('activate', self.on_activate)
        self.cli_path = cli_path

        # Initialize data structures
        self.images = []
        self.needleCoordinates = [0, 0, 0, 0]
        self.directory = ""
        self.rectangle = None
        self.needle = needleData({"properties":[], "tags":[], "area":[]})
        self.imageName = None
        self.handler = None
        self.imageCount = 0
        self.rectangles = []
        self.kvm = None
        self.virtual_machine = None
        self.startPoint = [0, 0]
        self.endPoint = [0, 0]
        self.pixbuf = None
        self.surface = None
        self.window = None

    def on_activate(self, app):
        """Create the main window when the application is activated."""
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title("Create a needle for the selected tag.")
        self.window.set_default_size(1280, 800)

        # Set up key event controller
        key_controller = Gtk.EventControllerKey()
        key_controller.connect('key-pressed', self.on_key_pressed)
        self.window.add_controller(key_controller)

        self.buildWidgets()
        self.window.present()

        # Load CLI path if provided
        if self.cli_path:
            self.acceptCliChoice(self.cli_path)

    def run(self):
        """ Starts the mainloop of the application. """
        self.app.run(None)

    def on_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard shortcuts."""
        ctrl = state & Gdk.ModifierType.CONTROL_MASK

        if ctrl:
            if keyval == Gdk.KEY_m:
                self.modifyArea()
                return True
            elif keyval == Gdk.KEY_a:
                self.addAreaToNeedle()
                return True
            elif keyval == Gdk.KEY_r:
                self.removeAreaFromNeedle()
                return True
            elif keyval == Gdk.KEY_s:
                self.createNeedle()
                return True
            elif keyval == Gdk.KEY_q:
                self.window.close()
                return True
        return False

    def acceptCliChoice(self, path):
        """Opens an image for editing when passed as a CLI argument upon starting the editor."""
        self.directory = os.path.dirname(path)
        image = os.path.basename(path)
        if '.json' in image:
            prefix = image.split('.')[0]
            image = prefix + '.png'
        self.imageName = image
        self.imageCount = 0
        path = os.path.join(self.directory, self.imageName)
        self.displayImage(path)

    def buildWidgets(self):
        """Construct GUI"""
        # Main horizontal box
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.window.set_child(main_box)

        # Left side: Picture frame with scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_width(1025)
        scrolled.set_min_content_height(769)

        # Drawing area for the picture
        self.pictureField = Gtk.DrawingArea()
        self.pictureField.set_size_request(1025, 769)
        self.pictureField.set_draw_func(self.on_draw)

        # Add gesture controllers for mouse interaction
        drag_controller = Gtk.GestureDrag()
        drag_controller.connect('drag-begin', self.on_drag_begin)
        drag_controller.connect('drag-update', self.on_drag_update)
        drag_controller.connect('drag-end', self.on_drag_end)
        self.pictureField.add_controller(drag_controller)

        # Key controller for arrow keys
        key_controller = Gtk.EventControllerKey()
        key_controller.connect('key-pressed', self.on_picture_key_pressed)
        self.pictureField.add_controller(key_controller)

        # Make drawing area focusable
        self.pictureField.set_focusable(True)

        scrolled.set_child(self.pictureField)
        main_box.append(scrolled)

        # Right side: JSON data frame
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        right_box.set_margin_start(10)
        right_box.set_margin_end(10)
        right_box.set_margin_top(10)
        right_box.set_margin_bottom(10)
        main_box.append(right_box)

        # Filename
        name_label = Gtk.Label(label="Filename:")
        name_label.set_halign(Gtk.Align.START)
        right_box.append(name_label)

        self.nameEntry = Gtk.Entry()
        self.nameEntry.set_editable(False)
        right_box.append(self.nameEntry)

        # Properties
        prop_label = Gtk.Label(label="Properties:")
        prop_label.set_halign(Gtk.Align.START)
        right_box.append(prop_label)

        prop_scroll = Gtk.ScrolledWindow()
        prop_scroll.set_min_content_height(80)
        self.propText = Gtk.TextView()
        self.propText.set_wrap_mode(Gtk.WrapMode.WORD)
        prop_scroll.set_child(self.propText)
        right_box.append(prop_scroll)

        # Area Coordinates
        coord_label = Gtk.Label(label="Area Coordinates:")
        coord_label.set_halign(Gtk.Align.START)
        right_box.append(coord_label)

        # Coordinate grid
        coord_grid = Gtk.Grid()
        coord_grid.set_column_spacing(5)
        coord_grid.set_row_spacing(5)
        right_box.append(coord_grid)

        # X1, Y1
        coord_grid.attach(Gtk.Label(label="X1:"), 0, 0, 1, 1)
        self.axEntry = Gtk.Entry()
        self.axEntry.set_width_chars(5)
        coord_grid.attach(self.axEntry, 1, 0, 1, 1)

        coord_grid.attach(Gtk.Label(label="Y1:"), 2, 0, 1, 1)
        self.ayEntry = Gtk.Entry()
        self.ayEntry.set_width_chars(5)
        coord_grid.attach(self.ayEntry, 3, 0, 1, 1)

        coord_grid.attach(Gtk.Label(label="Width:"), 4, 0, 1, 1)
        self.widthEntry = Gtk.Entry()
        self.widthEntry.set_width_chars(5)
        coord_grid.attach(self.widthEntry, 5, 0, 1, 1)

        # X2, Y2
        coord_grid.attach(Gtk.Label(label="X2:"), 0, 1, 1, 1)
        self.bxEntry = Gtk.Entry()
        self.bxEntry.set_width_chars(5)
        coord_grid.attach(self.bxEntry, 1, 1, 1, 1)

        coord_grid.attach(Gtk.Label(label="Y2:"), 2, 1, 1, 1)
        self.byEntry = Gtk.Entry()
        self.byEntry.set_width_chars(5)
        coord_grid.attach(self.byEntry, 3, 1, 1, 1)

        coord_grid.attach(Gtk.Label(label="Height:"), 4, 1, 1, 1)
        self.heigthEntry = Gtk.Entry()
        self.heigthEntry.set_width_chars(5)
        coord_grid.attach(self.heigthEntry, 5, 1, 1, 1)

        # Area type
        type_label = Gtk.Label(label="Area type:")
        type_label.set_halign(Gtk.Align.START)
        right_box.append(type_label)

        self.typeList = Gtk.DropDown.new_from_strings(["match", "ocr", "exclude"])
        self.typeList.set_selected(0)
        right_box.append(self.typeList)

        # Tags
        tags_label = Gtk.Label(label="Tags:")
        tags_label.set_halign(Gtk.Align.START)
        right_box.append(tags_label)

        tags_scroll = Gtk.ScrolledWindow()
        tags_scroll.set_min_content_height(100)
        self.textField = Gtk.TextView()
        self.textField.set_wrap_mode(Gtk.WrapMode.WORD)
        tags_scroll.set_child(self.textField)
        right_box.append(tags_scroll)

        # JSON Data
        json_label = Gtk.Label(label="Json Data:")
        json_label.set_halign(Gtk.Align.START)
        right_box.append(json_label)

        json_scroll = Gtk.ScrolledWindow()
        json_scroll.set_min_content_height(150)
        json_scroll.set_vexpand(True)
        self.textJson = Gtk.TextView()
        self.textJson.set_wrap_mode(Gtk.WrapMode.WORD)
        json_scroll.set_child(self.textJson)
        right_box.append(json_scroll)

        # Areas in needle
        needle_label = Gtk.Label(label="Areas in needle:")
        needle_label.set_halign(Gtk.Align.START)
        right_box.append(needle_label)

        self.needleEntry = Gtk.Entry()
        self.needleEntry.set_editable(False)
        right_box.append(self.needleEntry)

        # VM connection
        vm_label = Gtk.Label(label="VM connection:")
        vm_label.set_halign(Gtk.Align.START)
        right_box.append(vm_label)

        self.vmEntry = Gtk.Entry()
        self.vmEntry.set_editable(False)
        self.vmEntry.set_text("Not connected")
        right_box.append(self.vmEntry)

    def on_draw(self, area, cr, width, height):
        """Draw the image and rectangle on the canvas."""
        # Draw the image if available
        if self.pixbuf:
            Gdk.cairo_set_source_pixbuf(cr, self.pixbuf, 0, 0)
            cr.paint()

        # Draw rectangles
        if self.rectangles:
            cr.set_source_rgb(1, 0, 0)  # Red color
            cr.set_line_width(2)
            for rect in self.rectangles:
                if rect and len(rect) == 4:
                    x1, y1, x2, y2 = rect
                    cr.rectangle(x1, y1, x2 - x1, y2 - y1)
                    cr.stroke()

        # Draw current rectangle
        if self.rectangle and len(self.rectangle) == 4:
            cr.set_source_rgb(1, 0, 0)  # Red color
            cr.set_line_width(2)
            x1, y1, x2, y2 = self.rectangle
            cr.rectangle(x1, y1, x2 - x1, y2 - y1)
            cr.stroke()

    def on_drag_begin(self, gesture, x, y):
        """Start drawing the rectangle."""
        self.startPoint = [int(x), int(y)]
        if self.rectangle is None:
            self.rectangle = [int(x), int(y), int(x), int(y)]
        self.pictureField.grab_focus()

    def on_drag_update(self, gesture, offset_x, offset_y):
        """Update the rectangle as the mouse is dragged."""
        start_x, start_y = gesture.get_start_point()
        end_x = start_x + offset_x
        end_y = start_y + offset_y

        self.endPoint = [int(end_x), int(end_y)]
        self.needleCoordinates = self.startPoint + self.endPoint
        self.rectangle = self.needleCoordinates.copy()

        self.pictureField.queue_draw()

    def on_drag_end(self, gesture, offset_x, offset_y):
        """Finalize the rectangle and normalize coordinates."""
        start_x, start_y = gesture.get_start_point()
        end_x = start_x + offset_x
        end_y = start_y + offset_y

        xpos = int(start_x)
        ypos = int(start_y)
        apos = int(end_x)
        bpos = int(end_y)

        # Normalize coordinates
        coordinates = [0, 0, 1, 1]
        if xpos <= apos and ypos <= bpos:
            coordinates = [xpos, ypos, apos, bpos]
        elif xpos >= apos and ypos >= bpos:
            coordinates = [apos, bpos, xpos, ypos]
        elif xpos <= apos and ypos >= bpos:
            coordinates = [xpos, bpos, apos, ypos]
        elif xpos >= apos and ypos <= bpos:
            coordinates = [apos, ypos, xpos, bpos]

        self.displayCoordinates(coordinates)
        self.needleCoordinates = coordinates
        self.rectangle = coordinates.copy()

    def on_picture_key_pressed(self, controller, keyval, keycode, state):
        """Handle arrow keys for resizing the area."""
        self.getCoordinates()

        shift = state & Gdk.ModifierType.SHIFT_MASK
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        alt = state & Gdk.ModifierType.ALT_MASK

        # Determine step size and which coordinates to modify
        if ctrl and shift and alt:
            step = 25
            x, y = 0, 1
        elif ctrl and shift:
            step = 5
            x, y = 0, 1
        elif ctrl:
            step = 1
            x, y = 0, 1
        elif alt:
            step = 25
            x, y = 2, 3
        elif shift:
            step = 5
            x, y = 2, 3
        else:
            step = 1
            x, y = 2, 3

        # Modify coordinates based on arrow key
        if keyval == Gdk.KEY_Left:
            self.needleCoordinates[x] -= step
        elif keyval == Gdk.KEY_Right:
            self.needleCoordinates[x] += step
        elif keyval == Gdk.KEY_Up:
            self.needleCoordinates[y] -= step
        elif keyval == Gdk.KEY_Down:
            self.needleCoordinates[y] += step
        else:
            return False

        self.displayCoordinates(self.needleCoordinates)
        self.rectangle = self.needleCoordinates.copy()
        self.pictureField.queue_draw()
        return True

    def wrapquit(self, event=None):
        self.window.close()

    def returnPath(self, image):
        """Create a full path from working directory and image name."""
        return os.path.join(self.directory, image)

    def readimages(self, event=None):
        """Read png images from the given directory and create a list of their names."""
        self.images = []

        dialog = Gtk.FileDialog()
        dialog.select_folder(None, None, self.on_folder_selected)

    def on_folder_selected(self, dialog, result):
        """Callback when a folder is selected."""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.directory = folder.get_path()
                for file in os.listdir(self.directory):
                    if file.endswith(".png"):
                        self.images.append(file)

                if len(self.images) == 1:
                    self.show_info_dialog("Found images", "Found 1 image in the selected directory.")
                else:
                    self.show_info_dialog("Found images", f"Found {len(self.images)} images in the selected directory.")

                self.imageCount = 0
                try:
                    self.imageName = self.images[0]
                    self.displayImage(self.returnPath(self.imageName))
                except IndexError:
                    pass
        except Exception as e:
            pass

    def selectfile(self, event=None):
        """Reads in an image file and shows it for editing."""
        dialog = Gtk.FileDialog()
        dialog.open(None, None, self.on_file_selected)

    def on_file_selected(self, dialog, result):
        """Callback when a file is selected."""
        try:
            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                self.directory = os.path.dirname(path)
                image = os.path.basename(path)
                if 'json' in image:
                    prefix = image.split('.')[0]
                    image = prefix + '.png'
                self.imageName = image
                self.imageCount = 0
                path = os.path.join(self.directory, image)
                self.displayImage(path)
        except Exception as e:
            pass

    def displayImage(self, path):
        """Display image on the canvas."""
        try:
            self.picture = Image.open(path)
            self.picsize = (self.picture.width, self.picture.height)

            # Load pixbuf
            self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)

            # Update drawing area size
            self.pictureField.set_size_request(self.pixbuf.get_width(), self.pixbuf.get_height())

            self.nameEntry.set_text(self.imageName)
            self.pictureField.queue_draw()
            self.pictureField.grab_focus()
        except Exception as e:
            self.show_error_dialog("Error", f"Failed to load image: {str(e)}")

    def nextImage(self, event=None):
        """Display next image on the list."""
        self.imageCount += 1
        try:
            self.imageName = self.images[self.imageCount]
            noimage = False
        except IndexError:
            if len(self.images) != 0:
                self.imageName = self.images[0]
                self.imageCount = 0
                noimage = False
            else:
                self.show_error_dialog("Error", "No images are loaded. Select an image first.")
                noimage = True

        if not noimage:
            self.rectangle = None
            self.displayImage(self.returnPath(self.imageName))

    def prevImage(self, event=None):
        """Display previous image on the list."""
        self.imageCount -= 1
        try:
            self.imageName = self.images[self.imageCount]
            noimage = False
        except IndexError:
            if len(self.images) != 0:
                self.imageName = self.images[-1]
                self.imageCount = len(self.images)
                noimage = False
            else:
                self.show_error_dialog("Error", "No images are loaded. Select an image first.")
                noimage = True

        if not noimage:
            self.rectangle = None
            self.displayImage(self.returnPath(self.imageName))

    def getCoordinates(self):
        """Read coordinates from the coordinate windows."""
        xpos = None
        apos = None
        try:
            xpos = int(self.axEntry.get_text())
            ypos = int(self.ayEntry.get_text())
            apos = int(self.bxEntry.get_text())
            bpos = int(self.byEntry.get_text())
        except ValueError:
            self.show_error_dialog("Error", "Cannot operate without valid coordinates.")

        if not xpos and not apos:
            self.needleCoordinates = [0, 0, 100, 200]
        else:
            self.needleCoordinates = [xpos, ypos, apos, bpos]

    def calculateSize(self, coordinates):
        """Calculate size of the area from its coordinates."""
        width = int(coordinates[2]) - int(coordinates[0])
        heigth = int(coordinates[3]) - int(coordinates[1])
        return [width, heigth]

    def showArea(self, event=None):
        """Load area and draw a rectangle around it."""
        self.area = self.needle.provideNextArea()
        try:
            self.needleCoordinates = [self.area[0], self.area[1], self.area[2], self.area[3]]
            typ = self.area[4]
            self.rectangle = self.needleCoordinates.copy()
            self.rectangles.append(self.rectangle)
            self.displayCoordinates(self.needleCoordinates)

            # Set the combo box
            if typ == "match":
                self.typeList.set_selected(0)
            elif typ == "ocr":
                self.typeList.set_selected(1)
            elif typ == "exclude":
                self.typeList.set_selected(2)

            self.pictureField.queue_draw()
        except (TypeError, AttributeError):
            self.rectangles = []
            self.pictureField.queue_draw()

    def displayCoordinates(self, coordinates):
        """Display coordinates in the GUI"""
        self.axEntry.set_text(str(coordinates[0]))
        self.ayEntry.set_text(str(coordinates[1]))
        self.bxEntry.set_text(str(coordinates[2]))
        self.byEntry.set_text(str(coordinates[3]))

        size = self.calculateSize(coordinates)
        self.widthEntry.set_text(str(size[0]))
        self.heigthEntry.set_text(str(size[1]))

    def modifyArea(self, event=None):
        """Update the information for the active needle area, including properties, tags, etc."""
        self.getCoordinates()
        xpos = self.needleCoordinates[0]
        ypos = self.needleCoordinates[1]
        apos = self.needleCoordinates[2]
        bpos = self.needleCoordinates[3]
        # Get selected type from DropDown
        selected_index = self.typeList.get_selected()
        type_options = ["match", "ocr", "exclude"]
        typ = type_options[selected_index]

        # Get properties
        prop_buffer = self.propText.get_buffer()
        props = prop_buffer.get_text(prop_buffer.get_start_iter(), prop_buffer.get_end_iter(), False)
        if "\n" in props:
            props = props.split("\n")
        if props == "":
            props = []

        # Get tags
        tags_buffer = self.textField.get_buffer()
        tags = tags_buffer.get_text(tags_buffer.get_start_iter(), tags_buffer.get_end_iter(), False)
        if "\n" in tags:
            tags = tags.split("\n")
        if tags == "":
            tags = []

        coordinates = [xpos, ypos, apos, bpos, typ]
        self.needle.update(coordinates, tags, props)

        # Update JSON display
        json_buffer = self.textJson.get_buffer()
        json_buffer.set_text("")
        json_text = self.needle.provideJson()
        json_buffer.set_text(json.dumps(json_text, indent=2))

        self.rectangle = self.needleCoordinates.copy()
        self.pictureField.queue_draw()

    def addAreaToNeedle(self, event=None):
        """Add new area to needle. The needle can have more areas."""
        self.needle.addArea()
        self.modifyArea(None)
        areas = self.needle.provideAreaCount()
        self.needleEntry.set_text(str(areas))

    def removeAreaFromNeedle(self, event=None):
        """Remove the active area from the needle (deletes it)."""
        self.needle.removeArea()
        areas = self.needle.provideAreaCount()
        coordinates = [0, 0, 0, 0]
        self.displayCoordinates(coordinates)
        self.needleEntry.set_text(str(areas))

        json_buffer = self.textJson.get_buffer()
        json_text = self.needle.provideJson()
        json_buffer.set_text(json.dumps(json_text, indent=2))

        self.rectangle = None
        self.pictureField.queue_draw()
        self.showArea(None)

    def loadNeedle(self, event=None):
        """Load the existing needle information from the file and display them in the window."""
        if self.imageName is not None:
            jsonfile = self.returnPath(self.imageName).replace(".png", ".json")
            self.handler = fileHandler(jsonfile)
            self.handler.readFile()
            jsondata = self.handler.provideData()

            self.needle = needleData(jsondata)

            # Update properties
            properties = self.needle.provideProperties()
            prop_buffer = self.propText.get_buffer()
            prop_buffer.set_text(properties)

            # Update tags
            tags = self.needle.provideTags()
            tags_buffer = self.textField.get_buffer()
            tags_buffer.set_text(tags)

            # Update JSON
            json_text = self.needle.provideJson()
            json_buffer = self.textJson.get_buffer()
            json_buffer.set_text(json.dumps(json_text, indent=2))

            # Update areas count
            areas = self.needle.provideAreaCount()
            self.needleEntry.set_text(str(areas))

            self.rectangle = None
            self.showArea(None)
        else:
            self.show_error_dialog("Error", "No images are loaded. Select image directory first.")

    def createNeedle(self, event=None):
        """Write out the json file for the actual image to store the needle permanently."""
        jsondata = self.needle.provideJson()
        filename = self.nameEntry.get_text().replace(".png", ".json")
        path = self.returnPath(filename)
        if self.handler is None:
            self.handler = fileHandler(path)
        self.handler.acceptData(jsondata)
        self.handler.writeFile(path)
        self.rectangle = None
        self.pictureField.queue_draw()

    def renameFile(self, event=None):
        """ Rename the needle PNG file with the top placed tag. """
        tags_buffer = self.textField.get_buffer()
        tags_text = tags_buffer.get_text(tags_buffer.get_start_iter(), tags_buffer.get_end_iter(), False)
        tags = tags_text.split("\n")
        future_name = tags[0]

        if future_name and self.imageName:
            future_name = f"{future_name}.png"
            current = self.returnPath(self.imageName)
            new = os.path.join(self.directory, future_name)
            try:
                os.rename(current, new)
                self.imageName = future_name
                self.nameEntry.set_text(future_name)
                self.show_info_dialog("Success", "The PNG file has been renamed.")
            except Exception as e:
                self.show_error_dialog("Error", str(e))
        elif not future_name:
            self.show_error_dialog("Error", "No tags available to rename the file. Leaving it unchanged.")
        elif not self.imageName:
            self.show_error_dialog("Error", "No image loaded. Load an image first!")

    def show_connect_VM(self, event=None):
        """ Show a dialogue to connect to a VM """
        dialog = Gtk.Window()
        dialog.set_title('Connect to a VM')
        dialog.set_transient_for(self.window)
        dialog.set_modal(True)
        dialog.set_default_size(300, 100)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        dialog.set_child(box)

        label = Gtk.Label(label='Choose a VM:')
        box.append(label)

        # Get the domain names from the kvm hypervisor
        domains = []
        try:
            self.kvm = libvirt.open("qemu:///session")
            domains = [x.name() for x in self.kvm.listAllDomains()]
            if len(domains) == 0:
                self.show_error_dialog("No domains found", "Either the hypervisor is not running or no VMs available in the qemu:///session.")
                domains = []
        except libvirt.libvirtError:
            self.show_error_dialog("Error", "Failed to open connection to the hypervisor.")
            domains = []

        if not domains:
            domains = ["No VMs available"]

        combo = Gtk.DropDown.new_from_strings(domains)
        combo.set_selected(0)
        box.append(combo)

        connect_btn = Gtk.Button(label="Connect")
        connect_btn.connect('clicked', lambda btn: self.connect(combo, dialog, domains))
        box.append(connect_btn)

        dialog.present()

    def connect(self, combo, dialog, domains):
        """ Update the status variable to let the application know about the VM. """
        selected_index = combo.get_selected()
        selected = domains[selected_index] if selected_index < len(domains) else None
        if not selected or selected == "No VMs available":
            self.show_error_dialog("No VM selected", "Please, select one of the available VMs.")
            return

        self.virtual_machine = selected
        self.vmEntry.set_text(self.virtual_machine)
        dialog.close()

    def takeScreenshot(self, event=None):
        """ Take the screenshot from the running virtual machine. """
        if not self.virtual_machine:
            self.show_error_dialog("No VM connected", "Connect a VM before you try taking screenshots from it. Use the CTRL-V key shortcut.")
            return

        # Get the domain object
        domain = self.kvm.lookupByName(self.virtual_machine)
        stream = self.kvm.newStream()
        image_type = domain.screenshot(stream, 0)

        # Collect the stream data
        image_data = io.BytesIO()
        part_stream = stream.recv(8192)
        while part_stream != b'':
            image_data.write(part_stream)
            part_stream = stream.recv(8192)

        # Convert and save the image
        image_data.seek(0)
        image = Image.open(image_data)
        image.save("screenshot.png", 'PNG')
        image_data.close()
        stream.finish()

        path = os.path.join(os.path.abspath('.'), 'screenshot.png')
        self.imageName = "screenshot.png"
        self.displayImage(path)

        tags_buffer = self.textField.get_buffer()
        tags_buffer.set_text(self.imageName)

    def show_info_dialog(self, title, message):
        """Show an information dialog."""
        dialog = Gtk.AlertDialog()
        dialog.set_message(title)
        dialog.set_detail(message)
        dialog.show(self.window)

    def show_error_dialog(self, title, message):
        """Show an error dialog."""
        dialog = Gtk.AlertDialog()
        dialog.set_message(title)
        dialog.set_detail(message)
        dialog.show(self.window)

#-----------------------------------------------------------------------------------------------

class fileHandler:
    def __init__(self, jsonfile):
        self.jsonData = {"properties": [],
                         "tags": [],
                         "area": []}
        self.jsonfile = jsonfile

    def readFile(self):
        """Read the json file and create the data variable with the info."""
        try:
            with open(self.jsonfile, "r") as inFile:
                self.jsonData = json.load(inFile)
        except FileNotFoundError:
            if self.jsonfile != "empty":
                print("Error: No needle exists. Create one.")
            else:
                print("Error: No images are loaded. Select image directory.")

    def writeFile(self, jsonfile):
        """Take the data variable and write is out as a json file."""
        with open(jsonfile, "w") as outFile:
            json.dump(self.jsonData, outFile, indent=2)
        print("Info: The needle has been written out.")

    def provideData(self):
        """Provide the json file."""
        return self.jsonData

    def acceptData(self, jsondata):
        """Update the data in data variable."""
        self.jsonData = jsondata

class needleData:
    def __init__(self, jsondata):
        self.jsonData = jsondata
        self.areas = self.jsonData["area"]
        self.areaPos = 0

    def provideJson(self):
        """Provide the json data (for the GUI)."""
        return self.jsonData

    def provideProperties(self):
        """Provide properties."""
        properties = "\n".join(self.jsonData["properties"])
        return properties

    def provideTags(self):
        """Provide tags."""
        tags = "\n".join(self.jsonData["tags"])
        return tags

    def provideNextArea(self):
        """Provide information about the active area and move pointer to the next area for future reference."""
        try:
            area = self.areas[self.areaPos]
            xpos = area["xpos"]
            ypos = area["ypos"]
            wide = area["width"]
            high = area["height"]
            typ = area["type"]
            apos = xpos + wide
            bpos = ypos + high
            areaData = [xpos, ypos, apos, bpos, typ]
            self.areaPos += 1
            return areaData
        except (IndexError, KeyError):
            print("Error: No more area in the needle.")
            return None

    def update(self, coordinates, tags, props):
        """Update all information taken from the GUI in the data variable."""
        xpos = coordinates[0]
        ypos = coordinates[1]
        apos = coordinates[2]
        bpos = coordinates[3]
        typ = coordinates[4]
        wide = int(apos) - int(xpos)
        high = int(bpos) - int(ypos)
        area = {"xpos":xpos, "ypos":ypos, "width":wide, "height":high, "type":typ}
        if type(props) != list:
            props = [props]
        if type(tags) != list:
            tags = [tags]
        self.jsonData["properties"] = props
        self.jsonData["tags"] = tags

        try:
            self.areas[self.areaPos-1] = area
        except IndexError:
            print("Error: Cannot modify non-existent area. Add area first!")
        self.jsonData["area"] = self.areas

    def addArea(self):
        """Add new area to the needle (at the end of the list)."""
        self.areas.append("newarea")
        self.areaPos = len(self.areas)

    def removeArea(self):
        """Remove the active area from the area list."""
        try:
            deleted = self.areas.pop(self.areaPos-1)
            self.jsonData["area"] = self.areas
            self.areaPos -= 2
        except IndexError:
            print("Error: No area in the needle. Not deleting anything.")

    def provideAreaCount(self):
        """Provide the number of the areas in the needle."""
        return len(self.areas)


#-----------------------------------------------------------------------------------------------

def main(path=None):

    try:
        path = sys.argv[1]
    except IndexError:
        pass

    app = Application(cli_path=path)
    app.run()


if __name__ == '__main__':
    main()
