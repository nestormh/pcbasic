@echo off
rem  Use this batch file to run the Brewer software without a Brewer
rem  connected.  DO NOT USE with Brewer connected since motors may
rem  move improperly.

rem ****************************************************************************
rem Use the variables in this section to configure the execution of the program
rem ****************************************************************************
rem Use NOBREW=1 if the brewer is not connected
set NOBREW=1
rem BREWER_MAIN indicates the folder in which the main GW-Basic file is contained
set BREWER_MAIN=C:\BrewerSoft
rem BREWER_DEVICE indicates the folder in which the data related to the specific brewer being connected is included
set BREWER_DEVICE=C:\Brw#183
rem MAIN_FILE is the name of the main GW-Basic file
set MAIN_FILE=main.asc
rem COM_PORT is the identifier of the port in which the brewer is connected
set COM_PORT=COM2
rem PCBASIC_PATH is the path in which the PC-BASIC is located
set PCBASIC_PATH=C:\brewer\brewer\pcbasic
rem PYTHON_DIR is the folder in which the python.exe is located
set PYTHON_DIR=C:\Python27
rem ADDITIONAL_OPTIONS set other options that are desired to be used (for example, ADDITIONAL_OPTIONS="-f=10 --debug")
set ADDITIONAL_OPTIONS="-f=10 --max-memory=67108864"

rem ############################################################################
rem ############################################################################
rem ############################################################################
rem ############################################################################

rem ****************************************************************************
rem Do not change anything below this line
rem ****************************************************************************

REM set PATH=%PATH%;C:\Program Files (x86)\PC-BASIC

rem Set the BREWDIR environment variable to the proper directory (full path)
set BREWDIR=D:\
rem * Change the prompt as a reminder that the Brewer software is running
PROMPT Brewer $P$G
rem * Change to the Brewer directory to ensure correct operation (full path)
set CURR_DIR=%CD%
cd /D %BREWER_MAIN%

rem * Run the Brewer software
%PCBASIC_PATH%\ansipipe-launcher.exe %PYTHON_DIR%\python.exe %PCBASIC_PATH%\pcbasic.py %MAIN_FILE% --mount=C:%BREWER_MAIN%,D:%BREWER_DEVICE% --com1=PORT:%COM_PORT% --interface=ansi %ADDITIONAL_OPTIONS%

rem * Undo what was done above
PROMPT $P$G
set BREWDIR=
set NOBREW=
cd /D %CURR_DIR%
cls
ECHO "Have a nice day!"