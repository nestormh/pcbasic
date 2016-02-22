@echo off
rem  Use this batch file to run the Brewer software without a Brewer
rem  connected.  DO NOT USE with Brewer connected since motors may
rem  move improperly.

rem *
rem * Change to the Brewer directory to ensure correct operation (full path)
rem *
C:
cd C:\Users\Néstornillador\Documents\brewer\brewer\pcbasic\brewer_tests\BrewerSoft-4.1\BrewerSoft-f17b3a98b024e921
rem *
rem * Set the BREWDIR environment variable to the proper directory (full path)
rem *
set NOBREW=1
set BREWDIR=C:\Users\Néstornillador\Documents\brewer\brewer\pcbasic\brewer_tests\BrewerSoft-4.1\BrewerSoft-f17b3a98b024e921
setdate
rem *
rem * Change the prompt as a reminder that the Brewer software is running
rem *
PROMPT Brewer $P$G

rem *
rem * Run the Brewer software
rem *
rem Comando Original
rem gwbasic main /f:10

pcbasic -t main.asc --com1=PORT:COM1 --mount=C:C:\Users\Néstornillador\Documents\brewer\brewer\pcbasic\brewer_tests -f=10

rem Indefined line number in 45
rem pcbasic -t MAIN.BAS --com1=PORT:COM1 --mount=C:../.. -f=10

rem Se cierra inesperadamente en o3 Observation
rem pcbasic -t main-pcb.asc --com1=PORT:COM1 --mount=C:../.. -f=10
rem pcbasic -t main --com1=PORT:COM1 --mount=C:../.. -f=10

rem *
rem * Undo what was done above
rem *
PROMPT $P$G
set BREWDIR=
set NOBREW=
