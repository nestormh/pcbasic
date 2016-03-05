__author__ = 'nestor'

import state
import var
import vartypes
import error
import fp
import itertools
import numpy as np
import logging
import util

import cStringIO

class GWBasic2Python(object):
    """ TODO """

    def __init__(self):
        """ TODO """

    def type_converter(self, v_val):
        if (v_val[0] == '%'):
            return vartypes.pass_int_unpack(v_val)
        elif (v_val[0] == '!'):
            return fp.Single.from_bytes(v_val[1]).to_value()
        elif (v_val[0] == '#'):
            return fp.Double.from_bytes(v_val[1]).to_value()
        elif (v_val[0] == '$'):
            return str(vartypes.pass_string_unpack(v_val))
        else:
            raise error.RunError(error.TYPE_MISMATCH)

    def name_converter(self, v):
        if (v[-1] == '%'):
            return v[:-1] + "_INT"
        elif (v[-1] == '!'):
            return v[:-1] + "_SNG"
        elif (v[-1] == '#'):
            return v[:-1] + "_DBL"
        elif (v[-1] == '$'):
            return v[:-1] + "_STR"
        else:
            return v + "_NUM"

    def name_recover(self, var_name):
        if (var_name[-4:].upper() == "_INT"):
            return var_name[:-4] + "%"
        elif (var_name[-4:].upper() == "_SNG"):
            return var_name[:-4] + "!"
        elif (var_name[-4:].upper() == "_DBL"):
            return var_name[:-4] + "#"
        elif (var_name[-4:].upper() == "_STR"):
            return var_name[:-4] + "$"
        else:
            return None         # These variables are not supposed to be exported

    def get_gwbasic_vars(self, dictionary):
        """ Read local variables """

        # Single variables
        for v in state.basic_state.variables:
            v_val = self.type_converter(var.get_var(v))
            v = self.name_converter(v)
            dictionary[v] = v_val

        # Arrays
        for v in state.basic_state.arrays:
            v_val = state.basic_state.arrays[v]

            dimensions = v_val[0]

            indexes = [list(xrange(d)) for d in dimensions]
            indexes = list(itertools.product(*indexes))

            values = np.empty(dimensions)
            for index in indexes:
                values[index] = self.type_converter(var.get_array(v, list(index)))

            values = values.tolist()
            v = self.name_converter(v)
            dictionary[v] = values

    def set_gwbasic_vars(self, dictionary):
        """ Retrieve variables from Python script """

        # var_names_list = state.basic_state.variables.keys() + state.basic_state.arrays.keys()
        for new_var_name, new_var_value in dictionary.iteritems():
            var_name = self.name_recover(new_var_name)

            if type(new_var_value) == str:
                if var_name[-1] != '$':
                    raise Exception("Type mismatch. Variable name is %s, but a string value was received (%s)" %
                                    (new_var_name , new_var_value))

                ins = cStringIO.StringIO(var_name)
                var_name = util.get_var_name(ins)
                var.set_var(var_name, vartypes.pack_string(bytearray(new_var_value + "\0")))
            elif type(new_var_value) == int:
                if var_name[-1] != '%':
                    raise Exception("Type mismatch. Variable name is %s, but a integer value was received (%d)" %
                                    (new_var_name , new_var_value))

                ins = cStringIO.StringIO(var_name)
                var_name = util.get_var_name(ins)
                var.set_var(var_name, vartypes.pack_int(new_var_value))
            elif type(new_var_value) == float:
                if var_name[-1] == '!':
                    ins = cStringIO.StringIO(var_name)
                    var_name = util.get_var_name(ins)
                    bytearray_val = fp.Single.from_value(new_var_value).to_bytes()
                    var.set_var(var_name, ('!', bytearray_val))
                elif var_name[-1] == '#':
                    ins = cStringIO.StringIO(var_name)
                    var_name = util.get_var_name(ins)
                    bytearray_val = fp.Double.from_value(new_var_value).to_bytes()
                    var.set_var(var_name, ('#', bytearray_val))
                else:
                    raise Exception("Type mismatch. Variable name is %s, but a floating-point value was received (%f)" %
                                    (new_var_name , new_var_value))
            elif type(new_var_value) == list:
                print var_name, "LST"
                print new_var_value
                #
                # print len(new_var_value)

                matrix = np.array(new_var_value)

                print matrix
                print type(matrix)
                dimensions = matrix.shape

                var.erase_array(var_name)
                var.dim_array(var_name, dimensions)

                indexes = [list(xrange(d)) for d in dimensions]
                indexes = list(itertools.product(*indexes))

                # name <type 'str'> ARRINT3%
                # index <type 'list'> [0, 0]
                # value <type 'tuple'> ('!', bytearray(b'\x00\x00\x00\x00'))

                for index in indexes:
                    var.set_array(var_name, index, ('!', bytearray(b'\x11\x11\x11\x11')))

            else:
                logging.warning('Received variable was not processed: %s.', new_var_name)

        # for v, val in state.basic_state.variables.iteritems():
        #     hex_string = "".join("%02x" % b for b in val)
        #     print v, type(val), hex_string





    def start_script(self, file):
        variables_dictionary = dict([])
        self.get_gwbasic_vars(variables_dictionary)

        print variables_dictionary

        print dir()
        execfile("C:\\brewer\\brewer\\script_test.py", variables_dictionary)

        self.set_gwbasic_vars(variables_dictionary)