'''
Handle DDformula script testing
'''

import imp
import sys
import json

def import_from_string(codestr, name='codestr'):
    """Import a module from a specified string.
    """
    mod = imp.new_module(name)
    mod.__file__ = "codestr"
    code = compile(codestr, '.', 'exec', dont_inherit=True)
    exec(code, mod.__dict__)
    return mod

class FormulaTester(object):
    '''
    Evaluate python script for DDformula answer checking, and perform unit tests on it.
    '''
    def __init__(self, check_code, box_answers):
        '''
        check_code = string with python script code for customresponse
        box_answers = dict with keys = target_id, values = draggable_id

        Note that an draggable_id may appear with multiple target_id keys.  
        Each target_id is unique, though.
        '''
        check_code = check_code.replace('from calc import evaluator', 'from latex2dnd.calc import evaluator')
        self.code = check_code
        self.env = {}
        try:
            self.mod = import_from_string(check_code)
        except Exception as err:
            sys.stderr.write("Failed to evaluate DDformula script code!  Err=%s\n" % (str(err)))
            sys.exit(0)
        self.expected_ans = [ {draggable_id: target_id} for target_id, draggable_id in box_answers.items() ]

    def run_tests(self):
        if self.test_expected_correct():
            print "DND formula script tested: OK"
        else:
            print "ERROR!  DND formula script tested: FAILURE"

    def test_expected_correct(self):
        # expected answer should be correct
        try:
            ret = self.mod.dnd_check_function(None, json.dumps(self.expected_ans))
        except Exception as err:
            print "ERROR in testing dnd check function: %s" % str(err)
            raise
        if not ret['ok']:
            sys.stderr.write("ERROR in DND formula unit test:\n")
            sys.stderr.write("    Expected %s to be CORRECT, but instead ret=%s\n" % (self.expected_ans, ret))
            return False
        return True

    
