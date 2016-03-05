"""
PC-BASIC - machine.py
Machine emulation and memory model

(c) 2013, 2014, 2015 Rob Hagemans
This file is released under the GNU GPL version 3.
"""

import logging

import config
import state
import backend
import inputs
import display
import vartypes
import var
import error
import memory
import devices
import program
import timedate
import unicodepage
# for state.console_state globals
import console
# ensure state.io_state.devices is populated with com ports
import ports

# pre-defined PEEK outputs
peek_values = {}

# where to find the rom font (chars 0-127)
rom_font_addr = 0xfa6e
# where to find the ram font (chars 128-254)
ram_font_addr = 0x500
# protection flag
protection_flag_addr = 1450

# base for our low-memory addresses
low_segment = 0

# data memory model: current segment
state.basic_state.segment = memory.data_segment

def prepare():
    """ Initialise machine module. """
    global allow_code_poke, tandy_syntax
    try:
        for a in config.get('peek'):
            seg, addr, val = a.split(':')
            peek_values[int(seg)*0x10 + int(addr)] = int(val)
    except (TypeError, ValueError):
        pass
    allow_code_poke = config.get('allow-code-poke')
    tandy_syntax = config.get('syntax') == 'tandy'

def peek(addr):
    """ Retrieve the value at an emulated memory location. """
    if addr < 0:
        addr += 0x10000
    addr += state.basic_state.segment*0x10
    return get_memory(addr)

def poke(addr, val):
    """ Set the value at an emulated memory location. """
    if addr < 0:
        addr += 0x10000
    addr += state.basic_state.segment * 0x10
    set_memory(addr, val)

# timer for reading game port
joystick_out_time = timedate.timer_milliseconds()
# time delay for port value to drop to 0 on maximum reading.
#  use 100./255. for 100ms.
joystick_time_factor = 75. / 255.

# serial port base address:
# http://www.petesqbsite.com/sections/tutorials/zines/qbnews/9-com_ports.txt
#            COM1             &H3F8
#            COM2             &H2F8
#            COM3             &H3E8 (not implemented)
#            COM4             &H2E8 (not implemented)
com_base = {0x3f8: 0, 0x2f8: 1}
com_device = [state.io_state.devices['COM1:'], state.io_state.devices['COM2:']]
com_enable_baud_write = [False, False]
com_baud_divisor = [0, 0]
com_break = [False, False]

# parallel port base address:
# http://retired.beyondlogic.org/spp/parallel.htm
# 3BCh - 3BFh  Used for Parallel Ports which were incorporated on to Video Cards - Doesn't support ECP addresses
# 378h - 37Fh  Usual Address For LPT 1
# 278h - 27Fh  Usual Address For LPT 2
lpt_device = [state.io_state.devices['LPT1:'], state.io_state.devices['LPT2:']]

def inp(port):
    """ Get the value in an emulated machine port. """
    # keyboard
    if port == 0x60:
        backend.wait()
        return state.console_state.keyb.last_scancode
    # game port (joystick)
    elif port == 0x201:
        value = (
            (not inputs.stick_is_firing[0][0]) * 0x40 +
            (not inputs.stick_is_firing[0][1]) * 0x20 +
            (not inputs.stick_is_firing[1][0]) * 0x10 +
            (not inputs.stick_is_firing[1][1]) * 0x80)
        decay = (timedate.timer_milliseconds() - joystick_out_time) % 86400000
        if decay < inputs.stick_axis[0][0] * joystick_time_factor:
            value += 0x04
        if decay < inputs.stick_axis[0][1] * joystick_time_factor:
            value += 0x02
        if decay < inputs.stick_axis[1][0] * joystick_time_factor:
            value += 0x01
        if decay < inputs.stick_axis[1][1] * joystick_time_factor:
            value += 0x08
        return value
    elif port in (0x379, 0x279):
        # parallel port input ports
        # http://www.aaroncake.net/electronics/qblpt.htm
        # http://retired.beyondlogic.org/spp/parallel.htm
        lpt_port_nr = 0 if port >= 0x378 else 1
        base_addr = {0: 0x378, 1: 0x278}
        if lpt_device[lpt_port_nr].stream is None:
            return 0
        # get status port
        busy, ack, paper, select, err = lpt_device[lpt_port_nr].stream.get_status()
        return busy * 0x80 | ack * 0x40 | paper * 0x20 | select * 0x10 | err * 0x8
    else:
        # serial port machine ports
        # http://www.qb64.net/wiki/index.php/Port_Access_Libraries#Serial_Communication_Registers
        # http://control.com/thread/1026221083
        for base_addr, com_port_nr in com_base.iteritems():
            com_port = com_device[com_port_nr]
            if com_port.stream is None:
                continue
            # Line Control Register: base_address + 3 (r/w)
            if port == base_addr + 3:
                _, parity, bytesize, stopbits = com_port.stream.get_params()
                value = com_enable_baud_write[com_port_nr] * 0x80
                value += com_break[com_port_nr] * 0x40
                value += {'S': 0x38, 'M': 0x28, 'E': 0x18, 'O': 0x8, 'N': 0}[parity]
                if stopbits > 1:
                    value += 0x4
                value += bytesize - 5
                return value
            # Line Status Register: base_address + 5 (read only)
            elif port == base_addr + 5:
                # not implemented
                return 0
            # Modem Status Register: base_address + 6 (read only)
            elif port == base_addr + 6:
                cd, ri, dsr, cts = com_port.stream.get_pins()
                # delta bits not implemented
                return (cd*0x80 + ri*0x40 + dsr*0x20 + cts*0x10)
        # addr isn't one of the covered ports
        return 0

def out(addr, val):
    """ Send a value to an emulated machine port. """
    global joystick_out_time
    if addr == 0x201:
        # game port reset
        joystick_out_time = timedate.timer_milliseconds()
    elif addr == 0x3c5:
        # officially, requires OUT &H3C4, 2 first (not implemented)
        state.console_state.screen.mode.set_plane_mask(val)
    elif addr == 0x3cf:
        # officially, requires OUT &H3CE, 4 first (not implemented)
        state.console_state.screen.mode.set_plane(val)
    elif addr == 0x3d8:
        #OUT &H3D8,&H1A: REM enable color burst
        #OUT &H3D8,&H1E: REM disable color burst
        # 0x1a == 0001 1010     0x1e == 0001 1110
        state.console_state.screen.set_colorburst(val & 4 == 0)
    elif addr in (0x378, 0x37A, 0x278, 0x27A):
        # parallel port output ports
        # http://www.aaroncake.net/electronics/qblpt.htm
        # http://retired.beyondlogic.org/spp/parallel.htm
        lpt_port_nr = 0 if addr >= 0x378 else 1
        base_addr = {0: 0x378, 1: 0x278}
        if lpt_device[lpt_port_nr].stream is None:
            return
        if addr - base_addr[lpt_port_nr] == 0:
            # set data port
            lpt_device[lpt_port_nr].stream.write(chr(val))
        else:
            # set control port
            lpt_device[lpt_port_nr].stream.set_control(
                select=val & 0x8, init=val&0x4, lf=val&0x2, strobe=val&0x1)
    else:
        # serial port machine ports
        # http://www.qb64.net/wiki/index.php/Port_Access_Libraries#Serial_Communication_Registers
        # http://control.com/thread/1026221083
        for base_addr, com_port_nr in com_base.iteritems():
            com_port = com_device[com_port_nr]

            if com_port.stream is None:
                continue
            # ports at base addr and the next one are used for writing baud rate
            # (among other things that aren't implemented)
            if addr in (base_addr, base_addr+1) and com_enable_baud_write[com_port_nr]:

                if addr == base_addr:
                    com_baud_divisor[com_port_nr] = (com_baud_divisor[com_port_nr] & 0xff00) + val
                elif addr == base_addr + 1:
                    com_baud_divisor[com_port_nr] = val*0x100 + (com_baud_divisor[com_port_nr] & 0xff)
                if com_baud_divisor[com_port_nr]:
                    baudrate, parity, bytesize, stopbits = com_port.stream.get_params()
                    baudrate = 115200 // com_baud_divisor[com_port_nr]
                    com_port.stream.set_params(baudrate, parity, bytesize, stopbits)
            # Line Control Register: base_address + 3 (r/w)
            elif addr == base_addr + 3:
                baudrate, parity, bytesize, stopbits = com_port.stream.get_params()
                if val & 0x80:
                    com_enable_baud_write[com_port_nr] = True
                # break condition
                com_break[com_port_nr] = (val & 0x40) != 0
                # parity
                parity = {0x38:'S', 0x28:'M', 0x18:'E', 0x8:'O', 0:'N'}[val&0x38]
                # stopbits
                if val & 0x4:
                    # 2 or 1.5 stop bits
                    stopbits = 2
                else:
                    # 1 stop bit
                    stopbits = 1
                # set byte size to 5, 6, 7, 8
                bytesize = (val & 0x3) + 5
                com_port.stream.set_params(baudrate, parity, bytesize, stopbits)
                com_port.stream.set_pins(brk=com_break[com_port_nr])
            # Modem Control Register: base_address + 4 (r/w)
            elif addr == base_addr + 4:
                com_port.stream.set_pins(rts=val & 0x2, dtr=val & 0x1)

def wait(addr, ander, xorer):
    """ Wait untial an emulated machine port has a specified value. """
    store_suspend = state.basic_state.events.suspend_all
    state.basic_state.events.suspend_all = True
    while (inp(addr) ^ xorer) & ander == 0:
        backend.wait()
    state.basic_state.events.suspend_all = store_suspend

def bload(g, offset):
    """ Load a file into a block of memory. """
    # size gets ignored; even the \x1a at the end gets dumped onto the screen.
    seg = g.seg
    if offset is None:
        offset = g.offset
    buf = bytearray(g.read())
    # remove any EOF marker at end
    if buf and buf[-1] == 0x1a:
        buf = buf[:-1]
    if tandy_syntax:
        buf = buf[:-7]
    addr = seg * 0x10 + offset
    set_memory_block(addr, buf)

def bsave(g, offset, length):
    """ Save a block of memory into a file. """
    addr = state.basic_state.segment * 0x10 + offset
    g.write(str(get_memory_block(addr, length)))
    # Tandys repeat the header at the end of the file
    if tandy_syntax:
        g.write('\xfd' + vartypes.value_to_uint(state.basic_state.segment) +
                vartypes.value_to_uint(offset) +
                vartypes.value_to_uint(length))

def varptr_file(filenum):
    """ Get address of FCB for a given file number. """
    if filenum < 1 or filenum > devices.max_files:
        raise error.RunError(error.BAD_FILE_NUMBER)
    return memory.field_mem_base + filenum * memory.field_mem_offset + 6

def varptr(name, indices):
    """Get address of variable. """
    name = vartypes.complete_name(name)
    if indices == []:
        try:
            _, var_ptr = state.basic_state.var_memory[name]
            return var_ptr
        except KeyError:
            return -1
    else:
        try:
            dimensions, _, _ = state.basic_state.arrays[name]
            _, array_ptr = state.basic_state.array_memory[name]
            # arrays are kept at the end of the var list
            return state.basic_state.var_current + array_ptr + var.var_size_bytes(name) * var.index_array(indices, dimensions)
        except KeyError:
            return -1

###############################################################################
# IMPLEMENTATION

def get_memory(addr):
    """ Retrieve the value at an emulated memory location. """
    try:
        # try if there's a preset value
        return peek_values[addr]
    except KeyError:
        if addr >= memory.rom_segment*0x10:
            # ROM font
            return max(0, get_rom_memory(addr))
        elif addr >= memory.ram_font_segment*0x10:
            # RAM font
            return max(0, get_font_memory(addr))
        elif addr >= memory.video_segment*0x10:
            # graphics and text memory
            return max(0, get_video_memory(addr))
        elif addr >= memory.data_segment*0x10 + memory.var_start():
            # variable memory
            return max(0, get_data_memory(addr))
        elif addr >= memory.data_segment*0x10 + memory.code_start:
            # code memory
            return max(0, get_code_memory(addr))
        elif addr >= memory.data_segment*0x10 + memory.field_mem_start:
            # file & FIELD memory
            return max(0, get_field_memory(addr))
        elif addr >= memory.data_segment*0x10:
            # other BASIC data memory
            return max(0, get_basic_memory(addr))
        elif addr >= low_segment*0x10:
            return max(0, get_low_memory(addr))
        else:
            return 0

def set_memory(addr, val):
    """ Set the value at an emulated memory location. """
    if addr >= memory.rom_segment*0x10:
        # ROM includes font memory
        pass
    elif addr >= memory.ram_font_segment*0x10:
        # RAM font memory
        set_font_memory(addr, val)
    elif addr >= memory.video_segment*0x10:
        # graphics and text memory
        set_video_memory(addr, val)
    elif addr >= memory.data_segment*0x10 + memory.var_start():
        # POKING in variables
        set_data_memory(addr, val)
    elif addr >= memory.data_segment*0x10 + memory.code_start:
        # code memory
        set_code_memory(addr, val)
    elif addr >= memory.data_segment*0x10 + memory.field_mem_start:
        # file & FIELD memory
        set_field_memory(addr, val)
    elif addr >= memory.data_segment*0x10:
        set_basic_memory(addr, val)
    elif addr >= low_segment*0x10:
        set_low_memory(addr, val)
    else:
        pass

def not_implemented_poke(addr, val):
    """ POKE into not implemented location; retain value. """
    peek_values[addr] = val

def not_implemented_pass(addr, val):
    """ POKE into not implemented location; ignore. """
    pass

# sections of memory for which POKE is not currently implemented
set_data_memory = not_implemented_poke
set_field_memory = not_implemented_poke

def get_memory_block(addr, length):
    """ Retrieve a contiguous block of bytes from memory. """
    block = bytearray()
    if addr >= memory.video_segment*0x10:
        video_len = 0x20000 - (addr - memory.video_segment*0x10)
        # graphics and text memory - specialised call
        block += get_video_memory_block(addr, min(length, video_len))
        addr += video_len
        length -= video_len
    for a in range(addr, addr+length):
        block += chr(max(0, get_memory(a)))
    return block

def set_memory_block(addr, buf):
    """ Set a contiguous block of bytes in memory. """
    if addr >= memory.video_segment*0x10:
        video_len = 0x20000 - (addr - memory.video_segment*0x10)
        # graphics and text memory - specialised call
        set_video_memory_block(addr, buf[:video_len])
        addr += video_len
        buf = buf[video_len:]
    for a in range(len(buf)):
        set_memory(addr + a, buf[a])

###############################################################################

def get_name_in_memory(name, offset):
    """ Memory representation of variable name. """
    if offset == 0:
        return var.byte_size[name[-1]]
    elif offset == 1:
        return ord(name[0].upper())
    elif offset == 2:
        if len(name) > 2:
            return ord(name[1].upper())
        else:
            return 0
    elif offset == 3:
        if len(name) > 3:
            return len(name)-3
        else:
            return 0
    else:
        # rest of name is encoded such that c1 == 'A'
        return ord(name[offset-1].upper()) - ord('A') + 0xC1

def get_field_memory(address):
    """ Retrieve data from FIELD buffer. """
    address -= memory.data_segment * 0x10
    if address < memory.field_mem_start:
        return -1
    # find the file we're in
    start = address - memory.field_mem_start
    number = 1 + start // memory.field_mem_offset
    offset = start % memory.field_mem_offset
    try:
        return state.io_state.fields[number].buffer[offset]
    except (KeyError, IndexError):
        return -1

def get_code_memory(address):
    """ Retrieve data from program code. """
    address -= memory.data_segment * 0x10 + memory.code_start
    code = state.basic_state.bytecode.getvalue()
    try:
        return ord(code[address])
    except IndexError:
        return -1

def set_code_memory(address, val):
    """ Change program code. """
    if not allow_code_poke:
        logging.warning('Ignored POKE into program code')
    else:
        address -= memory.data_segment * 0x10 + memory.code_start
        loc = state.basic_state.bytecode.tell()
        # move pointer to end
        state.basic_state.bytecode.seek(0, 2)
        if address > state.basic_state.bytecode.tell():
            state.basic_state.bytecode.write('\0' *
                        (address-state.basic_state.bytecode.tell()) + chr(val))
        else:
            state.basic_state.bytecode.seek(address)
            state.basic_state.bytecode.write(chr(val))
        # restore program pointer
        state.basic_state.bytecode.seek(loc)
        program.rebuild_line_dict()

def get_data_memory(address):
    """ Retrieve data from data memory. """
    address -= memory.data_segment * 0x10
    if address < state.basic_state.var_current:
        return get_data_memory_var(address)
    elif address < state.basic_state.var_current + state.basic_state.array_current:
        return get_data_memory_array(address)
    elif address > state.basic_state.strings.current:
        return get_data_memory_string(address)
    else:
        # unallocated var space
        return -1

def get_data_memory_var(address):
    """ Retrieve data from data memory: variable space """
    name_addr = -1
    var_addr = -1
    the_var = None
    for name in state.basic_state.var_memory:
        name_try, var_try = state.basic_state.var_memory[name]
        if name_try <= address and name_try > name_addr:
            name_addr, var_addr = name_try, var_try
            the_var = name
    if the_var is None:
        return -1
    if address >= var_addr:
        offset = address - var_addr
        if offset >= var.byte_size[the_var[-1]]:
            return -1
        var_rep = state.basic_state.variables[the_var]
        return var_rep[offset]
    else:
        offset = address - name_addr
        return get_name_in_memory(the_var, offset)

def get_data_memory_array(address):
    """ Retrieve data from data memory: array space """
    name_addr = -1
    arr_addr = -1
    the_arr = None
    for name in state.basic_state.array_memory:
        name_try, arr_try = state.basic_state.array_memory[name]
        if name_try <= address and name_try > name_addr:
            name_addr, arr_addr = name_try, arr_try
            the_arr = name
    if the_arr is None:
        return -1
    if address >= state.basic_state.var_current + arr_addr:
        offset = address - arr_addr - state.basic_state.var_current
        if offset >= var.array_size_bytes(the_arr):
            return -1
        _, byte_array, _ = state.basic_state.arrays[the_arr]
        return byte_array[offset]
    else:
        offset = address - name_addr - state.basic_state.var_current
        if offset < max(3, len(the_arr))+1:
            return get_name_in_memory(the_arr, offset)
        else:
            offset -= max(3, len(the_arr))+1
            dimensions, _, _ = state.basic_state.arrays[the_arr]
            data_rep = vartypes.value_to_uint(var.array_size_bytes(the_arr) + 1 + 2*len(dimensions)) + chr(len(dimensions))
            for d in dimensions:
                data_rep += vartypes.value_to_uint(d + 1 - state.basic_state.array_base)
            return data_rep[offset]

def get_data_memory_string(address):
    """ Retrieve data from data memory: string space """
    # find the variable we're in
    str_nearest = -1
    the_var = None
    for name in state.basic_state.variables:
        if name[-1] != '$':
            continue
        v = state.basic_state.variables[name]
        str_try = state.basic_state.strings.address(v)
        if str_try <= address and str_try > str_nearest:
            str_nearest = str_try
            the_var = v
    if the_var is None:
        for name in state.basic_state.arrays:
            if name[-1] != '$':
                continue
            _, lst, _ = state.basic_state.arrays[name]
            for i in range(0, len(lst), 3):
                str_try = state.basic_state.strings.address(lst[i:i+3])
                if str_try <= address and str_try > str_nearest:
                    str_nearest = str_try
                    the_var = lst[i:i+3]
    try:
        return state.basic_state.strings.retrieve(the_var)[address - str_nearest]
    except (IndexError, AttributeError, KeyError):
        return -1

###############################################################
# video memory model

def get_video_memory(addr):
    """ Retrieve a byte from video memory. """
    return state.console_state.screen.mode.get_memory(addr, 1)[0]

def set_video_memory(addr, val):
    """ Set a byte in video memory. """
    return state.console_state.screen.mode.set_memory(addr, [val])

def get_video_memory_block(addr, length):
    """ Retrieve a contiguous block of bytes from video memory. """
    return bytearray(state.console_state.screen.mode.get_memory(addr, length))

def set_video_memory_block(addr, some_bytes):
    """ Set a contiguous block of bytes in video memory. """
    state.console_state.screen.mode.set_memory(addr, some_bytes)

###############################################################################

def get_rom_memory(addr):
    """ Retrieve data from ROM. """
    addr -= memory.rom_segment*0x10 + rom_font_addr
    char = addr // 8
    if char > 127 or char<0:
        return -1
    return ord(display.fonts[8].fontdict[
            state.console_state.codepage.to_unicode(chr(char), u'\0')][addr%8])

def get_font_memory(addr):
    """ Retrieve RAM font data. """
    addr -= memory.ram_font_segment*0x10 + ram_font_addr
    char = addr // 8 + 128
    if char < 128 or char > 254:
        return -1
    return ord(display.fonts[8].fontdict[
            state.console_state.codepage.to_unicode(chr(char), u'\0')][addr%8])

def set_font_memory(addr, value):
    """ Retrieve RAM font data. """
    addr -= memory.ram_font_segment*0x10 + ram_font_addr
    char = addr // 8 + 128
    if char < 128 or char > 254:
        return
    uc = state.console_state.codepage.to_unicode(chr(char))
    if uc:
        old = display.fonts[8].fontdict[uc]
        display.fonts[8].fontdict[uc] = old[:addr%8]+chr(value)+old[addr%8+1:]
        state.console_state.screen.rebuild_glyph(char)

#################################################################################

def get_basic_memory(addr):
    """ Retrieve data from BASIC memory. """
    addr -= memory.data_segment*0x10
    # DS:2c, DS:2d  end of memory available to BASIC
    if addr == 0x2C:
        return memory.total_memory % 256
    elif addr == 0x2D:
        return memory.total_memory // 256
    # DS:30, DS:31: pointer to start of program, excluding initial \0
    elif addr == 0x30:
        return (memory.code_start+1) % 256
    elif addr == 0x31:
        return (memory.code_start+1) // 256
    # DS:358, DS:359: start of variable space
    elif addr == 0x358:
        return memory.var_start() % 256
    elif addr == 0x359:
        return memory.var_start() // 256
    # DS:35A, DS:35B: start of array space
    elif addr == 0x35A:
        return state.basic_state.var_current % 256
    elif addr == 0x35B:
        return state.basic_state.var_current // 256
    # DS:35C, DS:35D: end of array space
    elif addr == 0x35C:
        return (state.basic_state.var_current + state.basic_state.array_current) % 256
    elif addr == 0x35D:
        return (state.basic_state.var_current + state.basic_state.array_current) // 256
    elif addr == protection_flag_addr:
        return state.basic_state.protected * 255
    return -1

def set_basic_memory(addr, val):
    """ Change BASIC memory. """
    addr -= memory.data_segment*0x10
    if addr == protection_flag_addr and not program.dont_protect:
        state.basic_state.protected = (val != 0)

key_buffer_offset = 30
blink_enabled = True

def get_low_memory(addr):
    """ Retrieve data from low memory. """
    addr -= low_segment*0x10
    # from MEMORY.ABC: PEEKs and POKEs (Don Watkins)
    # http://www.qbasicnews.com/abc/showsnippet.php?filename=MEMORY.ABC&snippet=6
    # &h40:&h17 keyboard flag
    # &H80 - Insert state active
    # &H40 - CapsLock state has been toggled
    # &H20 - NumLock state has been toggled
    # &H10 - ScrollLock state has been toggled
    # &H08 - Alternate key depressed
    # &H04 - Control key depressed
    # &H02 - Left shift key depressed
    # &H01 - Right shift key depressed
    # &h40:&h18 keyboard flag
    # &H80 - Insert key is depressed
    # &H40 - CapsLock key is depressed
    # &H20 - NumLock key is depressed
    # &H10 - ScrollLock key is depressed
    # &H08 - Suspend key has been toggled
    backend.wait()
    # 108-115 control Ctrl-break capture; not implemented (see PC Mag POKEs)
    # 1040 monitor type
    if addr == 124:
        return ram_font_addr % 256
    elif addr == 125:
        return ram_font_addr // 256
    elif addr == 126:
        return memory.ram_font_segment % 256
    elif addr == 127:
        return memory.ram_font_segment // 256
    elif addr == 1040:
        if display.mono_monitor:
            # mono
            return 48 + 6
        else:
            # 80x25 graphics
            return 32 + 6
    # http://textfiles.com/programming/peekpoke.txt
    #   "(PEEK (1041) AND 14)/2" WILL PROVIDE NUMBER OF RS232 PORTS INSTALLED.
    #   "(PEEK (1041) AND 16)/16" WILL PROVIDE NUMBER OF GAME PORTS INSTALLED.
    #   "(PEEK (1041) AND 192)/64" WILL PROVIDE NUMBER OF PRINTERS INSTALLED.
    elif addr == 1041:
        return (2 * ((state.io_state.devices['COM1:'].stream is not None) +
                    (state.io_state.devices['COM2:'].stream is not None)) +
                16 +
                64 * ((state.io_state.devices['LPT1:'].stream is not None) +
                    (state.io_state.devices['LPT2:'].stream is not None) +
                    (state.io_state.devices['LPT3:'].stream is not None)))
    elif addr == 1047:
        return state.console_state.keyb.mod
    # not implemented: peek(1048)==4 if sysrq pressed, 0 otherwise
    elif addr == 1048:
        return 0
    elif addr == 1049:
        return int(state.console_state.keyb.keypad_ascii or 0)%256
    elif addr == 1050:
        # keyboard ring buffer starts at n+1024; lowest 1054
        return (state.console_state.keyb.buf.start*2 + key_buffer_offset) % 256
    elif addr == 1051:
        return (state.console_state.keyb.buf.start*2 + key_buffer_offset) // 256
    elif addr == 1052:
        # ring buffer ends at n + 1023
        return (state.console_state.keyb.buf.stop()*2 + key_buffer_offset) % 256
    elif addr == 1053:
        return (state.console_state.keyb.buf.stop()*2 + key_buffer_offset) // 256
    elif addr in range(1024+key_buffer_offset, 1024+key_buffer_offset+32):
        index = (addr-1024-key_buffer_offset)//2
        odd = (addr-1024-key_buffer_offset)%2
        c, scan = state.console_state.keyb.buf.ring_read(index)
        if odd:
            return scan
        elif c == '':
            return 0
        else:
            # however, arrow keys (all extended scancodes?) give 0xe0 instead of 0
            return ord(c[0])
    # 1097 screen mode number
    elif addr == 1097:
        # these are the low-level mode numbers used by mode switching interrupt
        cval = state.console_state.screen.colorswitch % 2
        if state.console_state.screen.mode.is_text_mode:
            if (display.video_capabilities in ('mda', 'ega_mono') and
                    state.console_state.screen.mode.width == 80):
                return 7
            return (state.console_state.screen.mode.width == 40)*2 + cval
        elif state.console_state.screen.mode.name == '320x200x4':
            return 4 + cval
        else:
            mode_num = {'640x200x2': 6, '160x200x16': 8, '320x200x16pcjr': 9,
                '640x200x4': 10, '320x200x16': 13, '640x200x16': 14,
                '640x350x4': 15, '640x350x16': 16, '640x400x2': 0x40,
                '320x200x4pcjr': 4 }
                # '720x348x2': ? # hercules - unknown
            try:
                return mode_num[state.console_state.screen.mode.name]
            except KeyError:
                return 0xff
    # 1098, 1099 screen width
    elif addr == 1098:
        return state.console_state.screen.mode.width % 256
    elif addr == 1099:
        return state.console_state.screen.mode.width // 256
    # 1100, 1101 graphics page buffer size (32k for screen 9, 4k for screen 0)
    # 1102, 1103 zero (PCmag says graphics page buffer offset)
    elif addr == 1100:
        return state.console_state.screen.mode.page_size % 256
    elif addr == 1101:
        return state.console_state.screen.mode.page_size // 256
    # 1104 + 2*n (cursor column of page n) - 1
    # 1105 + 2*n (cursor row of page n) - 1
    # we only keep track of one row,col position
    elif addr in range(1104, 1120, 2):
        return state.console_state.col - 1
    elif addr in range(1105, 1120, 2):
        return state.console_state.row - 1
    # 1120, 1121 cursor shape
    elif addr == 1120:
        return state.console_state.screen.cursor.to_line
    elif addr == 1121:
        return state.console_state.screen.cursor.from_line
    # 1122 visual page number
    elif addr == 1122:
        return state.console_state.screen.vpagenum
    # 1125 screen mode info
    elif addr == 1125:
        # bit 0: only in text mode?
        # bit 2: should this be colorswitch or colorburst_is_enabled?
        return ((state.console_state.screen.mode.width == 80) * 1 +
                (not state.console_state.screen.mode.is_text_mode) * 2 +
                 state.console_state.screen.colorswitch * 4 + 8 +
                 (state.console_state.screen.mode.name == '640x200x2') * 16 +
                 blink_enabled * 32)
    # 1126 color
    elif addr == 1126:
        if state.console_state.screen.mode.name == '320x200x4':
            return (state.console_state.screen.palette.get_entry(0)
                    + 32 * state.console_state.screen.cga4_palette_num)
        elif state.console_state.screen.mode.is_text_mode:
            return state.console_state.screen.border_attr % 16
            # not implemented: + 16 "if current color specified through
            # COLOR f,b with f in [0,15] and b > 7
    # 1296, 1297: zero (PCmag says data segment address)
    return -1

def set_low_memory(addr, value):
    """ Set data in low memory. """
    addr -= low_segment*0x10
    if addr == 1047:
        state.console_state.keyb.mod = value
    # from basic_ref_3.pdf: the keyboard buffer may be cleared with
    # DEF SEG=0: POKE 1050, PEEK(1052)
    elif addr == 1050:
        # keyboard ring buffer starts at n+1024; lowest 1054
        state.console_state.keyb.buf.ring_set_boundaries(
                (value - key_buffer_offset) // 2,
                state.console_state.keyb.buf.stop())
    elif addr == 1052:
        # ring buffer ends at n + 1023
        state.console_state.keyb.buf.ring_set_boundaries(
                state.console_state.keyb.buf.start,
                (value - key_buffer_offset) // 2)
    elif addr in range(1024+key_buffer_offset, 1024+key_buffer_offset+32):
        index = (addr-1024-key_buffer_offset)//2
        odd = (addr-1024-key_buffer_offset)%2
        c, scan = state.console_state.keyb.buf.ring_read(index)
        if odd:
            scan = value
        elif value in (0, 0xe0):
            c = ''
        else:
            c = chr(value)
        state.console_state.keyb.buf.ring_write(index, c, scan)

prepare()
