"""
PC-BASIC - draw_and_play.py
DRAW and PLAY macro language stream utilities

(c) 2013, 2014, 2015, 2016 Rob Hagemans
This file is released under the GNU GPL version 3.
"""

import string

import error
import vartypes
import representation
import util
import var
import state

# generic for both macro languages
ml_whitepace = ' '

def get_value_for_varptrstr(varptrstr):
    """ Get a value given a VARPTR$ representation. """
    if len(varptrstr) < 3:
        raise error.RunError(error.IFC)
    varptrstr = bytearray(varptrstr)
    varptr = vartypes.uint_to_value(bytearray(varptrstr[1:3]))
    found_name = ''
    for name in state.basic_state.var_memory:
        _, var_ptr = state.basic_state.var_memory[name]
        if var_ptr == varptr:
            found_name = name
            break
    if found_name == '':
        raise error.RunError(error.IFC)
    return var.get_var(found_name)

def ml_parse_value(gmls, default=None):
    """ Parse a value in a macro-language string. """
    c = util.skip(gmls, ml_whitepace)
    sgn = -1 if c == '-' else 1
    if c in ('+', '-'):
        gmls.read(1)
        c = util.peek(gmls)
        # don't allow default if sign is given
        default = None
    if c == '=':
        gmls.read(1)
        c = util.peek(gmls)
        if len(c) == 0:
            raise error.RunError(error.IFC)
        elif ord(c) > 8:
            name = util.get_var_name(gmls)
            indices = ml_parse_indices(gmls)
            step = var.get_var_or_array(name, indices)
            util.require_read(gmls, (';',), err=error.IFC)
        else:
            # varptr$
            step = get_value_for_varptrstr(gmls.read(3))
    elif c and c in string.digits:
        step = ml_parse_const(gmls)
    elif default is not None:
        step = default
    else:
        raise error.RunError(error.IFC)
    if sgn == -1:
        step = vartypes.number_neg(step)
    return step

def ml_parse_number(gmls, default=None):
    """ Parse and return a number value in a macro-language string. """
    return vartypes.pass_int_unpack(ml_parse_value(gmls, default), err=error.IFC)

def ml_parse_const(gmls):
    """ Parse and return a constant value in a macro-language string. """
    c = util.skip(gmls, ml_whitepace)
    if c and c in string.digits:
        numstr = ''
        while c and c in string.digits:
            gmls.read(1)
            numstr += c
            c = util.skip(gmls, ml_whitepace)
        return representation.str_to_value_keep(('$', numstr))
    else:
        raise error.RunError(error.IFC)

def ml_parse_const_int(gmls):
    """ Parse a constant value in a macro-language string, return Python int. """
    return vartypes.pass_int_unpack(ml_parse_const(gmls), err=error.IFC)

def ml_parse_string(gmls):
    """ Parse a string value in a macro-language string. """
    c = util.skip(gmls, ml_whitepace)
    if len(c) == 0:
        raise error.RunError(error.IFC)
    elif ord(c) > 8:
        name = util.get_var_name(gmls, err=error.IFC)
        indices = ml_parse_indices(gmls)
        sub = var.get_var_or_array(name, indices)
        util.require_read(gmls, (';',), err=error.IFC)
        return vartypes.pass_string_unpack(sub, err=error.IFC)
    else:
        # varptr$
        return vartypes.pass_string_unpack(get_value_for_varptrstr(gmls.read(3)))

def ml_parse_indices(gmls):
    """ Parse constant array indices. """
    indices = []
    c = util.skip(gmls, ml_whitepace)
    if c in ('[', '('):
        gmls.read(1)
        while True:
            indices.append(ml_parse_const_int(gmls))
            c = util.skip(gmls, ml_whitepace)
            if c == ',':
                gmls.read(1)
            else:
                break
        util.require_read(gmls, (']', ')'))
    return indices
