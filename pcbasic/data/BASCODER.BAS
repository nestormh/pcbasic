1 REM BASCODER.BAS - Implementation of the BASICODE-3C API on PC-BASIC
2 REM Copyright (c) 2015, 2016 Rob Hagemans
3 REM This file is released under the GNU GPL version 3
4 REM
9 GOTO 1000 ' Initialise client
10 '
11 ' Settings and initialisation
20 '
21 O.VERSION$ = "3C"
23 O.WD% = 40 ' Screen width
24 HG = 640: VG = 350: HO = O.WD% - 1: VE = 24: CT = 0: CN = 0: SR = 0: SR$ = "": IN$ = " ": SV = 7
25 CC[0] = 7: CC[1] = 0
30 O.CL%[0] = 0: O.CL%[1] = 1: O.CL%[2] = 4: O.CL%[3] = 5
31 O.CL%[4] = 2: O.CL%[5] = 3: O.CL%[6] = 6: O.CL%[7] = 63
35 GOSUB 100
40 FOR O.I% = 1 TO 10
50   KEY O.I%, ""
60 NEXT
70 PLAY "MF"
80 RANDOMIZE TIMER
85 DIM O.FN%[8]: O.FFN% = 0
90 GOTO 1010 ' Yield control to client
97  '
98  ' BASICODE-2 subroutines
99  '
100 ' Initialise text screen
101   SCREEN 0, 0, 0, 0
102   WIDTH O.WD%
103   KEY OFF
104   COLOR CC[0],CC[1],0
105   CLS
106   FOR O.I%=0 TO 15
107       PALETTE O.I%, O.CL%[O.I% MOD 8]
108   NEXT
109 RETURN
110 ' Set cursor position
112   LOCATE VE+1, HO+1
113 RETURN
120 ' Retrieve cursor position
121   VE = CSRLIN
122   HO = POS(0)
123 RETURN
150 ' Print highlighted text block to screen
151   COLOR CC[0], CC[1]: PRINT " ";
152   COLOR CC[1], CC[0]: PRINT "  "; SR$; "  ";
153   COLOR CC[0], CC[1]: PRINT " ";
154 RETURN
200 ' Read keystroke
201   IN$ = INKEY$: IF IN$ = "" THEN IN = 0: RETURN
202   IN = ASC(IN$): CN = 0: IF IN$ >= "a" AND IN$ <= "z" THEN CN = IN-32: IN = CN
203   IF IN$ >= "A" AND IN$ <= "Z" THEN CN = IN+32
204   IF IN = 0 THEN O.EA = ASC(RIGHT$(IN$, 1)): IN$ = "" ELSE O.EA = 0
205   IF IN = 8 THEN IN = 127 ELSE IF IN < 32 OR IN > 95 THEN IN = 0
206   IF O.EA >= &H3B AND O.EA <= &H44 THEN IN = &H3A-O.EA
207   IF O.EA = &H4B THEN IN = 28 ELSE IF O.EA = &H4D THEN IN = 29 ELSE IF O.EA = &H50 THEN IN = 30 ELSE IF O.EA = &H48 THEN IN = 31
208   IF O.EA = &H53 THEN IN = 127
209 RETURN
210 ' Wait for keystroke
211     GOSUB 200
212   IF IN$ = "" AND IN = 0 THEN GOTO 211
213 RETURN
220 ' Read character from screen
221   IN = SCREEN(VE+1, HO+1)
222 RETURN
250 ' Beep the speaker
251   BEEP
252 RETURN
260 ' Obtain a random number
261   RV = RND(1)
262 RETURN
270 ' Perform garbage collection and get amount of free memory
271   FR = FRE("")
272 RETURN
280 ' Switch break key on/off
281   KEY 20, CHR$(&H04)+CHR$(&H46)
285   ON KEY(20) GOSUB 290
287   IF FR = 1 THEN KEY(20) ON ELSE KEY(20) OFF
290 RETURN
300 ' Format number as string
301   SR$ = STR$(SR)
302   IF LEFT$(SR$,1) = " " THEN SR$ = MID$(SR$, 2, LEN(SR$)-1)
303 RETURN
310 ' Format number as string; length and decimal places specified
311   O.IN$ = STR$(FIX(SR)): O.FR$ = STR$(SR-FIX(SR))
312   IF LEFT$(O.IN$) = " " THEN O.IN$ = RIGHT$(O.IN$, 2, LEN(O.IN$)-1)
313   IF O.FR$ = "0" THEN O.FR$ = "": GOTO 321
314   IF 1+CN <= LEN(O.FR$) THEN O.REST$ = MID$(O.FR$, 1+CN, 1) ELSE O.REST$ = "0"
315   O.FR$ = MID$(O.FR$, 2, 1+CN): IF O.REST$ < "5" THEN GOTO 321
316   FOR O.PS = LEN(O.FR$) TO 2 STEP -1
317     MID$(O.FR$, POS, 1) = CHR$(ASC(MID$(O.FR$, POS, 1))+1)
318     IF MID$(O.FR$, POS, 1) <= "9" THEN GOTO 321
319     IF MID$(O.FR$, POS, 1) = "0"
320   NEXT
321   IF LEN(O.FR$) < CN+1 THEN O.FR$ = O.FR$ + STRING$("0", CN+1-LEN(O.FR$))
322   SR$ = O.IN$ + O.FR$: IF LEN(SR$) > O.CT THEN SR$=STRING$("*", O.CT): RETURN
324   SR$ = STRING$(" ", O.CT-LEN(SR$)) + SR$
326 RETURN
330 ' Capitalise a string (BASICODE-3)
331   FOR O.I = 1 TO LEN(SR$)
332     IF MID$(SR$, O.I) >= "a" AND MID$(SR$, O.I) <= "z" THEN MID$(SR$, O.I) = CHR$(ASC(MID$(SR$, O.I)) - &H20)
334   NEXT
336 RETURN
350 ' Print string to printer
351   LPRINT SR$;
352 RETURN
360 ' Print carriage return/newline to printer
361   LPRINT
362 RETURN
397 '
398 ' BASICODE-3 subroutines
399 '
400 ' Produce a tone on the speaker of specified frequency and duration
401   IF SV = 0 THEN O.FREQ = 0 ELSE O.FREQ = EXP(SP*.057762+2.10125)
402   IF O.FREQ > 32766 THEN O.FREQ = 32766
403   IF O.FREQ < 37 THEN O.FREQ = 37
404   SOUND O.FREQ, SD*1.82 ' NOTE: volume setting in SV is ignored
405 RETURN
450 ' Wait for SD/10 seconds or until a key is pressed
451   O.TM = TIMER + SD*0.1
452     GOSUB 200
453     IF IN$ <> "" OR IN <> 0 THEN RETURN
454     SD = 10*(O.TM - TIMER)
455   IF SD > 0 THEN GOTO 452 ELSE SD = 0
456 RETURN
480 ' Get file number for NF, use NF=0 for first free file (internal)
481   IN = 0: IF O.FFN% > 0 AND O.FN%[O.FFN%] = NF THEN RETURN
483   FOR O.FFN% = 1 TO 8
484     IF O.FN%[O.FFN%] = NF THEN RETURN
486   NEXT
487   O.FFN% = 0: ERROR 52
488 RETURN
490 ' File error handler (internal)
491   IN = -1
492 RESUME NEXT
500 ' Open a file
501   IF NF MOD 2 = 0 THEN O.MD$ = "I" ELSE O.MD$ = "O"
502   IF NF < 0 OR NF > 7 THEN IN = -1: RETURN
504   IF NF\2 = 0 THEN O.DV$ = "CAS1:"
506   IF NF\2 = 2 THEN O.DV$ = "A:"
508   IF NF\2 = 3 THEN O.DV$ = "B:"
510   IF NF\2 = 1 THEN O.DV$ = ""
511   O.RFN% = NF: NF = 0: GOSUB 480: NF = O.RFN%
512   O.FN%[O.FFN%] = NF
515   IN = 0: ON ERROR GOTO 490
516   OPEN O.MD$, O.FFN%, O.DV$ + NF$
518   IF EOF(O.FFN%) THEN IN = 1
520   ON ERROR GOTO 0
521 RETURN
540 ' Read a line from file
542   GOSUB 480
543   IN = 0: ON ERROR GOTO 490
544   LINE INPUT #O.FFN%, IN$
545   IF EOF(O.FFN%) THEN IN = 1
546   ON ERROR GOTO 0
547 RETURN
560 ' Write a string to file
562   GOSUB 480
563   IN = 0: ON ERROR GOTO 490
564   PRINT #O.FFN%, SR$
565   IF EOF(O.FFN%) THEN IN = 1
566   ON ERROR GOTO 0
567 RETURN
580 ' Close the file
581   GOSUB 480
582   CLOSE O.FFN%
583   O.FN%[O.FFN%] = 0
585 RETURN
600 ' Initialise graphics screen
601   SCREEN 9
602   GOSUB 106
603   COLOR CC[0], O.CL%[CC[1]]
604   CLS
605   WINDOW SCREEN (0, 0) - (1, 1)
606 RETURN
620 ' Put a pixel on the screen
621   PSET (HO, VE), CC[CN] + 8
625 RETURN
630 ' Draw a line on the screen
631   LINE -(HO, VE), CC[CN] + 8
635 RETURN
650 ' Draw text at a specified position on the graphics screen
651   DEF SEG = &HF000
652   O.HO% = PMAP(HO, 0): O.VE% = PMAP(VE, 1)
655   WINDOW
657   'LINE (O.HO%, O.VE%)-(O.HO% + 8*LEN(SR$)-1, O.VE%+7), CC[1-CN]+8, BF
660   FOR O.P% = 1 TO LEN(SR$)
662       O.C$ = MID$(SR$, O.P%, 1)
665       FOR O.I% = 0 TO 7
667           IF ASC(O.C$) > 127 THEN O.V = 0 ELSE O.V = PEEK(&HFA6E+8*ASC(O.C$)+O.I%)*256
670           IF O.V > 32767 THEN O.V = O.V-65536!
672           LINE (O.HO%+7+8*(O.P%-1), O.VE%+O.I%) - (O.HO%+8*(O.P%-1), O.VE%+O.I%), CC[CN]+8,, O.V
675       NEXT
677   NEXT
680   WINDOW SCREEN (0, 0) - (1, 1)
682 RETURN
950 ' Finalise BASICODE
951   CLOSE
952   CC[0] = 7: CC[1] = 0: GOSUB 100
954   PALETTE
955 END
