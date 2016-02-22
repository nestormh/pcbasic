rem  MKLST.BAT
rem
rem  This file sorts the filelist in the current directory
rem  and outputs it to the file zzzz.tmp.
rem
dir  > zzz.tmp
sort < zzz.tmp > zzzz.tmp
