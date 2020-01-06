import string
import random
from math import *
from calc import evaluator
import json

def is_formula_equal(expected, given, samples, cs=True, tolerance=0.01):
    try:
        variables = samples.split('@')[0].split(',')
        sranges = list(zip(*[list(map(float, x.split(","))) for x in samples.split('@')[1].split('#')[0].split(':')]))
        ranges = dict(list(zip(variables, sranges)))
    except Exception as err:
        raise Exception("is_formula_eq: failed to evaluate samples expression '%s', err=%s" % (samples, str(err)))
    try:
        numsamples = int(samples.split('@')[1].split('#')[1])
    except Exception as err:
        raise Exception("is_formula_eq: failed to evaluate samples expression '%s', bad specification of number of samples, err=%s" % (samples, str(err)))
    if not len(variables)==len(sranges):
        raise Exception("is_formula_eq: bad samples expression '%s', # variables = %s, but # ranges = %s" % (samples, len(variables), len(sranges)))

    for i in range(numsamples):
        vvariables = {}
        for var in ranges:
            value = random.uniform(*ranges[var])
            vvariables[str(var)] = value
        try:
            instructor_result = evaluator(vvariables, dict(), expected, case_sensitive=cs)
        except Exception as err:
            raise Exception("is_formula_eq: failed to evaluate expected instructor result, formula='%s', vvariables=%s, err=%s" % (expected, vvariables, str(err)))
        try:
            student_result = evaluator(vvariables, dict(), given, case_sensitive=cs)
        except Exception as err:
            raise Exception("is_formula_eq: failed to evaluate student result entry, formula='%s', vvariables=%s, err=%s" % (given, vvariables, str(err)))
        if abs(instructor_result-student_result) > tolerance:
            return False
    return True
    
def dnd_check_formula(expect, ans, draggable_map, target_formula, samples, options=None):

    # construct symbolic expression from drag-and-drop result, given
    # targets in numerator and denominator
    # 
    # draggable_map maps from draggable_id to math symbol
    # target_formula is a format string which places target_id into a formula
    # samples = sample string for numerical checking
    #
    # the code in this procedure should be independent of a specific DND problem.

    anslist = json.loads(ans)
    if options is None:
        options = {}

    target_syms = {}
    for dnddict in anslist:
        # each dnddict is {draggable_id : target_id}
        (did, tid) = list(dnddict.items())[0]
        try:
            # turn target id's which are numbers into _number (so that format strings work)
            tidnum = int(tid)
            tid = '_' + tid
        except:
            pass
        target_syms[tid] = draggable_map[did]

    if options.get('allow_empty', False):
        # dict which defaults to "1" if key missing
        # allows empty factors in formula to be treated as the multiplicative identity
        class SD(dict):
            def __missing__(self, key):
                return '1'
        tsdict = SD()
        tsdict.update(target_syms)
        expr = string.Formatter().vformat(target_formula, (), tsdict)
    else:
        try:
            expr = target_formula.format(**target_syms)
        except Exception as err:
            msg = "<br/>Sorry, your input is incomplete "
            return {'ok': False, 'msg': msg}

    if options.get('hide_formula_input', False):
        msg = ''
    else:
        msg = 'You have input the expression: %s' % expr
    ok = False
    try:
        ok = is_formula_equal(expect, expr, samples)
    except Exception as err:
        msg += "<br/>error %s" % str(err).replace('>','&gt;')

    if not ok:
        msg += '<br/><font color="red">%s</font>' % options.get('err_msg', '')

    # ret = {'ok': False, 'msg': 'ans=%s' % ans}
    ret = {'ok': ok, 'msg': msg}
    return ret

def CHECK_FUNCTION(expect, ans, dcf=dnd_check_formula):
    dmap = CHECK_DMAP
    formula = CHECK_FORMULA
    samples = CHECK_SAMPLES
    expect = CHECK_EXPECT
    options = {'allow_empty': OPTION_ALLOW_EMPTY,
               'err_msg': CHECK_ERROR_MSG,
               'hide_formula_input': OPTION_HIDE_FORMULA_INPUT,
    }

    # call dnd_check_formula to do mapping from dnd to formual and to test expression
    return dcf(expect, ans, dmap, formula, samples, options)

# keep note of check function for other hinting code
dnd_check_function = CHECK_FUNCTION


