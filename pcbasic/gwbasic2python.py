__author__ = 'nestor'

import state
import var
import vartypes
import error
import fp

class GWBasic2Python(object):
    """ TODO """

    def __init__(self):
        """ TODO """
        print "Initialized"

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
        for v in state.basic_state.variables:

            v_val = self.type_converter(var.get_var(v))

            # v_val = vartypes.pass_int_unpack(v_val)
            print v, "=", v_val, "=>", type(v_val)

            dictionary[v] = v_val

            # http://stackoverflow.com/questions/8028708/dynamically-set-local-variable-in-python

        # for v in state.basic_state.arrays:
        #
        #     print v
        #
        #     v_val = var.get_var_or_array(v, [])
        #
        #     # v_val = vartypes.pass_int_unpack(v_val)
        #     print v, "=", v_val
        #     print v_val[0]
        #     array = v_val[1]


            # v_val = vartypes.pass_type_keep(v[-1], var.get_var(v))
            # print v, "=", v_val

            # TODO: Hacer generico para cualquier tipo de datos (string)
            # TODO: Capturar error de sintaxis

    def start_script(self, file):
        variables_dictionary = dict([])
        self.get_gwbasic_vars(variables_dictionary)

        print variables_dictionary

        print dir()
        execfile("/home/nestor/Dropbox/brewer/script_test.py", variables_dictionary)
        print dir()
        print variables_dictionary.keys()