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

class TestCustomCFN(unittest.TestCase):

    def test_custom_cfn1(self):
        testdir = path(l2dndmod.__file__).parent / 'testtex'  
        fn = testdir / 'gravity_cfn.tex'
        print("="*70)
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2dnd = LatexToDragDrop(nfn, verbose=True)

            pre = nfn[:-4]
            auxfn = pre + ".aux"
            self.assertTrue(os.path.exists(auxfn))

            xfn = path(tmdir) / 'gravity_cfn_dnd.xml'
            xml = open(xfn).read()
            self.assertIn('<customresponse cfn="mytest">', xml)

    def test_custom_cfn2(self):
        testdir = path(l2dndmod.__file__).parent / 'testtex'  
        fn = testdir / 'gravity_cfn.tex'
        print("="*70)
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            l2dnd = LatexToDragDrop(nfn, verbose=True, custom_cfn='testcfn')

            pre = nfn[:-4]
            auxfn = pre + ".aux"
            self.assertTrue(os.path.exists(auxfn))

            xfn = path(tmdir) / 'gravity_cfn_dnd.xml'
            xml = open(xfn).read()
            self.assertIn('<customresponse cfn="testcfn">', xml)

if __name__ == '__main__':
    unittest.main()
