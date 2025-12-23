# ask_for_image.py
# Handles asking user for image file and copying it to images/ directory
# using tinkinter  for GUI dialog if available, else console input.
# Also ensures safe filenames and avoids overwrites.
# Returns the saved filename or None on cancel/error.

# Imports 

import tkinter as tk
from tkinter.filedialog import askopenfilename
import os
import shutil
import re
from pathlib import Path

class Colors:
    BLUE = '\033[94m'
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'

# Function to ask for Excel file
def ask_excel_file_dialog():
        """
        Open a file dialog to pick an Excel file. Falls back to console input
        if tkinter is not available (e.g. headless server).
        Returns selected file path or None.
        """
        try: # GUI dialog
            root = tk.Tk() # Initialize TK
            root.withdraw() # Hide main window
            path = askopenfilename(title="Select Excel file", filetypes=[("Excel files","*.xlsx *.xls")]) # Open dialog
            root.destroy() # Clean up TK
            if path: # If user selected a file
                return path # Return the path
        except Exception:
            # If tkinter is not available or fails (e.g., headless), fall back to console
            pass

        # Fallback: ask in console
        path = input(f"{Colors.BLUE}Enter Excel filename to import (or full path): {Colors.RESET}").strip()
        return path if path else None

# Helper to make safe filenames
def _safe_basename(name: str) -> str:
    """Make a filesystem-safe base name (no directory, no special chars)."""
    name = os.path.basename(name)# get base name only from path geven
    name = re.sub(r'[^\w\-. ]', '_', name).strip() # replace unsafe chars by underscore and trim before and after spaces
    name = name.replace(' ', '_')# replace spaces with underscores
    return name or 'image' # default name if empty 


def ask_image_file_dialog(current_image_name: str, dest_dir: str = "images"):
    """
    Let user pick an image file and copy it into dest_dir using current_image_name as base.
    - If current_image_name is empty/None -> do nothing (return None).
    - Returns the relative filename saved in dest_dir (e.g. "sugar.jpg") or None on cancel/error.
    """
    if not current_image_name:
        # Don't open dialog until a name exists in the IMAGE column
        print(f"{Colors.YELLOW}⚠ Please enter an image name in the IMAGE column first.{Colors.RESET}")
        return None

    allowed_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'} # supported image types
    Path(dest_dir).mkdir(parents=True, exist_ok=True)# ensure dest_dir exists

    try:
        # GUI dialog if available
        root = tk.Tk()# Initialize TK
        root.withdraw()# Hide main window
        selected = askopenfilename(title="Select image file",
                                   filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")]) # Open dialog
        root.destroy()# Clean up TK
    except Exception:
        selected = None

    # Fallback to console input if GUI not used or cancelled
    if not selected:
        # Don't prompt again — try to use an existing file in dest_dir that matches the IMAGE name.
        base = _safe_basename(current_image_name) # safe base name
        base_no_ext = os.path.splitext(base)[0]# name without extension
        found = None
        for ext in allowed_exts:# check all allowed extensions
            candidate = Path(dest_dir) / f"{base_no_ext}{ext}" # construct candidate path
            if candidate.exists():  # if file exists
                found = str(candidate) # found existing file
                break
        if found:
            selected = found # use found file
        else:# no file found, inform user and return None
            print(f"{Colors.BLUE}No image selected and no default found for '{current_image_name}'.{Colors.RESET}")
            return None

    if not os.path.exists(selected): # sanity check
        print(f"{Colors.RED}❌ File not found: {selected}{Colors.RESET}")# error message file not found
        return None

    ext = os.path.splitext(selected)[1].lower() # get extension of selected file
    if ext not in allowed_exts: # check if extension is allowed
        print(f"{Colors.RED}❌ Unsupported image type: {ext}{Colors.RESET}") # error message unsupported type
        return None

    base = _safe_basename(current_image_name)# safe base name from provided IMAGE name
    # If provided name already has an allowed extension, keep it; otherwise append selected ext
    provided_ext = os.path.splitext(base)[1].lower()
    if provided_ext in allowed_exts:
        filename = base
    else:
        filename = f"{os.path.splitext(base)[0]}{ext}"

    # avoid overwrite by adding counter if needed
    dest_path = Path(dest_dir) / filename
    counter = 1
    while dest_path.exists():
        filename = f"{os.path.splitext(filename)[0]}_{counter}{ext}"
        dest_path = Path(dest_dir) / filename
        counter += 1

    try:
        shutil.copy2(selected, dest_path)
        print(f"{Colors.GREEN}✓ Image saved to: {dest_path}{Colors.RESET}")
        # Return just the filename (suitable for storing in Excel IMAGE column)
        return filename
    except Exception as e:
        print(f"{Colors.RED}❌ Failed to copy image: {e}{Colors.RESET}")
        return None