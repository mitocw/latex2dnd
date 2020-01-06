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
    def __init__(self, check_code, box_answers, unit_tests):
        '''
        check_code = string with python script code for customresponse
        box_answers = expected correct answer dict with keys = target_id, values = draggable_id
        unit_tests = list of dicts with etype (expected answer type) and target_assignments for tests

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
        for ut in unit_tests:
            ut['expected_ans'] = self.make_expected_ans(ut['target_assignments'])
        self.unit_tests = [{'etype': 'correct', 'expected_ans': self.make_expected_ans(box_answers) }]
        self.unit_tests += unit_tests

    def make_expected_ans(self, target_assignments):
        return [ {draggable_id: target_id} for target_id, draggable_id in list(target_assignments.items()) ]

    def run_tests(self):
        cnt = 0
        print("---------- Running %d DD formula unit tests ----------" % len(self.unit_tests))
        self.test_results = []
        for ut in self.unit_tests:
            cnt += 1
            ret = self.test_answer(ut['etype'], ut['expected_ans'])
            self.test_results.append(ret)
            if ret['test_ok']:
                print("DDformula test [%d] OK" % cnt)
            else:
                msg = "DDformula test [%d] ERROR! FAILURE on %s" % (cnt, ut)
                print(msg)
                raise Exception(msg)
        return self.test_results

    def test_answer(self, etype, expected_ans):
        '''
        etype = correct or incorrect
        expected_ans = list of {draggable_id: target_id} dicts
        '''
        assert etype=="correct" or etype=="incorrect"
        ret = None
        try:
            ret = self.mod.dnd_check_function(None, json.dumps(expected_ans))
        except Exception as err:
            print("ERROR in testing dnd check function: %s" % str(err))
            print("etype=%s" % etype)
            print("expected_ans=%s" % expected_ans)
            raise Exception("DDformula failure on %s" % json.dumps(expected_ans))
        ret['test_etype'] = etype
        ret['test_expected_ans'] = expected_ans
        ret['test_ok'] = True
        if etype=="correct" and not ret['ok']:
            sys.stderr.write("ERROR in DND formula unit test:\n")
            sys.stderr.write("    Expected %s to be CORRECT, but instead ret=%s\n" % (expected_ans, ret))
            ret['test_ok'] = False
        if etype=="incorrect" and ret['ok']:
            sys.stderr.write("ERROR in DND formula unit test:\n")
            sys.stderr.write("    Expected %s to be INCORRECT, but instead ret=%s\n" % (expected_ans, ret))
            ret['test_ok'] = False
        return ret

    
