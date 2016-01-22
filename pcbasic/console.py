"""
PC-BASIC - console.py
Console front-end

(c) 2013, 2014, 2015, 2016 Rob Hagemans
This file is released under the GNU GPL version 3.
"""

import string

import state
import backend
import redirect
import error
# to initialise state.console_state.codepage
import unicodepage

# alt+key macros for interactive mode
# these happen at a higher level than F-key macros
alt_key_replace = {
    '\0\x1E': 'AUTO',   '\0\x30': 'BSAVE',  '\0\x2E': 'COLOR',
    '\0\x20': 'DELETE', '\0\x12': 'ELSE',   '\0\x21': 'FOR',
    '\0\x22': 'GOTO',   '\0\x23': 'HEX$',   '\0\x17': 'INPUT',
    '\0\x25': 'KEY',    '\0\x26': 'LOCATE', '\0\x32': 'MOTOR',
    '\0\x31': 'NEXT',   '\0\x18': 'OPEN',   '\0\x19': 'PRINT',
    '\0\x13': 'RUN',    '\0\x1F': 'SCREEN', '\0\x14': 'THEN',
    '\0\x16': 'USING',  '\0\x2F': 'VAL',    '\0\x11': 'WIDTH',
    '\0\x2D': 'XOR'}

# on the keys line 25, what characters to replace & with which
keys_line_replace_chars = {
        '\x07': '\x0e',    '\x08': '\xfe',    '\x09': '\x1a',    '\x0A': '\x1b',
        '\x0B': '\x7f',    '\x0C': '\x16',    '\x0D': '\x1b',    '\x1C': '\x10',
        '\x1D': '\x11',    '\x1E': '\x18',    '\x1F': '\x19'}

# KEY ON?
state.console_state.keys_visible = False

# viewport parameters
state.console_state.view_start = 1
state.console_state.scroll_height = 24
state.console_state.view_set = False
# writing on bottom row is allowed
state.console_state.bottom_row_allowed = False

# current row and column
state.console_state.row = 1
state.console_state.col = 1
# true if we're on 80 but should be on 81
state.console_state.overflow = False

# overwrite mode (instead of insert)
state.console_state.overwrite_mode = True

#############################
# init

def prepare():
    """ Initialise console module. """
    state.console_state.keys_visible = False

def init_mode():
    """ Initialisation when we switched to new screen mode. """
    # only redraw keys if screen has been cleared  (any colours stay the same).
    if state.console_state.keys_visible:
        show_keys(True)
    # rebuild build the cursor;
    # first move to home in case the screen has shrunk
    set_pos(1, 1)
    state.console_state.screen.cursor.set_default_shape(state.console_state.overwrite_mode)
    state.console_state.screen.cursor.reset_visibility()
    # there is only one VIEW PRINT setting across all pages.
    if state.console_state.scroll_height == 25:
        # tandy/pcjr special case: VIEW PRINT to 25 is preserved
        state.console_state.screen.set_view(1, 25)
    else:
        state.console_state.screen.unset_view()

def set_width(to_width):
    """ Change the width of the screen. """
    # raise an error if the width value doesn't make sense
    if to_width not in (20, 40, 80):
        raise error.RunError(error.IFC)
    # if we're currently at that width, do nothing
    if to_width != state.console_state.screen.mode.width:
        # change video mode to one with new width
        state.console_state.screen.set_width(to_width)
        init_mode()

###############################
# interactive mode

def wait_screenline(write_endl=True, from_start=False):
    """ Enter interactive mode and read string from console. """
    # from_start means direct entry mode, otherwise input mode
    prompt_width = 0 if from_start else state.console_state.col-1
    try:
        # give control to user for interactive mode
        prompt_row, left, right = wait_interactive(prompt_width)
    except error.Break:
        for echo in redirect.output_echos:
            # for some reason, 0E character is printed to redirects at break
            echo ('\x0e')
        write_line()
        raise
    # get contents and of the logical line
    if from_start:
        outstr = get_logical_line(state.console_state.row)
    else:
        outstr = get_logical_line_input(state.console_state.row,
                                        prompt_row, left, right)
    # redirects output exactly the contents of the logical line
    # including any trailing whitespace and chars past 255
    for echo in redirect.output_echos:
        echo(outstr)
    # go to last row of logical line
    state.console_state.row = find_end_of_line(state.console_state.row)
    # echo the CR, if requested
    if write_endl:
        for echo in redirect.output_echos:
            echo('\r\n')
        set_pos(state.console_state.row+1, 1)
    # to the parser/INPUT, only the first 255 chars are returned
    # with trailing whitespace removed
    return str(outstr[:255].rstrip(' \t\n'))

def find_start_of_line(srow):
    """ Find the start of the logical line that includes our current position. """
    # move up as long as previous line wraps
    while srow > 1 and state.console_state.screen.apage.row[srow-2].wrap:
        srow -= 1
    return srow

def find_end_of_line(srow):
    """ Find the end of the logical line that includes our current position. """
    # move down as long as this line wraps
    while srow <= state.console_state.screen.mode.height and state.console_state.screen.apage.row[srow-1].wrap:
        srow += 1
    return srow

def get_logical_line(srow):
    """ Get bytearray of the contents of the logical line. """
    # find start of logical line
    srow = find_start_of_line(srow)
    line = bytearray()
    # add all rows of the logical line
    for therow in state.console_state.screen.apage.row[
                                srow-1:state.console_state.screen.mode.height]:
        line += bytearray(pair[0] for pair in therow.buf[:therow.end])
        # continue so long as the line wraps
        if not therow.wrap:
            break
        # wrap before end of line means LF
        if therow.end < state.console_state.screen.mode.width:
            line += '\n'
    return line

def get_logical_line_input(srow, prompt_row, left, right):
    """ Get bytearray of the contents of the logical line, adapted for INPUT. """
    # INPUT: the prompt starts at the beginning of a logical line
    # but the row may have moved up: this happens on line 24
    # in this case we need to move up to the start of the logical line
    prompt_row = find_start_of_line(prompt_row)
    # find start of logical line
    srow = find_start_of_line(srow)
    line = bytearray()
    # INPUT returns empty string if enter pressed below prompt row
    if srow <= prompt_row:
        # add all rows of the logical line
        for crow in range(srow, state.console_state.screen.mode.height+1):
            therow = state.console_state.screen.apage.row[crow-1]
            # exclude prompt, if any; only go from furthest_left to furthest_right
            if crow == prompt_row:
                rowpairs = therow.buf[:therow.end][left-1:right-1]
            else:
                rowpairs = therow.buf[:therow.end]
            # get characters from char/attr pairs and convert to bytearray
            line += bytearray(pair[0] for pair in rowpairs)
            if not therow.wrap:
                break
            # wrap before end of line means LF
            if therow.end < state.console_state.screen.mode.width:
                line += '\n'
    return line

def wait_interactive(prompt_width):
    """ Manage the interactive mode. """
    # force cursor visibility in all cases
    state.console_state.screen.cursor.show(True)
    try:
        # this is where we started
        start_row = state.console_state.row
        furthest_left = 1 + prompt_width
        # this is where we arrow-keyed on the start line
        furthest_right = state.console_state.col
        while True:
            row, col = state.console_state.row, state.console_state.col
            if row == start_row:
                furthest_left = min(col, furthest_left)
                furthest_right = max(col, furthest_right)
                if col == state.console_state.screen.mode.width and state.console_state.overflow:
                    furthest_right += 1
            # wait_char returns one e-ASCII code
            d = state.console_state.keyb.get_char_block()
            # insert dbcs chars from keyboard buffer two bytes at a time
            if (d in state.console_state.codepage.lead and
                    state.console_state.keyb.buf.peek() in
                    state.console_state.codepage.trail):
                d += state.console_state.keyb.buf.getc()
            if not d:
                # input stream closed
                raise error.Exit()
            if d in ('\0\x48', '\x1e', '\0\x50', '\x1f',  '\0\x4d', '\x1c',
                      '\0\x4B', '\x1d', '\0\x47', '\x0b', '\0\x4f', '\x0e'):
                # arrow keys drop us out of insert mode
                set_overwrite_mode(True)
            if d == '\x03':
                # CTRL-C -- only caught here, not in wait_char like <CTRL+BREAK>
                raise error.Break()
            elif d == '\r':
                # ENTER, CTRL+M
                break
            elif d == '\a':
                # BEL, CTRL+G
                state.console_state.sound.beep()
            elif d == '\b':
                # BACKSPACE, CTRL+H
                backspace(start_row, furthest_left)
            elif d == '\t':
                # TAB, CTRL+I
                tab()
            elif d == '\n':
                # CTRL+ENTER, CTRL+J
                line_feed()
            elif d == '\x1b':
                # ESC, CTRL+[
                clear_line(row, furthest_left)
            elif d in ('\0\x75', '\x05'):
                # CTRL+END, CTRL+E
                clear_rest_of_line(row, col)
            elif d in ('\0\x48', '\x1e'):
                # UP, CTRL+6
                set_pos(row - 1, col, scroll_ok=False)
            elif d in ('\0\x50', '\x1f'):
                # DOWN, CTRL+-
                set_pos(row + 1, col, scroll_ok=False)
            elif d in ('\0\x4D', '\x1c'):
                # RIGHT, CTRL+\
                # skip dbcs trail byte
                if state.console_state.screen.apage.row[row-1].double[col-1] == 1:
                    set_pos(row, col + 2, scroll_ok=False)
                else:
                    set_pos(row, col + 1, scroll_ok=False)
            elif d in ('\0\x4b', '\x1d'):
                # LEFT, CTRL+]
                set_pos(row, col - 1, scroll_ok=False)
            elif d in ('\0\x74', '\x06'):
                # CTRL+RIGHT, CTRL+F
                skip_word_right()
            elif d in ('\0\x73', '\x02'):
                # CTRL+LEFT, CTRL+B
                skip_word_left()
            elif d in ('\0\x52', '\x12'):
                # INS, CTRL+R
                set_overwrite_mode(not state.console_state.overwrite_mode)
            elif d in ('\0\x53', '\x7f'):
                # DEL, CTRL+BACKSPACE
                delete_char(row, col)
            elif d in ('\0\x47', '\x0b'):
                # HOME, CTRL+K
                set_pos(1, 1)
            elif d in ('\0\x4f', '\x0e'):
                # END, CTRL+N
                end()
            elif d in ('\0\x77', '\x0c'):
                # CTRL+HOME, CTRL+L
                clear()
            else:
                try:
                    # these are done on a less deep level than the fn key macros
                    letters = list(alt_key_replace[d]) + [' ']
                except KeyError:
                    letters = [d]
                for d in letters:
                    # ignore eascii by this point, but not dbcs
                    if d[0] not in ('\0', '\r'):
                        if not state.console_state.overwrite_mode:
                            for c in d:
                                insert(row, col, c, state.console_state.screen.attr)
                                # row and col have changed
                                state.console_state.screen.redraw_row(col-1, row)
                                col += 1
                            set_pos(state.console_state.row,
                                    state.console_state.col + len(d))
                        else:
                            # put all dbcs in before messing with cursor position
                            for c in d:
                                put_char(c, do_scroll_down=True)
            # move left if we end up on dbcs trail byte
            row, col = state.console_state.row, state.console_state.col
            if state.console_state.screen.apage.row[row-1].double[col-1] == 2:
                set_pos(row, col-1, scroll_ok=False)
            # adjust cursor width
            row, col = state.console_state.row, state.console_state.col
            if state.console_state.screen.apage.row[row-1].double[col-1] == 1:
                state.console_state.screen.cursor.set_width(2)
            else:
                state.console_state.screen.cursor.set_width(1)
    finally:
        set_overwrite_mode(True)
        # reset cursor visibility
        state.console_state.screen.cursor.reset_visibility()
    return start_row, furthest_left, furthest_right

def set_overwrite_mode(new_overwrite=True):
    """ Set or unset the overwrite mode (INS). """
    if new_overwrite != state.console_state.overwrite_mode:
        state.console_state.overwrite_mode = new_overwrite
        state.console_state.screen.cursor.set_default_shape(new_overwrite)

def insert(crow, ccol, c, cattr):
    """ Insert a single byte at the current position. """
    while True:
        therow = state.console_state.screen.apage.row[crow-1]
        therow.buf.insert(ccol-1, (c, cattr))
        if therow.end < state.console_state.screen.mode.width:
            therow.buf.pop()
            if therow.end > ccol-1:
                therow.end += 1
            else:
                therow.end = ccol
            break
        else:
            if crow == state.console_state.scroll_height:
                state.console_state.screen.scroll()
                # this is not the global row which is changed by scroll()
                crow -= 1
            if not therow.wrap and crow < state.console_state.screen.mode.height:
                state.console_state.screen.scroll_down(crow+1)
                therow.wrap = True
            c, cattr = therow.buf.pop()
            crow += 1
            ccol = 1

def delete_char(crow, ccol):
    """ Delete the character (single/double width) at the current position. """
    double = state.console_state.screen.apage.row[crow-1].double[ccol-1]
    if double == 0:
        # we're on an sbcs byte.
        delete_sbcs_char(crow, ccol)
    elif double == 1:
        # we're on a lead byte, delete this and the next.
        delete_sbcs_char(crow, ccol)
        delete_sbcs_char(crow, ccol)
    elif double == 2:
        # we're on a trail byte, delete the previous and this.
        delete_sbcs_char(crow, ccol-1)
        delete_sbcs_char(crow, ccol-1)

def delete_sbcs_char(crow, ccol):
    """ Delete a single-byte character at the current position. """
    save_col = ccol
    thepage = state.console_state.screen.apage
    therow = thepage.row[crow-1]
    width = state.console_state.screen.mode.width
    if crow > 1 and ccol >= therow.end and therow.wrap:
        # row was an LF-ending row & we're deleting past the LF
        nextrow = thepage.row[crow]
        # replace everything after the delete location with
        # stuff from the next row
        therow.buf[ccol-1:] = nextrow.buf[:width-ccol+1]
        therow.end = min(max(therow.end, ccol) + nextrow.end, width)
        # and continue on the following rows as long as we wrap.
        while crow < state.console_state.scroll_height and nextrow.wrap:
            nextrow2 = thepage.row[crow+1]
            nextrow.buf = (nextrow.buf[width-ccol+1:] +
                           nextrow2.buf[:width-ccol+1])
            nextrow.end = min(nextrow.end + nextrow2.end, width)
            crow += 1
            therow, nextrow = thepage.row[crow-1], thepage.row[crow]
        # replenish last row with empty space
        nextrow.buf = (nextrow.buf[width-ccol+1:] +
                       [(' ', state.console_state.screen.attr)] * (width-ccol+1))
        # adjust the row end
        nextrow.end -= width - ccol
        # redraw the full logical line from the original position onwards
        state.console_state.screen.redraw_row(save_col-1, state.console_state.row)
        # if last row was empty, scroll up.
        if nextrow.end <= 0:
            nextrow.end = 0
            ccol += 1
            therow.wrap = False
            state.console_state.screen.scroll(crow+1)
    elif ccol <= therow.end:
        # row not ending with LF
        while True:
            if (therow.end < width or crow == state.console_state.scroll_height
                    or not therow.wrap):
                # no knock on to next row, just delete the char
                del therow.buf[ccol-1]
                # and replenish the buffer at the end of the line
                therow.buf.insert(therow.end-1, (' ', state.console_state.screen.attr))
                break
            else:
                # wrap and end[row-1]==width
                nextrow = thepage.row[crow]
                # delete the char and replenish from next row
                del therow.buf[ccol-1]
                therow.buf.insert(therow.end-1, nextrow.buf[0])
                # then move on to the next row and delete the first char
                crow += 1
                therow, nextrow = thepage.row[crow-1], thepage.row[crow]
                ccol = 1
        # redraw the full logical line
        # this works from *global* row onwards
        state.console_state.screen.redraw_row(save_col-1, state.console_state.row)
        # change the row end
        # this works on *local* row (last row edited)
        if therow.end > 0:
            therow.end -= 1
        else:
            # if there was nothing on the line, scroll the next line up.
            state.console_state.screen.scroll(crow)
            if crow > 1:
                thepage.row[crow-2].wrap = False

def clear_line(the_row, from_col=1):
    """ Clear whole logical line (ESC), leaving prompt. """
    clear_rest_of_line(find_start_of_line(the_row), from_col)

def clear_rest_of_line(srow, scol):
    """ Clear from given position to end of logical line (CTRL+END). """
    mode = state.console_state.screen.mode
    therow = state.console_state.screen.apage.row[srow-1]
    therow.buf = (therow.buf[:scol-1] +
        [(' ', state.console_state.screen.attr)] * (mode.width-scol+1))
    therow.double = (therow.double[:scol-1] + [0] * (mode.width-scol+1))
    therow.end = min(therow.end, scol-1)
    crow = srow
    while state.console_state.screen.apage.row[crow-1].wrap:
        crow += 1
        state.console_state.screen.apage.row[crow-1].clear(state.console_state.screen.attr)
    for r in range(crow, srow, -1):
        state.console_state.screen.apage.row[r-1].wrap = False
        state.console_state.screen.scroll(r)
    therow = state.console_state.screen.apage.row[srow-1]
    therow.wrap = False
    set_pos(srow, scol)
    save_end = therow.end
    therow.end = mode.width
    if scol > 1:
        state.console_state.screen.redraw_row(scol-1, srow)
    else:
        # inelegant: we're clearing the text buffer for a second time now
        state.console_state.screen.clear_rows(srow, srow)
    therow.end = save_end

def backspace(start_row, start_col):
    """ Delete the char to the left (BACKSPACE). """
    crow, ccol = state.console_state.row, state.console_state.col
    # don't backspace through prompt
    if ccol == 1:
        if crow > 1 and state.console_state.screen.apage.row[crow-2].wrap:
            ccol = state.console_state.screen.mode.width
            crow -= 1
    elif ccol != start_col or state.console_state.row != start_row:
        ccol -= 1
    set_pos(crow, max(1, ccol))
    if state.console_state.screen.apage.row[state.console_state.row-1].double[state.console_state.col-1] == 2:
        # we're on a trail byte, move to the lead
        set_pos(state.console_state.row, state.console_state.col-1)
    delete_char(crow, ccol)

def tab():
    """ Jump to next 8-position tab stop (TAB). """
    row, col = state.console_state.row, state.console_state.col
    newcol = 9 + 8 * int((col-1) / 8)
    if state.console_state.overwrite_mode:
        set_pos(row, newcol, scroll_ok=False)
    else:
        for _ in range(8):
            insert(row, col, ' ', state.console_state.screen.attr)
        state.console_state.screen.redraw_row(col - 1, row)
        set_pos(row, newcol)

def end():
    """ Jump to end of logical line; follow wraps (END). """
    crow = state.console_state.row
    while (state.console_state.screen.apage.row[crow-1].wrap and
            crow < state.console_state.screen.mode.height):
        crow += 1
    if state.console_state.screen.apage.row[crow-1].end == state.console_state.screen.mode.width:
        set_pos(crow, state.console_state.screen.apage.row[crow-1].end)
        state.console_state.overflow = True
    else:
        set_pos(crow, state.console_state.screen.apage.row[crow-1].end+1)

def line_feed():
    """ Move the remainder of the line to the next row and wrap (LF). """
    crow, ccol = state.console_state.row, state.console_state.col
    if ccol < state.console_state.screen.apage.row[crow-1].end:
        for _ in range(state.console_state.screen.mode.width - ccol + 1):
            insert(crow, ccol, ' ', state.console_state.screen.attr)
        state.console_state.screen.redraw_row(ccol - 1, crow)
        state.console_state.screen.apage.row[crow-1].end = ccol - 1
    else:
        while (state.console_state.screen.apage.row[crow-1].wrap and
                crow < state.console_state.scroll_height):
            crow += 1
        if crow >= state.console_state.scroll_height:
            state.console_state.screen.scroll()
        # state.console_state.row has changed, don't use crow
        if state.console_state.row < state.console_state.screen.mode.height:
            state.console_state.screen.scroll_down(state.console_state.row+1)
    # LF connects lines like word wrap
    state.console_state.screen.apage.row[state.console_state.row-1].wrap = True
    set_pos(state.console_state.row+1, 1)

def skip_word_right():
    """ Skip one word to the right (CTRL+RIGHT). """
    crow, ccol = state.console_state.row, state.console_state.col
    # find non-alphanumeric chars
    while True:
        c = state.console_state.screen.apage.row[crow-1].buf[ccol-1][0]
        if (c not in string.digits + string.ascii_letters):
            break
        ccol += 1
        if ccol > state.console_state.screen.mode.width:
            if crow >= state.console_state.scroll_height:
                # nothing found
                return
            crow += 1
            ccol = 1
    # find alphanumeric chars
    while True:
        c = state.console_state.screen.apage.row[crow-1].buf[ccol-1][0]
        if (c in string.digits + string.ascii_letters):
            break
        ccol += 1
        if ccol > state.console_state.screen.mode.width:
            if crow >= state.console_state.scroll_height:
                # nothing found
                return
            crow += 1
            ccol = 1
    set_pos(crow, ccol)

def skip_word_left():
    """ Skip one word to the left (CTRL+LEFT). """
    crow, ccol = state.console_state.row, state.console_state.col
    # find alphanumeric chars
    while True:
        ccol -= 1
        if ccol < 1:
            if crow <= state.console_state.view_start:
                # not found
                return
            crow -= 1
            ccol = state.console_state.screen.mode.width
        c = state.console_state.screen.apage.row[crow-1].buf[ccol-1][0]
        if (c in string.digits + string.ascii_letters):
            break
    # find non-alphanumeric chars
    while True:
        last_row, last_col = crow, ccol
        ccol -= 1
        if ccol < 1:
            if crow <= state.console_state.view_start:
                break
            crow -= 1
            ccol = state.console_state.screen.mode.width
        c = state.console_state.screen.apage.row[crow-1].buf[ccol-1][0]
        if (c not in string.digits + string.ascii_letters):
            break
    set_pos(last_row, last_col)

def clear():
    """ Clear the screen. """
    save_view_set = state.console_state.view_set
    save_view_start = state.console_state.view_start
    save_scroll_height = state.console_state.scroll_height
    state.console_state.screen.set_view(1, 25)
    state.console_state.screen.clear_view()
    if save_view_set:
        state.console_state.screen.set_view(save_view_start, save_scroll_height)
    else:
        state.console_state.screen.unset_view()
    if state.console_state.keys_visible:
        show_keys(True)

##### output methods

def write(s, scroll_ok=True, do_echo=True):
    """ Write a string to the screen at the current position. """
    if do_echo:
        for echo in redirect.output_echos:
            # CR -> CRLF, CRLF -> CRLF LF
            echo(''.join([ ('\r\n' if c == '\r' else c) for c in s ]))
    last = ''
    # if our line wrapped at the end before, it doesn't anymore
    state.console_state.screen.apage.row[state.console_state.row-1].wrap = False
    for c in s:
        row, col = state.console_state.row, state.console_state.col
        if c == '\t':
            # TAB
            num = (8 - (col - 1 - 8 * int((col-1) / 8)))
            for _ in range(num):
                put_char(' ')
        elif c == '\n':
            # LF
            # exclude CR/LF
            if last != '\r':
                # LF connects lines like word wrap
                state.console_state.screen.apage.row[row-1].wrap = True
                set_pos(row + 1, 1, scroll_ok)
        elif c == '\r':
            # CR
            state.console_state.screen.apage.row[row-1].wrap = False
            set_pos(row + 1, 1, scroll_ok)
        elif c == '\a':
            # BEL
            state.console_state.sound.beep()
        elif c == '\x0B':
            # HOME
            set_pos(1, 1, scroll_ok)
        elif c == '\x0C':
            # CLS
            clear()
        elif c == '\x1C':
            # RIGHT
            set_pos(row, col + 1, scroll_ok)
        elif c == '\x1D':
            # LEFT
            set_pos(row, col - 1, scroll_ok)
        elif c == '\x1E':
            # UP
            set_pos(row - 1, col, scroll_ok)
        elif c == '\x1F':
            # DOWN
            set_pos(row + 1, col, scroll_ok)
        else:
            # includes \b, \0, and non-control chars
            put_char(c)
        last = c

def write_line(s='', scroll_ok=True, do_echo=True):
    """ Write a string to the screen and end with a newline. """
    write(s, scroll_ok, do_echo)
    if do_echo:
        for echo in redirect.output_echos:
            echo('\r\n')
    check_pos(scroll_ok=True)
    state.console_state.screen.apage.row[state.console_state.row-1].wrap = False
    set_pos(state.console_state.row + 1, 1)

def list_line(line, newline=True):
    """ Print a line from a program listing or EDIT prompt. """
    # no wrap if 80-column line, clear row before printing.
    # flow of listing is visible on screen
    backend.check_events()
    # replace LF CR with LF
    line = line.replace('\n\r', '\n')
    cuts = line.split('\n')
    for i, l in enumerate(cuts):
        # clear_line looks back along wraps, use clear_rest_of_line instead
        clear_rest_of_line(state.console_state.row, 1)
        write(str(l))
        if i != len(cuts)-1:
            write('\n')
    if newline:
        write_line()
    # remove wrap after 80-column program line
    if len(line) == state.console_state.screen.mode.width and state.console_state.row > 2:
        state.console_state.screen.apage.row[state.console_state.row-3].wrap = False

#####################
# key replacement

def list_keys():
    """ Print a list of the function key macros. """
    for i in range(backend.num_fn_keys):
        text = bytearray(state.console_state.key_replace[i])
        for j in range(len(text)):
            try:
                text[j] = keys_line_replace_chars[chr(text[j])]
            except KeyError:
                pass
        write_line('F' + str(i+1) + ' ' + str(text))

def clear_key_row():
    """ Clear row 25 on the active page. """
    key_row = state.console_state.screen.mode.height
    state.console_state.screen.clear_rows(key_row, key_row)

def show_keys(do_show):
    """ Show/hide the function keys line on the active page. """
    # Keys will only be visible on the active page at which KEY ON was given,
    # and only deleted on page at which KEY OFF given.
    if not do_show:
        state.console_state.keys_visible = False
        clear_key_row()
    else:
        state.console_state.keys_visible = True
        clear_key_row()
        for i in range(state.console_state.screen.mode.width/8):
            text = str(state.console_state.key_replace[i][:6])
            kcol = 1+8*i
            write_for_keys(str(i+1)[-1], kcol, state.console_state.screen.attr)
            if not state.console_state.screen.mode.is_text_mode:
                write_for_keys(text, kcol+1, state.console_state.screen.attr)
            else:
                if (state.console_state.screen.attr>>4) & 0x7 == 0:
                    write_for_keys(text, kcol+1, 0x70)
                else:
                    write_for_keys(text, kcol+1, 0x07)
        state.console_state.screen.apage.row[24].end = state.console_state.screen.mode.width

def write_for_keys(s, col, cattr):
    """ Write chars on the keys line; no echo, some character replacements. """
    for c in s:
        if c == '\0':
            # NUL character terminates display of a word
            break
        else:
            try:
                c = keys_line_replace_chars[c]
            except KeyError:
                pass
            state.console_state.screen.put_char_attr(state.console_state.screen.apagenum, 25, col, c, cattr, for_keys=True)
        col += 1
    #backend.video_queue.put(backend.Event(backend.VIDEO_SET_ATTR,
    #                                        (state.console_state.screen.attr)))

#####################
# screen read/write

def put_char(c, do_scroll_down=False):
    """ Put one byte at the current position. """
    # check if scroll& repositioning needed
    if state.console_state.overflow:
        state.console_state.col += 1
        state.console_state.overflow = False
    # see if we need to wrap and scroll down
    check_wrap(do_scroll_down)
    # move cursor and see if we need to scroll up
    check_pos(scroll_ok=True)
    # put the character
    state.console_state.screen.put_char_attr(state.console_state.screen.apagenum,
            state.console_state.row, state.console_state.col,
            c, state.console_state.screen.attr)
    # adjust end of line marker
    if (state.console_state.col >
            state.console_state.screen.apage.row[state.console_state.row-1].end):
         state.console_state.screen.apage.row[state.console_state.row-1].end = state.console_state.col
    # move cursor. if on col 80, only move cursor to the next row
    # when the char is printed
    if state.console_state.col < state.console_state.screen.mode.width:
        state.console_state.col += 1
    else:
        state.console_state.overflow = True
    # move cursor and see if we need to scroll up
    check_pos(scroll_ok=True)

def check_wrap(do_scroll_down):
    """ Wrap if we need to. """
    if state.console_state.col > state.console_state.screen.mode.width:
        if state.console_state.row < state.console_state.screen.mode.height:
            # wrap line
            state.console_state.screen.apage.row[state.console_state.row-1].wrap = True
            if do_scroll_down:
                # scroll down (make space by shifting the next rows down)
                if state.console_state.row < state.console_state.scroll_height:
                    state.console_state.screen.scroll_down(state.console_state.row+1)
            # move cursor and reset cursor attribute
            state.console_state.screen.move_cursor(state.console_state.row + 1, 1)
        else:
            state.console_state.col = state.console_state.screen.mode.width

def set_pos(to_row, to_col, scroll_ok=True):
    """ Set the current position. """
    state.console_state.overflow = False
    state.console_state.row, state.console_state.col = to_row, to_col
    # this may alter state.console_state.row, state.console_state.col
    check_pos(scroll_ok)
    # move cursor and reset cursor attribute
    state.console_state.screen.move_cursor(state.console_state.row, state.console_state.col)

def check_pos(scroll_ok=True):
    """ Check if we have crossed the screen boundaries and move as needed. """
    oldrow, oldcol = state.console_state.row, state.console_state.col
    if state.console_state.bottom_row_allowed:
        if state.console_state.row == state.console_state.screen.mode.height:
            state.console_state.col = min(state.console_state.screen.mode.width, state.console_state.col)
            if state.console_state.col < 1:
                state.console_state.col += 1
            state.console_state.screen.move_cursor(state.console_state.row, state.console_state.col)
            return state.console_state.col == oldcol
        else:
            # if row > height, we also end up here
            # (eg if we do INPUT on the bottom row)
            # adjust viewport if necessary
            state.console_state.bottom_row_allowed = False
    # see if we need to move to the next row
    if state.console_state.col > state.console_state.screen.mode.width:
        if state.console_state.row < state.console_state.scroll_height or scroll_ok:
            # either we don't nee to scroll, or we're allowed to
            state.console_state.col -= state.console_state.screen.mode.width
            state.console_state.row += 1
        else:
            # we can't scroll, so we just stop at the right border
            state.console_state.col = state.console_state.screen.mode.width
    # see if we eed to move a row up
    elif state.console_state.col < 1:
        if state.console_state.row > state.console_state.view_start:
            state.console_state.col += state.console_state.screen.mode.width
            state.console_state.row -= 1
        else:
            state.console_state.col = 1
    # see if we need to scroll
    if state.console_state.row > state.console_state.scroll_height:
        if scroll_ok:
            state.console_state.screen.scroll()
        state.console_state.row = state.console_state.scroll_height
    elif state.console_state.row < state.console_state.view_start:
        state.console_state.row = state.console_state.view_start
    state.console_state.screen.move_cursor(state.console_state.row, state.console_state.col)
    # signal position change
    return (state.console_state.row == oldrow and
             state.console_state.col == oldcol)

def start_line():
    """ Move the cursor to the start of the next line, this line if empty. """
    if state.console_state.col != 1:
        for echo in redirect.output_echos:
            echo('\r\n')
        check_pos(scroll_ok=True)
        set_pos(state.console_state.row + 1, 1)
    # ensure line above doesn't wrap
    state.console_state.screen.apage.row[state.console_state.row-2].wrap = False

def write_error_message(msg, linenum):
    """ Write an error message to the console. """
    start_line()
    write(msg)
    if linenum is not None and linenum > -1 and linenum < 65535:
        write(' in %i' % linenum)
    write_line(' ')


################################################

prepare()
