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
from latex2dnd.main import LatexToDragDrop, CommandLine
from io import StringIO

@contextlib.contextmanager
def make_temp_directory():
    temp_dir = tempfile.mkdtemp('l2dndtmp')
    yield temp_dir
    shutil.rmtree(temp_dir)

class TestDNDspec(unittest.TestCase):

    def test_dndspec_gravity(self):
        testdir = path(l2dndmod.__file__).parent / 'testtex'  
        fn = testdir / 'gravity_simple.dndspec'
        print("="*70)
        print("file %s" % fn)
        with make_temp_directory() as tmdir:
            nfn = '%s/%s' % (tmdir, fn.basename())
            os.system('cp %s/* %s' % (testdir, tmdir))
            os.chdir(tmdir)
            # l2dnd = LatexToDragDrop(nfn, verbose=True)
            l2d = CommandLine(arglist=["-v", nfn, '--nonrandom'], return_object=True)

            pre = nfn.rsplit('.', 1)[0]
            auxfn = pre + ".aux"
            print("checking %s" % auxfn)
            self.assertTrue(os.path.exists(auxfn))

            files = ['gravity_simple_dnd_label1.png', 'gravity_simple_dnd.xml', 'gravity_simple_dnd.xml', 'gravity_simple_dnd_sol.png']
            for fn in files:
                print("checking %s" % fn)
                self.assertTrue(os.path.exists(path(tmdir)/fn))

            xfn = path(tmdir) / 'gravity_simple_dnd.xml'
            xml = open(xfn).read()
            print("checking png")
            self.assertIn('<img src="/static/images/gravity_simple/gravity_simple_dnd_sol.png"/>', xml)
            print("checking samples")
            # self.assertIn("samples = 'G,m1,m2,R@1,1,1,1:20,20,20,20#20'", xml)
            # self.assertIn("samples = 'R,m_1,G,m_2@1,1,1,1:20,20,20,20#20'", xml)
            self.assertIn("samples = 'G,m_1,m_2,R@1,1,1,1:20,20,20,20#20'", xml)

if __name__ == '__main__':
    unittest.main()
