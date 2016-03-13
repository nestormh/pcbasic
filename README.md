### BREWERSOFT ###

The software included in this repository is a for of the PC-BASIC software (whose latest version can be found at 
the [PC-BASIC home page](http://robhagemans.github.io/pcbasic/). The documentation of the latest version of the PC-BASIC at the moment
in which this fork was created can be found below.

The documentation of this software is divided into: TODO

## Launch configuration ##

In order to launch the software, please use the launch_pcbasic.bat file, included in the root folder of this repository.

You will need to configure the following variables at the beginning of the file:
* *NOBREW*: Use NOBREW=1 if the brewer is not connected
* *BREWER_MAIN*: indicates the folder in which the main GW-Basic file is contained
* *BREWER_DEVICE*: indicates the folder in which the data related to the specific brewer being connected is included
* *MAIN_FILE*: is the name of the main GW-Basic file
* *COM_PORT*: is the identifier of the port in which the brewer is connected
* *PCBASIC_PATH*: is the path in which the PC-BASIC is located
* *PYTHON_DIR*: is the folder in which the python.exe is located
* *ADDITIONAL_OPTIONS*: set other options that are desired to be used (for example, ADDITIONAL_OPTIONS="-f=10 --debug")

## Additional options ##

Apart the original options included in PC-BASIC (see the [PC-BASIC home page](http://robhagemans.github.io/pcbasic/)), there are other 
options related to the brewer itself:
 
* *--use-serial-brewer*: Allows to choose if the original serial module (False), or the one specifically designed for the Brewer (True), 
which will be referred as SerialBrewer from now, for clarification purposes.
The purpose of this module is to simulate the existing behavior observed for the BrewerCMD program, each time the OPEN statement is
called for a COM port. Iterativelly, and for a list of possible baudrates, the program sends a '\r' character, and waits for a response
from the Brewer. If the sequence ' -> ' is received, the program repeats the operation again at the same baudrate, just to confirm. This 
process is done up to 10 times for each baudrate, until the connection is successful. By default, this parameter is set to True.

* *--verbose-brewer*: If selected (True by default), the output from the tests described for the SerialBrewer module is shown. It is useful
to test the communication with the Brewer if it fails.

* *--max-memory*: Althought it comes from the original PC-Basic, now it allows sizes bigger than 64K.

## PYTHON statement ##

An non-standard GW-Basic statement has been included in this version. The purpose of this statement is making the PC-Basic able to include 
Python scripts, allowing to combine the latests developments in Python with the existing software written in GW-Basic. The usage is as 
follows:

PYTHON "<python_script_file.py>"

The called file will receive the existing variables in GW-Basic, so it can read from them. However, have in mind that those variables will
be different, since the naming convention for GW-Basic is not compatible with Python variable names. So:

* All variable names will be in CAPITAL letters
* The '$' character at the end of string variables will be appended to the variable using the suffix '_STR'

Example: VAR$ -> VAR_STR 

* The '!' character at the end of string variables will be appended to the variable using the suffix '_INT'

Example: VAR! -> VAR_INT

* The '%' character at the end of string variables will be appended to the variable using the suffix '_SNG'

Example: VAR% -> VAR_SNG

* The '#' character at the end of string variables will be appended to the variable using the suffix '_DBL'

Example: VAR# -> VAR_DBL

* Once the python program finishes, all variable names finished into '_STR', '_INT', '_SNG', '_DBL' will be converted to their related names
in GW-Basic
* To get a list of the variables available, execute 'print globals().keys()' inside the python script
* Those variables not following this convention will be simply ignored
* Please have in mind that all variable names will be converted to CAPITAL letters.
* These indications also apply for matrices.
* There is an example of a program which calls to a python script and retrieves the variables in the examples/python_statement folder

## Main modifications ##

* SerialBrewer.py and SerialBrewerWin32.py files included for specific communication with the Brewer.
* Added some fixes to the ports.py file, in order to solve the problem of duplicated COM files when the port was re-open.
* Added some fixes to the video_ansi.py file, which was not receiving the proper parameters, making it impossible to use the ansi interface.
* The file var.py has been modified in order to use 32-bit indexes, which allowed to use more than 64K for variables, among other modifications.
* File statements.py has been modified, and a new file called gwbasic2python.py, allowing to execute python scripts from GW-Basic.
* Other modifications.

### PC-BASIC ###

In this section, the original documentation of the PC-Basic has been included, for tracking and usability purposes.

_A free, cross-platform emulator for the GW-BASIC family of interpreters._

PC-BASIC is a free, cross-platform interpreter for GW-BASIC, Advanced BASIC (BASICA), PCjr Cartridge Basic and Tandy 1000 GW-BASIC.
It interprets these BASIC dialects with a high degree of accuracy, aiming for bug-for-bug compatibility.
PC-BASIC emulates the most common video and audio hardware on which these BASICs used to run.
PC-BASIC runs ASCII, bytecode and protected .BAS files.
It implements floating-point arithmetic in the Microsoft Binary Format (MBF) and can therefore
read and write binary data files created by GW-BASIC.  

PC-BASIC is free and open source software released under the GPL version 3.  

See also the [PC-BASIC home page](http://robhagemans.github.io/pcbasic/).

![](https://robhagemans.github.io/pcbasic/screenshots/pcbasic.png)

----------

### Quick Start Guide ###

This quick start guide covers installation and elementary use of PC-BASIC. For more information, please refer to the [full PC-BASIC documentation](http://pc-basic.org/doc#) which covers usage, command-line options and a full [GW-BASIC language reference](http://pc-basic.org/doc#reference). This documentation is also included with the current PC-BASIC release.

If you find bugs, please report them on the [SourceForge discussion page](https://sourceforge.net/p/pcbasic/discussion/bugs/) or [open an issue on GitHub](https://github.com/robhagemans/pcbasic/issues). It would be most helpful if you could include a short bit of BASIC code that triggers the bug.


#### Installation ####
Packaged distributions can be downloaded from one of the following locations:  

- [PC-BASIC releases on GitHub](https://github.com/robhagemans/pcbasic/releases)  
- [PC-BASIC releases on SourceForge](https://sourceforge.net/projects/pcbasic/files/)  

On **Windows**:  

- run the installer  
- to start, click PC-BASIC in your Start menu  

On **OS X**:  

- mount the disk image  
- to start, double click the PC-BASIC app  

On **Linux** and **other Unix**:  

- untar the archive  
- run `sudo ./install.sh`. You may be asked to install further dependencies through your OS's package management system.  
- to start, click PC-BASIC in your Applications menu or run `pcbasic` on the command line.  

If the options above are not applicable or you prefer to install from source, please
consult [`INSTALL.md`](https://github.com/robhagemans/pcbasic/blob/master/INSTALL.md) for detailed instructions.


#### Usage essentials ####
Double-click on `pcbasic` or run `pcbasic` on the Windows, OSX or Linux command line to start in interactive mode with no program loaded.  
A few selected command-line options:  
`pcbasic PROGRAM.BAS` runs PROGRAM.BAS directly.  
`pcbasic -h` shows all available command line options.  

If you're running PC-BASIC from a GUI, you can set the required options in the configuration file instead.
The configuration file is stored in the following location:

| OS         | Configuration file  
|------------|-------------------------------------------------------------------------  
| Windows    | `%APPDATA%\pcbasic\PCBASIC.INI`  
| OS X       | `~/Library/Application Support/pcbasic/PCBASIC.INI`  
| Linux      | `~/.config/pcbasic/PCBASIC.INI`  

For example, you could include the following line in `PCBASIC.INI` to emulate IBM PCjr Cartridge Basic instead of GW-BASIC 3.23:

    preset=pcjr  


#### Basic BASIC commands ####
PC-BASIC starts in interactive mode, where you can execute BASIC statements directly.
A few essential statements:  
`SYSTEM` exits PC-BASIC.  
`LOAD "PROGRAM"` loads `PROGRAM.BAS` (but does not start it).  
`RUN` starts the currently loaded program.  

Use one of the key combinations `Ctrl+Break`, `Ctrl+Scroll Lock`, `Ctrl+C` or `F12+B`
to terminate the running program and return to interactive mode.  


#### Get BASIC programs ####
The following pages have GW-BASIC and Tandy 1000 BASIC program downloads, lots of information and further links.  

- [KindlyRat](http://www.oocities.org/KindlyRat/GWBASIC.html)'s archived geocities page has a number of classic games and utilities.  
- [PeatSoft](http://archive.is/AUm6G) provides GW-BASIC documentation, utilities and some more games.  
- [Neil C. Obremski's gw-basic.com](http://www.gw-basic.com/) has fun new games made in GW-BASIC over the last few years!  
- [Leon Peyre](http://peyre.x10.mx/GWBASIC/) has a nice collection of GW-BASIC programs, including the original IBM PC-DOS 1.1 samples and the (in)famous `DONKEY.BAS`.  
- [Brooks deForest](http://www.brooksdeforest.com/tandy1000/) provides his amazing Tandy BASIC games, all released into the public domain.  
- [TVDog's Archive](http://www.oldskool.org/guides/tvdog/) is a great source of Tandy 1000 information and BASIC programs.  
- [Phillip Bigelow](http://www.scn.org/~bh162/basic_programs.html) provides scientific programs written in GW-BASIC, as many science and engineering programs once were.  
- [Gary Peek](http://www.garypeek.com/basic/gwprograms.htm) provides miscellaneous GW-BASIC sources which he released into the public domain.  
- [S.A. Moore's Classic BASIC Games page](http://www.moorecad.com/classicbasic/index.html) has some nice pictures of retro hardware and the BASIC Games from David Ahl's classic book.  
- [Joseph Sixpack's Last Book of GW-BASIC](http://www.geocities.ws/joseph_sixpack/btoc.html) has lots of GW-BASIC office and utility programs, including the PC-CALC spreadsheet.  
- [cd.textfiles.com](http://cd.textfiles.com) has tons of old shareware, among which some good GW-BASIC games - dig around here to find some treasures...  
