import unittest
from squad_os.tools.registry import _validate_python_code

class TestPythonSecurityUpgrade(unittest.TestCase):
    def test_block_direct_eval(self):
        code = "eval('1+1')"
        valid, msg = _validate_python_code(code)
        self.assertFalse(valid)
        self.assertIn("eval", msg)

    def test_block_getattr_bypass(self):
        code = "import os\ngetattr(os, 'system')('ls')"
        valid, msg = _validate_python_code(code)
        self.assertFalse(valid)
        self.assertIn("getattr", msg)

    def test_block_os_import(self):
        code = "import os\nos.system('ls')"
        valid, msg = _validate_python_code(code)
        self.assertFalse(valid)
        self.assertIn("forbidden module 'os'", msg)

    def test_block_os_system_alias(self):
        code = "import os as dangerous\ndangerous.system('ls')"
        valid, msg = _validate_python_code(code)
        self.assertFalse(valid)
        self.assertIn("forbidden module 'os'", msg)

    def test_block_dunder_attribute(self):
        code = "obj.__subclasses__()"
        valid, msg = _validate_python_code(code)
        self.assertFalse(valid)
        self.assertIn("__subclasses__", msg)

    def test_allow_safe_code(self):
        code = "print('hello world')\nlist(range(10))"
        valid, msg = _validate_python_code(code)
        self.assertTrue(valid, msg)

    def test_block_recursive_builtins(self):
        code = "(eval)(compile('print(1)', '', 'exec'))"
        valid, msg = _validate_python_code(code)
        self.assertFalse(valid)
        # Should catch both eval and compile
        self.assertIn("eval", msg)

if __name__ == '__main__':
    unittest.main()
