import datetime
import inspect
import os
import sys
import unittest

from timeit import default_timer

plural = lambda n: n != 1 and 's' or ''

def timer(callable, *args, **kwargs):
    """Time and run callable with args and kwargs.

    Returns a tuple (timedelta, returned), where 'timedelta' is a
    datetime.timedelta object representing the time it took to run
    the callable and 'returned' is the output from callable.
    """
    start = default_timer()
    returned = callable(*args, **kwargs)
    stop = default_timer()
    duration = datetime.timedelta(seconds=stop - start)

    return returned, duration

class AppTestCase(unittest.TestCase, object):

    @property
    def testmethod(self):
        name = getattr(self, "_testMethodName", None)
        method = getattr(self, name, None)
        return method

    @property
    def lineno(self):
        return inspect.getsourcelines(self.testmethod)[1]

    @property
    def filename(self):
        return inspect.getsourcefile(self.testmethod)

    @property
    def module(self):
        return inspect.getmodule(self.testmethod)

    @property
    def classname(self):
        im_class = getattr(self.testmethod, "im_class", None)
        if im_class is not None:
            return im_class
        else:
            return inspect.getmodulename(self.filename)

    @property
    def methodname(self):
        func = getattr(self.testmethod, "im_func", None)
        if func is None:
            func = self.testmethod

        return func.func_name

class AppTestSuite(unittest.TestSuite, object):
    pass

class AppTestLoader(unittest.TestLoader, object):
    ignore_dirs = '.'
    module_extension = ".py"
    module_prefix = "test_"
    module_suffix = "_test"
    func_prefix = "test_"
    class_prefix = "Test"
    testcase_factory = AppTestCase
    testsuite_factory = AppTestSuite

    # Unittest synonyms.
    suiteClass = testsuite_factory
    testMethodPrefix = func_prefix
    sortTestMethodsUsing = None

    def __init__(self, app):
        self.app = app

    @staticmethod
    def sort_methods(cls, x, y):
        """Sort objects based on their appearance in a source file.
        
        If they both were defined in the same file, the object which
        was defined earlier is considered "less than" the object
        which was defined later. If they were defined in different
        source files, the source filenames will be compared
        alphabetically.
        """
        args = [getattr(cls, name) for name in x, y]
        x_file, y_file = [inspect.getsourcefile(obj) for obj in args]
        if x_file == y_file:
            x, y = [inspect.getsourcelines(obj)[1] for obj in args]
        else:
            x, y = x_file, y_file
        return cmp(x, y)

    def getTestCaseNames(self, testCaseClass):
        names = unittest.TestLoader.getTestCaseNames(self, testCaseClass)
        def sorter(x, y):
            return self.sort_methods(testCaseClass, x, y)
        names.sort(sorter)

        return names

    def loadTestsFromDirectory(self, directory):
        directory = os.path.abspath(directory)
        suite = self.suiteClass()

        root = directory
        self.app.log.debug("Examining %s", root)
        for dirpath, dirnames, filenames in os.walk(root):
            # Trim directories list.
            dirnames = [x for x in dirnames \
                    if not x.startswith(self.ignore_dirs)]

            # Search for candidate files.
            candidates = [full for base, ext, full in \
                    [os.path.splitext(x) + (x,) for x in filenames] \
                    if ext == self.module_extension and \
                    base.startswith(self.module_prefix) or \
                    base.endswith(self.module_suffix)]

            for candidate in candidates:
                fullpath = os.path.join(dirpath, candidate)
                self.app.log.debug("Adding %s", fullpath)
                suite.addTests(self.loadTestsFromFile(fullpath))

        return suite

    def loadTestsFromFile(self, filename):
        name, _ = os.path.splitext(os.path.basename(filename))
        dirname = os.path.dirname(filename)
        sys.path.insert(0, dirname)
        module = __import__(name)
        return self.loadTestsFromModule(module)

    def loadTestsFromModule(self, module):
        tests = []
        class TestCase(AppTestCase):
            """To collect module-level tests."""
            # XXX: fix class naming.

        TestCase.module = module
        
        for name, obj in vars(module).items():
            if name.startswith("test_") and inspect.isfunction(obj):
                self.app.log.debug("Adding function %s", name)
                self.wrap_function(TestCase, obj)
            elif name.startswith("Test") and inspect.isclass(obj):
                self.app.log.debug("XXX: ignoring class %s for now", name)
                if issubclass(unittest.TestCase, obj):
                    #TestCase = obj
                    pass
                else:
                    #TestCase.something()
                    pass
        tests.insert(0, self.loadTestsFromTestCase(TestCase))

        return tests

    def loadTestsFromTestClass(self, obj):
        pass

    @staticmethod
    def wrap_function(testcase, function):
        name = function.func_name
        doc = function.__doc__

        setattr(testcase, name, staticmethod(function))

    @staticmethod
    def wrap_class(testcase, cls):
        noop = lambda s: None
        setup_method = getattr(cls, "setup_method", noop)
        setUp = getattr(cls, "setUp", noop)
        teardown_method = getattr(cls, "teardown_method", noop)
        tearDown = getattr(cls, "tearDown", noop)

        tests = [(n, m) for n, m in vars(cls).items() if \
                n.startswith("test_")]

        for name, method in tests:
            def wrapped_method(self):

                method()

class AppTestResult(unittest.TestResult, object):

    def __init__(self, app):
        self.app = app
        unittest.TestResult.__init__(self)

        self.start = 0
        self.stop = 0

    def status_message(self, test, status):
        time = self.time
        fields = {
                "seconds": time.seconds,
                "microseconds": time.microseconds,
                "status": status,
                "filename": test.filename,
                "lineno": test.lineno,
                "classname": test.classname,
                "methodname": test.methodname,
        }

        format = "%(seconds)d.%(microseconds)03.d %(status)5s %(filename)s:" \
                "%(lineno)-10d %(classname)s.%(methodname)s()"
        return format % fields

    @property
    def time(self):
        return datetime.timedelta(seconds=self.stop - self.start)

    def startTest(self, test):
        unittest.TestResult.startTest(self, test)
        if not hasattr(test, "...description..."):
            test.description = "DESCR"
        if not hasattr(test, "name"):
            test.name = str(test)

        self.app.log.debug("Starting %s (%s)", test.name, test.description)
        self.start = default_timer()

    def stopTest(self, test):
        unittest.TestResult.stopTest(self, test)
        self.app.log.debug("Finished %s", test.name)

    def addSuccess(self, test):
        self.stop = default_timer()
        unittest.TestResult.addSuccess(self, test)
        self.app.log.info(self.status_message(test, "ok"))

    def addFailure(self, test, err):
        self.stop = default_timer()
        unittest.TestResult.addFailure(self, test, err)
        self.app.log.warning(self.status_message(test, "fail"))

    def addError(self, test, err):
        self.stop = default_timer()
        unittest.TestResult.addFailure(self, test, err)
        self.app.log.error(self.status_message(test, "error"))

class AppTestRunner(object):
    result_factory = AppTestResult

    def __init__(self, app):
        self.app = app

    def run(self, test):
        result = self.result_factory(self.app)

        # Time and run the test.
        _, time = timer(test, result)

        tests = result.testsRun
        self.app.log.info("Ran %d test%s in %s", tests,
                plural(tests), time)

        if not result.wasSuccessful():
            failed, errored = [len(x) for x in (result.failures, result.errors)]
            self.app.log.error("%d failure%s, %d error%s", failed,
                    plural(failed), errored, plural(errored))

        return result

def test(app, *args):
    runner = AppTestRunner(app)
    suite = AppTestSuite()
    loader = AppTestLoader(app)

    directory = args and args[0] or '.'

    suite.addTests(loader.loadTestsFromDirectory(directory))
    runner.run(suite)

if __name__ == "__main__":
    from cli import App
    app = App(test)
    app.run()
