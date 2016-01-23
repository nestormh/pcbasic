__author__ = 'nestor'

import state
import var
import vartypes
import error
import fp
import itertools
import numpy as np

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

    def get_gwbasic_vars(self, dictionary):
        """ Read local variables """

        # Single variables
        for v in state.basic_state.variables:
            v_val = self.type_converter(var.get_var(v))
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
            dictionary[v] = values

    def start_script(self, file):
        variables_dictionary = dict([])
        self.get_gwbasic_vars(variables_dictionary)

        print variables_dictionary

        print dir()
        execfile("/home/nestor/Dropbox/brewer/script_test.py", variables_dictionary)
        print dir()
        print variables_dictionary.keys()