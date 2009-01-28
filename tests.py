import operator
import optparse
import unittest
import sys

from cli import Parameter, ParameterError
from cli import EnvironParameterHandler

class TestFailed(Exception):
    pass

class BaseTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

def run_suite(suite):
    """Stolen from Python/Lib/test/test_support."""
    runner = unittest.TextTestRunner(sys.stdout, verbosity=2)

    result = runner.run(suite)
    if not result.wasSuccessful():
        if len(result.errors) == 1 and not result.failures:
            err = result.errors[0][1]
        elif len(result.failures) == 1 and not result.errors:
            err = result.failures[0][1]
        else:
            err = "errors occurred; run in verbose mode for details"
        raise TestFailed(err)

def run_unittest(*classes):
    """Stolen from Python/Lib/test/test_support."""
    valid_types = (unittest.TestSuite, unittest.TestCase)
    suite = unittest.TestSuite()
    for cls in classes:
        if isinstance(cls, str):
            if cls in sys.modules:
                suite.addTest(unittest.findTestCases(sys.modules[cls]))
            else:
                raise ValueError("str arguments must be keys in sys.modules")
        elif isinstance(cls, valid_types):
            suite.addTest(cls)
        else:
            suite.addTest(unittest.makeSuite(cls))
    run_suite(suite)

class ParameterTests(BaseTest):

    def setUp(self):
        self.params = Parameter("root")

    def test_attributes(self):
        self.assertEqual(self.params.name, "root")

    def test_add(self):
        bar = Parameter("bar")
        self.params.add(bar)

        self.assertEqual(self.params.bar, bar)
        self.assertEqual(len(self.params.children), 1)

        self.params.add("baz")
        self.assertTrue("baz" in [x.name for x in self.params.children])

        # Test re-writing existing children.
        self.params.add(bar)
        self.assertEquals(bar, self.params.bar)

    def test_remove(self):
        eggs = Parameter("eggs")
        self.params.add(eggs)
        self.params.add("bacon")

        self.assertEqual(len(self.params.children), 2)

        self.params.remove(eggs)
        self.assertEqual(len(self.params.children), 1)
        self.assertRaises(AttributeError,
                operator.attrgetter("eggs"), self.params)
        self.assertFalse("eggs" in [x.name for x in self.params.children])

        self.params.remove("bacon")
        self.assertEqual(len(self.params.children), 0)
        self.assertRaises(AttributeError,
                operator.attrgetter("bacon"), self.params)
        self.assertFalse("eggs" in [x.name for x in self.params.children])

    def test_tree(self):
        self.params.add("bar")
        self.assertEqual(len(self.params.children), 1)

        spam = Parameter("spam")
        self.params.bar.add(spam)
        self.assertEqual(self.params.bar.spam, spam)

        self.assertEqual(str(self.params.bar.path), "bar")
        self.assertEqual(str(self.params.bar.spam.path), "bar.spam")

    def test_attributes(self):
        self.assertFalse(isinstance(getattr(self.params, "keys"), Parameter))

        keys_parameter = Parameter("keys")
        self.params.add(keys_parameter)
        self.assertFalse(isinstance(getattr(self.params, "keys"), Parameter))
        self.assertTrue(self.params["keys"] is keys_parameter)

    def test_value(self):
        self.params.add("test")
        self.params.test.value = "foo"

        self.assertEqual(self.params.test.value, "foo")

        self.params.test.value = 0
        self.assertEqual(self.params.test.value, "0")

        self.params.add("bar", default=0, coerce=int)
        self.assertEqual(self.params.bar.value, 0)
        
        self.params.bar.value = 10
        self.assertEqual(self.params.bar.value, 10)

        self.params.bar.value = "ten"
        self.assertRaises(ValueError, getattr, self.params.bar, "value")

class EnvironParameterHandlerTests(BaseTest):
    environ = {
            'TEST_TEST_TEST': 'foo'}

    def setUp(self):
        self.params = Parameter("root")
        self.params.add("test")
        self.params.test.add("test")
        self.params.test.test.add("test")

    def test_foo(self):
        handler = EnvironParameterHandler(self.environ)
        handler.handle(self.params)

        self.assertEqual(self.params.test.test.test.value,
                self.environ['TEST_TEST_TEST'])

def run_tests(app, *args, **kwargs):
    """[options]

    Run unit tests.
    """
    run_unittest(__name__)

if __name__ == "__main__":
    run_unittest(__name__)
    #from cli import App
    #app = App(run_tests)
    #app.run()
