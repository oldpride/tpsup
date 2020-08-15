@echo off
wmic process where (ParentProcessId=%*) get Caption,ProcessId
