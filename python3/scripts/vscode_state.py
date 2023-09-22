import sqlite3
import json
from pprint import pprint, pformat

import tpsup.envtools

myenv = tpsup.envtools.Env()
homedir = tpsup.envtools.get_home_dir()

if myenv.isWindows:
    file = f'{homedir}/AppData/Roaming/Code/User/globalStorage/state.vscdb'
elif myenv.isMac:
    file = f'{homedir}/Library/Application Support/Code/User/globalStorage/state.vscdb'
else:
    # assume linux
    file = f'{homedir}/.config/Code/User/globalStorage/state.vscdb'

print(f'file={file}')
print()

connection = sqlite3.connect(file)

cursor = connection.cursor()

result_list = cursor.execute("SELECT * FROM ItemTable;").fetchall()
# list of key-value tuples
print(pformat(result_list))

# python vscode_state.py
# this prints key-value tuples
