import os
import unittest
import tempfile
import shutil
try:
    from path import path
except:
    from path import Path as path
import latex2dnd as l2dndmod
from latex2dnd.main import LatexToDragDrop


class TestCustomCFN(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        testdir = path(l2dndmod.__file__).parent / 'testtex'
        cls._tmpdir = tempfile.mkdtemp('l2dndtmp')
        os.system('cp %s/* %s' % (testdir, cls._tmpdir))
        os.chdir(cls._tmpdir)
        cls._nfn = '%s/%s' % (cls._tmpdir, 'gravity_cfn.tex')
        # compile once; both tests reuse the compiled output
        LatexToDragDrop(cls._nfn, verbose=False, latex_passes=1)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmpdir)

    def test_custom_cfn1(self):
        l2dnd = LatexToDragDrop(self._nfn, compile=False)
        self.assertTrue(os.path.exists(self._nfn[:-4] + '.aux'))
        xml = open(path(self._tmpdir) / 'gravity_cfn_dnd.xml').read()
        self.assertIn('<customresponse cfn="mytest">', xml)

    def test_custom_cfn2(self):
        l2dnd = LatexToDragDrop(self._nfn, compile=False, custom_cfn='testcfn')
        self.assertTrue(os.path.exists(self._nfn[:-4] + '.aux'))
        xml = open(path(self._tmpdir) / 'gravity_cfn_dnd.xml').read()
        self.assertIn('<customresponse cfn="testcfn">', xml)


if __name__ == '__main__':
    unittest.main()
