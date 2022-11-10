ftype PythonScript=C:\Program Files\Python37\python.exe "%1" %*
ftype PythonScript

assoc .py=PythonScript
assoc .py

@rem use 'call' to invoke external script; otherwise, the current script will exit after the external script
call addpath PATHEXT .PY
echo PATHEXT=%PATHEXT%


@echo.
@echo. you still need to go to Settings - Apps - Default Apps - Choose Default Apps to file type - .py - link Python (not python, lowercase, which is python 2)
