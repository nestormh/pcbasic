"""
PC-BASIC - var.py
Variable & array management

(c) 2013, 2014, 2015, 2016 Rob Hagemans
This file is released under the GNU GPL version 3.
"""

from operator import itemgetter

import error
import vartypes
import state
import memory

byte_size = {'$': 3, '%': 2, '!': 4, '#': 8}

def prepare():
    """ Initialise the var module """
    clear_variables()

class StringSpace(object):
    """ String space is a table of strings accessible by their 2-byte pointers. """

    def __init__(self):
        """ Initialise empty string space. """
        self.clear()

    def clear(self):
        """ Empty string space. """
        self.strings = {}
        # strings are placed at the top of string memory, just below the stack
        self.current = memory.stack_start()

    def retrieve(self, key):
        """ Retrieve a string by its 3-byte sequence. 2-byte keys allowed, but will return longer string for empty string. """
        key = str(key)
        if len(key) == 2:
            return self.strings[key]
        elif len(key) == 3:
            # if string length == 0, return empty string
            return bytearray('') if ord(key[0]) == 0 else self.strings[key[-2:]]
        else:
            raise KeyError('String key %s has wrong length.' % repr(key))

    def copy_packed(self, key):
        """ Return a packed copy of the string by its 2-byte key or 3-byte sequence. """
        return vartypes.pack_string(self.retrieve(key)[:])

    def store(self, string_buffer, address=None):
        """ Store a new string and return the 3-byte memory sequence. """
        # don't store overlong strings
        if len(string_buffer) > 255:
            raise error.RunError(error.STRING_TOO_LONG)
        if len(string_buffer) > fre():
            raise error.RunError(error.OUT_OF_STRING_SPACE)
        if address is None:
            # find new string address
            self.current -= len(string_buffer)
            address = self.current + 1
        key = str(vartypes.value_to_uint(address))
        # don't store empty strings
        if len(string_buffer) > 0:
            if key in self.strings:
                raise KeyError('String key %s at %d already defined.' % (repr(key), address))
            self.strings[key] = string_buffer
        return bytearray(chr(len(string_buffer)) + key)

    def address(self, key):
        """ Return the address of a given key. """
        return vartypes.uint_to_value(bytearray(key[-2:]))

def get_string_copy_packed(sequence):
    """ Return a packed copy of a string from its 3-byte sequence. """
    length = ord(sequence[0:1])
    address = vartypes.uint_to_value(sequence[-2:])
    if address >= memory.var_start():
        # string is stored in string space
        return state.basic_state.strings.copy_packed(sequence)
    else:
        # string is stored in code space or field buffers
        if address < memory.field_mem_start:
            return vartypes.pack_string('\0' * length)
        # find the file we're in
        start = address - memory.field_mem_start
        number = 1 + start // memory.field_mem_offset
        offset = start % memory.field_mem_offset
        try:
            return vartypes.pack_string(state.io_state.fields[number].buffer[
                                                        offset : offset+length])
        except KeyError, IndexError:
            return vartypes.pack_string('\0' * length)

def clear_variables(preserve_common=False, preserve_all=False, preserve_deftype=False):
    """ Reset and clear variables, arrays, common definitions and functions. """
    if not preserve_deftype:
        # deftype is not preserved on CHAIN with ALL, but is preserved with MERGE
        state.basic_state.deftype = ['!']*26
    if not preserve_all:
        if preserve_common:
            # preserve COMMON variables (CHAIN does this)
            common, common_arrays, common_strings = {}, {}, {}
            for varname in state.basic_state.common_names:
                try:
                    common[varname] = state.basic_state.variables[varname]
                except KeyError:
                    pass
            for varname in state.basic_state.common_array_names:
                try:
                    common_arrays[varname] = state.basic_state.arrays[varname]
                except KeyError:
                    pass
        else:
            # clear option base
            state.basic_state.array_base = None
            common = {}
            common_arrays = {}
            # at least I think these should be cleared by CLEAR?
            state.basic_state.common_names = []
            state.basic_state.common_array_names = []
        # restore only common variables
        # this is a re-assignment which is not FOR-safe; but clear_variables is only called in CLEAR which also clears the FOR stack
        state.basic_state.variables = {}
        state.basic_state.arrays = {}
        state.basic_state.var_memory = {}
        state.basic_state.array_memory = {}
        state.basic_state.var_current = memory.var_start()
        # arrays are always kept after all vars
        state.basic_state.array_current = 0
        # functions are cleared except when CHAIN ... ALL is specified
        state.basic_state.functions = {}
        # reset string space
        new_strings = StringSpace()
        # preserve common variables
        # use set_var and dim_array to rebuild memory model
        for v in common:
            if v[-1] == '$':
                state.basic_state.variables[v] = (
                    new_strings.store(bytearray(vartypes.unpack_string(
                        get_string_copy_packed(common[v])
                    ))))
            else:
                set_var(v, (v[-1], common[v]))
        for a in common_arrays:
            dim_array(a, common_arrays[a][0])
            if a[-1] == '$':
                s = bytearray()
                for i in range(0, len(common_arrays[a][1]), byte_size['$']):
                    s += (new_strings.store(bytearray(vartypes.unpack_string(
                        get_string_copy_packed(common_arrays[a][1][i+1:i+byte_size['$']])
                    ))))
                state.basic_state.arrays[a][1] = s
            else:
                state.basic_state.arrays[a] = common_arrays[a]
        state.basic_state.strings = new_strings

def set_var(name, value):
    """ Assign a value to a variable. """
    name = vartypes.complete_name(name)
    type_char = name[-1]
    # check if garbage needs collecting before allocating mem
    size = (max(3, len(name)) + 1 + byte_size[type_char])
    if type_char == '$':
        unpacked = vartypes.pass_string_unpack(value)
        size += len(unpacked)
    if fre() <= size:
        # TODO: GARBTEST difference is because string literal is currently stored in string space, whereas GW stores it in code space.
        collect_garbage()
        if fre() <= size:
            raise error.RunError(error.OUT_OF_MEMORY)
    # assign variables
    if type_char == '$':
        # every assignment to string leads to new pointer being allocated
        # TODO: string literals in programs have the var ptr point to program space.
        state.basic_state.variables[name] = state.basic_state.strings.store(bytearray(unpacked[:]))
    else:
        # make a copy of the value in case we want to use POKE on it - we would change both values otherwise
        # NOTE: this is an in-place copy - crucial for FOR!
        try:
            state.basic_state.variables[name][:] = vartypes.pass_type_keep(name[-1], value)[1][:]
        except KeyError:
            state.basic_state.variables[name] = vartypes.pass_type_keep(name[-1], value)[1][:]
    # update memory model
    # first two bytes: chars of name or 0 if name is one byte long
    if name not in state.basic_state.var_memory:
        name_ptr = state.basic_state.var_current
        var_ptr = name_ptr + max(3, len(name)) + 1 # byte_size first_letter second_letter_or_nul remaining_length_or_nul
        state.basic_state.var_current += max(3, len(name)) + 1 + byte_size[name[-1]]
        state.basic_state.var_memory[name] = (name_ptr, var_ptr)

def get_var(name):
    """ Retrieve the value of a variable. """
    name = vartypes.complete_name(name)
    try:
        if name[-1] == '$':
            return get_string_copy_packed(state.basic_state.variables[name])
        else:
            return (name[-1], state.basic_state.variables[name])
    except KeyError:
        return vartypes.null[name[-1]]

def swap_var(name1, index1, name2, index2):
    """ Swap two variables by reference (Strings) or value (everything else). """
    if name1[-1] != name2[-1]:
        # type mismatch
        raise error.RunError(error.TYPE_MISMATCH)
    elif ((index1 == [] and name1 not in state.basic_state.variables) or
            (index1 != [] and name1 not in state.basic_state.arrays) or
            (index2 == [] and name2 not in state.basic_state.variables) or
            (index2 != [] and name2 not in state.basic_state.arrays)):
        # illegal function call
        raise error.RunError(error.IFC)
    typechar = name1[-1]
    size = byte_size[typechar]
    # swap non-strings by value, strings by address
    if index1 == []:
        p1, off1 = state.basic_state.variables[name1], 0
    else:
        dimensions, p1, _ = state.basic_state.arrays[name1]
        off1 = index_array(index1, dimensions)*size
    if index2 == []:
        p2, off2 = state.basic_state.variables[name2], 0
    else:
        dimensions, p2, _ = state.basic_state.arrays[name2]
        off2 = index_array(index2, dimensions)*size
    # swap the contents
    p1[off1:off1+size], p2[off2:off2+size] =  p2[off2:off2+size], p1[off1:off1+size]
    # inc version
    if name1 in state.basic_state.arrays:
        state.basic_state.arrays[name1][2] += 1
    if name2 in state.basic_state.arrays:
        state.basic_state.arrays[name2][2] += 1

def erase_array(name):
    """ Remove an array from memory. """
    try:
        del state.basic_state.arrays[name]
    except KeyError:
        # illegal fn call
        raise error.RunError(error.IFC)

def index_array(index, dimensions):
    """ Return the flat index for a given dimensioned index. """
    bigindex = 0
    area = 1
    for i in range(len(index)):
        # WARNING: dimensions is the *maximum index number*, regardless of state.basic_state.array_base!
        bigindex += area*(index[i]-state.basic_state.array_base)
        area *= (dimensions[i]+1-state.basic_state.array_base)
    return bigindex

def array_len(dimensions):
    """ Return the flat length for given dimensioned size. """
    return index_array(dimensions, dimensions) + 1

def var_size_bytes(name):
    """ Return the size of a variable, if it exists. Raise ILLEGAL FUNCTION CALL otherwise. """
    try:
        return byte_size[name[-1]]
    except KeyError:
        raise error.RunError(error.IFC)

def array_size_bytes(name):
    """ Return the byte size of an array, if it exists. Return 0 otherwise. """
    try:
        dimensions, _, _ = state.basic_state.arrays[name]
    except KeyError:
        return 0
    return array_len(dimensions) * var_size_bytes(name)

def dim_array(name, dimensions):
    """ Allocate array space for an array of given dimensioned size. Raise errors if duplicate name or illegal index value. """
    if state.basic_state.array_base is None:
        state.basic_state.array_base = 0
    name = vartypes.complete_name(name)
    if name in state.basic_state.arrays:
        raise error.RunError(error.DUPLICATE_DEFINITION)
    for d in dimensions:
        if d < 0:
            raise error.RunError(error.IFC)
        elif d < state.basic_state.array_base:
            raise error.RunError(error.SUBSCRIPT_OUT_OF_RANGE)
    size = array_len(dimensions)
    try:
        state.basic_state.arrays[name] = [ dimensions, bytearray(size*var_size_bytes(name)), 0 ]
    except OverflowError:
        # out of memory
        raise error.RunError(error.OUT_OF_MEMORY)
    except MemoryError:
        # out of memory
        raise error.RunError(error.OUT_OF_MEMORY)
    # update memory model
    # first two bytes: chars of name or 0 if name is one byte long
    name_ptr = state.basic_state.array_current
    record_len = 1 + max(3, len(name)) + 3 + 2*len(dimensions)
    array_ptr = name_ptr + record_len
    state.basic_state.array_current += record_len + array_size_bytes(name)
    state.basic_state.array_memory[name] = (name_ptr, array_ptr)

def check_dim_array(name, index):
    """ Check if an array has been allocated. If not, auto-allocate if indices are <= 10; raise error otherwise. """
    try:
        [dimensions, lst, _] = state.basic_state.arrays[name]
    except KeyError:
        # auto-dimension - 0..10 or 1..10
        # this even fixes the dimensions if the index turns out to be out of range!
        dimensions = [ 10 ] * len(index)
        dim_array(name, dimensions)
        [dimensions, lst, _] = state.basic_state.arrays[name]
    if len(index) != len(dimensions):
        raise error.RunError(error.SUBSCRIPT_OUT_OF_RANGE)
    for i in range(len(index)):
        if index[i] < 0:
            raise error.RunError(error.IFC)
        elif index[i] < state.basic_state.array_base or index[i] > dimensions[i]:
            # WARNING: dimensions is the *maximum index number*, regardless of state.basic_state.array_base!
            raise error.RunError(error.SUBSCRIPT_OUT_OF_RANGE)
    return [dimensions, lst]

def base_array(base):
    """ Set the array base to 0 or 1 (OPTION BASE). Raise error if already set. """
    if base not in (1, 0):
        # syntax error
        raise error.RunError(error.STX)
    if state.basic_state.array_base is not None and base != state.basic_state.array_base:
        # duplicate definition
        raise error.RunError(error.DUPLICATE_DEFINITION)
    state.basic_state.array_base = base

def get_array(name, index):
    """ Retrieve the value of an array element. """
    [dimensions, lst] = check_dim_array(name, index)
    bigindex = index_array(index, dimensions)
    value = lst[bigindex*var_size_bytes(name):(bigindex+1)*var_size_bytes(name)]
    if name[-1] == '$':
        return get_string_copy_packed(value)
    return (name[-1], value)

def set_array(name, index, value):
    """ Assign a value to an array element. """
    [dimensions, lst] = check_dim_array(name, index)
    bigindex = index_array(index, dimensions)
    # make a copy of the value, we don't want them to be linked
    value = (vartypes.pass_type_keep(name[-1], value)[1])[:]
    # for strings, store the string in string space and store the key in the array
    if name[-1] == '$':
        value = state.basic_state.strings.store(bytearray(value))
    bytesize = var_size_bytes(name)
    lst[bigindex*bytesize:(bigindex+1)*bytesize] = value
    # inc version
    state.basic_state.arrays[name][2] += 1

def get_var_or_array(name, indices):
    """ Retrieve the value of a variable or an array element. """
    if indices == []:
        return get_var(name)
    else:
        return get_array(name, indices)

def set_var_or_array(name, indices, value):
    """ Assign a value to a variable or an array element. """
    if indices == []:
        set_var(name, value)
    else:
        set_array(name, indices, value)

def set_field_var_or_array(random_file, varname, indices, offset, length):
    """ Attach a string variable to a FIELD buffer. """
    if varname[-1] != '$':
        # type mismatch
        raise error.RunError(error.TYPE_MISMATCH)
    if offset+length > len(random_file.field.buffer):
        # FIELD overflow
        raise error.RunError(error.FIELD_OVERFLOW)
    str_addr = random_file.field.address + offset
    str_sequence = bytearray(chr(length)) + vartypes.value_to_uint(str_addr)
    # assign the string ptr to the variable name
    # desired side effect: if we re-assign this string variable through LET, it's no longer connected to the FIELD.
    if indices == []:
        state.basic_state.variables[varname] = str_sequence
        # update memory model (see set_var)
        if varname not in state.basic_state.var_memory:
            name_ptr = state.basic_state.var_current
            var_ptr = name_ptr + max(3, len(varname)) + 1 # byte_size first_letter second_letter_or_nul remaining_length_or_nul
            state.basic_state.var_current += max(3, len(varname)) + 1 + byte_size['$']
            state.basic_state.var_memory[varname] = (name_ptr, var_ptr)
    else:
        check_dim_array(varname, indices)
        dimensions, lst, _ = state.basic_state.arrays[varname]
        bigindex = index_array(indices, dimensions)
        lst[bigindex*3:(bigindex+1)*3] = str_sequence

def get_var_or_array_string_pointer(name, indices):
    """ Retrieve the pointer value of a string or a string-array element. """
    if name[-1] != '$':
        # type mismatch
        raise error.RunError(error.TYPE_MISMATCH)
    try:
        if indices == []:
            return state.basic_state.variables[name]
        else:
            check_dim_array(name, indices)
            dimensions, lst, _ = state.basic_state.arrays[name]
            bigindex = index_array(indices, dimensions)
            return lst[bigindex*3:(bigindex+1)*3]
    except KeyError:
        return None

def assign_field_var_or_array(name, indices, value, justify_right=False):
    """ Write a packed value into a field-assigned string. """
    if value[0] != '$':
        # type mismatch
        raise error.RunError(error.TYPE_MISMATCH)
    s = vartypes.unpack_string(value)
    v = get_var_or_array_string_pointer(name, indices)
    if v is None:
        # LSET has no effect if variable does not exist
        return
    # trim and pad to size
    length = ord(v[0:1])
    s = s[:length]
    if justify_right:
        s = ' '*(length-len(s)) + s
    else:
        s += ' '*(length-len(s))
    # copy new value into existing buffer
    string_assign_unpacked_into(v, 0, length, s)

def string_assign_into(name, indices, offset, num, value):
    """ Write a packed value into a string variable or array. """
    # WARNING - need to decrement basic offset by 1 to get python offset
    if value[0] != '$':
        # type mismatch
        raise error.RunError(error.TYPE_MISMATCH)
    s = vartypes.unpack_string(value)
    v = get_var_or_array_string_pointer(name, indices)
    if v is None:
        # illegal function call
        raise error.RunError(error.IFC)
    string_assign_unpacked_into(v, offset, num, s)

def string_assign_unpacked_into(sequence, offset, num, val):
    """ Write an unpacked value into a string buffer for given 3-byte sequence. """
    # don't overwrite more of the old string than the length of the new string
    num = min(num, len(val))
    # ensure the length of val is num, cut off any extra characters
    val = val[:num]
    length = ord(sequence[0:1])
    address = vartypes.uint_to_value(sequence[-2:])
    if offset + num > length:
        num = length - offset
    if num <= 0:
        return
    if address >= memory.var_start():
        # string stored in string space
        state.basic_state.strings.retrieve(sequence)[offset:offset+num] = val
    else:
        # string stored in field buffers
        # find the file we're in
        start = address - memory.field_mem_start
        number = 1 + start // memory.field_mem_offset
        field_offset = start % memory.field_mem_offset
        try:
            state.io_state.fields[number].buffer[
                    field_offset+offset : field_offset+offset+num] = val
        except KeyError, IndexError:
            raise KeyError('Not a field string')

##########################################

def collect_garbage():
    """ Collect garbage from string space. Compactify string storage. """
    string_list = []
    # copy all strings that are actually referenced
    for name in state.basic_state.variables:
        if name[-1] == '$':
            v = state.basic_state.variables[name]
            try:
                string_list.append((v, 0,
                        state.basic_state.strings.address(v),
                        state.basic_state.strings.retrieve(v)))
            except KeyError:
                # string is not located in memory - FIELD or code
                pass
    for name in state.basic_state.arrays:
        if name[-1] == '$':
            # ignore version - we can't put and get into string arrays
            dimensions, lst, _ = state.basic_state.arrays[name]
            for i in range(0, len(lst), 3):
                v = lst[i:i+3]
                try:
                    string_list.append((lst, i,
                            state.basic_state.strings.address(v),
                            state.basic_state.strings.retrieve(v)))
                except KeyError:
                    # string is not located in memory - FIELD or code
                    pass
    # sort by str_ptr, largest first (maintain order of storage)
    string_list.sort(key=itemgetter(2), reverse=True)
    # clear the string buffer and re-store all referenced strings
    state.basic_state.strings.clear()
    for item in string_list:
        # re-allocate string space; no need to copy buffer
        item[0][item[1]:item[1]+3] = state.basic_state.strings.store(item[3])

def fre():
    """ Return the amount of memory available to variables, arrays, strings and code. """
    return state.basic_state.strings.current - state.basic_state.var_current - state.basic_state.array_current

prepare()
