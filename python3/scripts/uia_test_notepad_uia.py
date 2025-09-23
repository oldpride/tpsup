#!/usr/bin/env python

# usage: python pwa_test_notepad.py
import datetime
import os
from pywinauto.application import Application

# from pywinauto.controls.win32_controls import 
from time import sleep
from tpsup.pwatools_old import dump_window

app = Application(
    # backend="win32", # win32 is the default.
    backend="uia", # uia is modern and preferred.
)

file_name = "tianjunk.txt"
title_pattern = f".*{file_name}.*"
print(f"Connecting to Notepad window with 'title_re=\"{title_pattern}\"'...")
try: 
    app.connect(title_re=title_pattern, timeout=10)  # Connect to the Notepad window
except Exception as e:
    file = os.path.expandvars(f"%USERPROFILE%/{file_name}")
    cmd = f"notepad.exe {file}"

    print(f"Failed to connect to Notepad window with 'title_re=\"{title_pattern}\"'.")
    print(f"Exception={e}")
    print(f"we will start it with command: {cmd}")
    
    # if the file doesn't exist, notepad will prompt to create a new file.
    # so to automate the test, we create the file using "touch" if the
    # file doesn't exist.
    if not os.path.exists(file):
        print(f"file {file} doesn't exist. creating it.")
        from pathlib import Path
        file_path = Path(file)
        file_path.touch()
    app.start(cmd, wait_for_idle=False)
    app.connect(title_re=title_pattern, timeout=10)

print(f"Connected")
print(f"\ndir(app) = {dir(app)}")
print(f"\napp.print_control_identifiers()")
# app.print_control_identifiers() # Application's doesn't have print_control_identifiers method.
print(f"\napp.windows() = {app.windows()}")

# the following methods work:
# notepad_window = app.Document # method 1.
# notepad_window = app.window(class_name="Notepad", title_re=".*tianjunk.*") # method 2.
notepad_window = app.top_window() # method 3. this is the most general method.

print(f"\nnotepad_window's python class name={type(notepad_window).__name__}")
print(f"\ndir(notepad_window) = {dir(notepad_window)}")
print(f"\nnotepad_window.print_control_identifiers()")
notepad_window.print_control_identifiers()

notepad_window.wait('visible')
notepad_window.click_input()
sleep(1)
dump_window(notepad_window)

exit(0)

'''
   | Pane - ''    (L1250, T75, R1914, B482)
   | ['Pane', 'tianjunk.txtPane', 'Pane0', 'Pane1', 'tianjunk.txtPane0', 'tianjunk.txtPane1']
   |    |
   |    | Document - 'hello'    (L1250, T75, R1914, B482)
   |    | ['helloDocument', 'Document', 'hello']
   |    | child_window(title="hello", control_type="Document")

note: 'hello' is the text in the notepad window, not the title.
'''

# either of the following works
# text_window = notepad_window.Document
text_window = notepad_window.child_window(control_type="Document")
'''
wrapper vs window
    Actual window lookup is performed by wrapper_object() method. 
    It returns some wrapper for the real existing window/control 
    or raises ElementNotFoundError. This wrapper can deal with the 
    window/control by sending actions or retrieving data.

    But Python can hide this wrapper_object() call so that you have 
    more compact code in production.

    therefore, the following two methods are equivalent:
''' 

# method 1.
# text_wrapper = text_window.wrapper_object()
# text_wrapper.click_input()

# method 2.
text_window.click_input()  # click to focus the text area

dump_window(text_window)

# to move cursor to the end of the current text, we
# need to count the number of lines in the text.
old_text = text_window.texts()
print(f"\nold_text={old_text}")
# ['hello\rworld\r\rhi\rhere\r\r\r']

# then use DOWN arrow key to move the cursor to the last line.
line_count = old_text[0].count('\r') + 1
for i in range(line_count):
    text_window.type_keys("{DOWN}", pause=0.05)

# at last, mve the cursor to the end of the last line
text_window.type_keys("{END}", pause=0.05)

# type hello YYYY-MM-DD HH:MM:SS in local time
# using {END}{ENTER} to move to the end of the current line and add a
yyyymmdd_HHMMSS = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
new_text = "{END}{ENTER}" + f"current time={yyyymmdd_HHMMSS}" + "{ENTER}"
print(f"\nnew_text={new_text}")


# slow down typing with pause=0.1 (second); otherwise, some keys may be dropped.
text_window.type_keys(new_text, with_spaces=True, pause=0.1)

'''
   |    |    |    | MenuItem - 'Edit'    (L1303, T42, R1347, B74)
   |    |    |    | ['Edit', 'EditMenuItem', 'MenuItem2']
   |    |    |    | child_window(title="Edit", auto_id="Edit", control_type="MenuItem")
'''
menu_edit_window = notepad_window.child_window(title="Edit", auto_id="Edit", control_type="MenuItem")
# menu_edit_wrapper = menu_edit_window.wrapper_object()
# click_input() vs set_focus().
#     click_input() is more realistic, as it simulates a mouse click.
menu_edit_window.click_input()
menu_edit_window.set_focus()
sleep(1)
dump_window(menu_edit_window)
dump_window(notepad_window)

# the following doesn't work because Edit->TimeDate is in
# notepad_window's menu, not menu_edit_window's menu.
# menu_edit_window.menu_select("Time/Date") # this doesn't work

# the following doesn't work either. see error below.
# notepad_window.menu_select("Edit->Time/Date") # this doesn't work
r'''
Traceback (most recent call last):
  File "C:\Users\tian\sitebase\github\tpsup\python3\scripts\pwa_test_notepad_uia.py", line 141, in <module>
    notepad_window.menu_select("Edit->Time/Date") # this doesn't work
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\tian\sitebase\python3\venv\Windows\win10-python3.12\Lib\site-packages\pywinauto\controls\uiawrapper.py", line 723, in menu_select
    menu.item_by_path(path, exact).select()
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\tian\sitebase\python3\venv\Windows\win10-python3.12\Lib\site-packages\pywinauto\controls\uia_controls.py", line 1051, in item_by_path
    menu = next_level_menu(self, menu_items[0], items_cnt == 1)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\tian\sitebase\python3\venv\Windows\win10-python3.12\Lib\site-packages\pywinauto\controls\uia_controls.py", line 1044, in next_level_menu
    return self._sub_item_by_text(parent_menu, item_name, exact, is_last)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\tian\sitebase\python3\venv\Windows\win10-python3.12\Lib\site-packages\pywinauto\controls\uia_controls.py", line 1006, in _sub_item_by_text
    sub_item = findbestmatch.find_best_match(name, texts, items)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\tian\sitebase\python3\venv\Windows\win10-python3.12\Lib\site-packages\pywinauto\findbestmatch.py", line 133, in find_best_match
    raise MatchError(items = text_item_map.keys(), tofind = search_text)
pywinauto.findbestmatch.MatchError: Could not find 'Edit' in 'dict_keys(['Undo', 'Cut', 'Copy', 'Paste', 'Delete', 'Clear formatting', 'Define with Bing', 'Find', 'Find next', 'Find previous', 'Replace', 'Go to', 'Select all', 'Time/Date', 'Font'])'

    how can I get current text_item_map? Is there a way to dump it?
'''

r'''
the following sub menu will show in notepad_window.print_control_identifiers() only
after clicking the Edit menu to open the menu.
   |    |    |    |    | MenuItem - 'Time/Date'    (L1308, T520, R1530, B549)
   |    |    |    |    | ['MenuItem14', 'Time/Date', 'Time/DateMenuItem', 'Time/Date0', 'Time/Date1']
   |    |    |    |    | child_window(title="Time/Date", control_type="MenuItem")
   |    |    |    |    |    |
   |    |    |    |    |    | Static - 'Time/Date'    (L1319, T525, R1449, B544)
   |    |    |    |    |    | ['Time/Date2', 'Time/DateStatic', 'Static14']
   |    |    |    |    |    | child_window(title="Time/Date", auto_id="TextBlock", control_type="Text")
'''
# the following methods work:
# method 1.
# notepad_window.menu_select("Time/Date") # this works

# method 2.
time_button_window = notepad_window.child_window(title="Time/Date", control_type="MenuItem")
time_button_window.click_input()

# click away
notepad_window.click_input()  # click away to close the menu
sleep(1)
