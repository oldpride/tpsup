#!/usr/bin/env python

# usage: python pwa_test_notepad.py

from pywinauto.application import Application
from time import sleep

app = Application(
    # backend="win32", # win32 is the default.
    backend="uia", # uia is modern and preferred, but doesn't work for notepad on windows 11
    ).start("notepad.exe", wait_for_idle=False)
sleep(3)
app.connect(title_re=".*Notepad", timeout=10)  # Connect to the Notepad window

# 2. Access a window within the application
# You can access windows by their title or by using child_window.
# 'UntitledNotepad' is the default title for a new Notepad window.
notepad_window = app.UntitledNotepad
notepad_window.wait('visible')
sleep(1)  # Wait for the window to be ready

print(f"\ndir(notepad_window) = {dir(notepad_window)}\n")
print(f"\nnotepad_window.print_control_identifiers()")
notepad_window.print_control_identifiers()
print(f"\nnotepad_window.__dict__ = {notepad_window.__dict__}\n")

# edit_menu = notepad_window.child_window(title="Edit", auto_id="Edit", control_type="MenuItem").wrapper_object()
# print(f"dir(edit_menu) = {dir(edit_menu)}\n")
# print(f"edit_menu.__dict__ = {edit_menu.__dict__}\n")
# print(f"edit_menu.print_control_identifiers()")
# edit_menu.click_input()  # Click the Edit menu to open it
# # edit_menu.wait('visible')
# notepad_window.child_window(title="Edit", auto_id="Edit", control_type="MenuItem").wait('visible')
# # sleep(1)
# # edit_menu.print_control_identifiers()
# # edit_menu.menu_select("Edit->Time/Date")  # Select the Time/Date option from the Edit menu
# edit_menu.type_keys("{F5}") # this works
# sleep(1)
# edit_menu.type_keys("{ESC}")
# sleep(1)
file_menu = notepad_window.child_window(title="File", auto_id="File", control_type="MenuItem")
file_menu_wrapper = file_menu.wrapper_object()
file_menu.wait('visible')
# close the tab
file_menu_wrapper.click_input()
sleep(1)
file_menu_wrapper.menu_select("File->Closetab")  # Select the Close option from the File menu
sleep(1)


exit(0)

# menu = notepad_window.child_window(control_type="MenuBar")
# print(f"\nmenu.print_control_identifiers()")
# menu.print_control_identifiers()


# 3. Interact with controls within the window
# This example types text into the main edit control of Notepad.
# notepad_window.Edit.type_keys("Hello from pywinauto!", with_spaces=True)
# print(f"before click Edit")
# # sleep(2)
# # notepad_window.Edit.type_keys("Time/jDate", with_spaces=True)
# # notepad_window.menu_select('Edit->Time/Date')


# print(f"\ndir(notepad_window.Edit) = {dir(notepad_window.Edit)}\n")
# print(f"\nnotepad_window.Edit.print_control_identifiers()")
# notepad_window.Edit.print_control_identifiers()

# notepad_window.ContentTextBlock.type_keys("hello")
# notepad_window.Static4.type_keys("hello")
# notepad_window.UntitledPane.type_keys("hello 1", with_spaces=True)
# notepad_window.UntitledPane2.type_keys("hello 2", with_spaces=True) # tab header
# notepad_window.UntitledPane3.type_keys("hello 3", with_spaces=True) # tab header
# notepad_window.UntitledPane4.type_keys("hello 4", with_spaces=True) # new tab
# notepad_window.UntitledPane5.type_keys("hello 5", with_spaces=True) # file new tab

# notepad_window.Pane.type_keys("hello Pane1", with_spaces=True)
# notepad_window.Pane2.type_keys("hello Pane2", with_spaces=True)
# notepad_window.Pane3.type_keys("hello Pane3", with_spaces=True)
# notepad_window.Pane4.type_keys("hello Pane4", with_spaces=True)
# notepad_window.Pane5.type_keys("hello Pane5", with_spaces=True)

# print("typed hello")
# sleep(5)
# notepad_window.close()
# exit(0)

# notepad_window.Edit.click_input()
# notepad_window.Edit.menu_select('Paste')
# notepad_window.Edit.type_keys("Hello from pywinauto!", with_spaces=True)
# notepad_window.Edit.set_text("Hello from pywinauto using set_text!")

w = None
for window in app.windows():
    print(f"window = {window}, title = {window.window_text()}")
    print(f"window.__dict__ = {window.__dict__}\n")
    print(f"dir(window) = {dir(window)}\n")
    if 'MenuItems' in dir(window):
        print(f"window.menu_items() = {window.menu_items()}")

    # w = window

# print(f"w.texts = {w.texts()}")
# texts = w.texts()
# print(f"dir(texts) = {dir(texts)}")
# print(f"texts.__dict__ = {texts.__dict__}\n")


notepad_window.close()
exit

# main_window = app.top_window()
# menu_bar = main_window.child_window(control_type="MenuBar") # Or similar identification

# for menu_item in menu_bar.children():
#     print(menu_item.texts()) # Prints the text of the menu item

# sleep(2)
# notepad_window.menu_select('Edit->Time/Date')
# app.close()  # Close the application
# # 4. Perform menu actions
# # This selects "Edit" then "Time/Date" from the menu.
# notepad_window.menu_select('Edit->Time/Date')
# notepad_window
    
# # 5. Interact with a newly opened dialog (About Notepad)
# # Access the "About Notepad" dialog and click its "OK" button.
# app.AboutNotepad.OK.click()

# # 6. Close the application (optional, but good practice for automation)
# # You might want to save changes or close without saving depending on your needs.
# # For this example, we'll close without saving.
# notepad_window.close()
# # Handle the "Do you want to save changes?" dialog if it appears
# try:
#     notepad_window.DonTSave.click()
# except Exception:
#     pass # No save dialog appeared, or it was already handled



# for i in range(10):
#     notepad_window.menu_select('View->Zoom->Zoom In')
#     sleep(1)
# notepad_window.Edit.type_keys('\r\nthis is really cool!', with_spaces="true")
# notepad_window.Edit.type_keys('\r\nThis is also cool!', with_spaces="true")
