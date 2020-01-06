import os
import contextlib
import unittest
import tempfile
import shutil
try:
    from path import path
except:
    from path import Path as path
import latex2dnd as l2dndmod
from latex2dnd.main import LatexToDragDrop
from io import StringIO

@contextlib.contextmanager
def make_temp_directory():
    temp_dir = tempfile.mkdtemp('l2dndtmp')
    yield temp_dir
    shutil.rmtree(temp_dir)

class TestGravityWithErrors(unittest.TestCase):

    def test_gravity_with_sample_errors(self):
        testdir = path(l2dndmod.__file__).parent / 'testtex'  
        fn = testdir / 'gravity_bad1.tex'
        print("="*70)
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)

            err = None
            try:
                l2dnd = LatexToDragDrop(nfn, verbose=True)
            except Exception as err:
                print("Error = %s" % str(err))
                self.assertTrue('DDformula test [1] ERROR!' in str(err))

    def test_gravity_with_formula_errors(self):
        testdir = path(l2dndmod.__file__).parent / 'testtex'  
        fn = testdir / 'gravity_bad2.tex'
        print("="*70)
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)

            err = None
            try:
                l2dnd = LatexToDragDrop(nfn, verbose=True)
            except Exception as err:
                print("Error = %s" % str(err))
                self.assertTrue('DDformula test [1] ERROR!' in str(err))

    def test_gravity_with_expected_answer_error(self):
        testdir = path(l2dndmod.__file__).parent / 'testtex'  
        fn = testdir / 'gravity_bad3.tex'
        print("="*70)
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)

            err = None
            try:
                l2dnd = LatexToDragDrop(nfn, verbose=True)
            except Exception as err:
                print("Error = %s" % str(err))
                self.assertTrue('DDformula test [1] ERROR!' in str(err))

if __name__ == '__main__':
    unittest.main()
