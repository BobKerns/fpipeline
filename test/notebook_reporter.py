"""TestReporter for use in notbooks"""

from IPython.display import display
from tester import TestReporter

class NotebookTestReporter(TestReporter):
    """Test reporter for notebook tests"""
    results: dict[str,tuple] = dict()
    successes: int = 0
    failures: int = 0
    errors: int = 0

    def display(self, style: str, token: str, name: str, msg: str):
        html = f"<span style='{style}'>{token} {name}: {msg}</span>"
        self.results[name] = html
        display({"text/html": html}, raw=True)

    def success(self, name: str, _: any):
        """Handle test success"""
        self.successes += 1
        self.display("color:green", '✅', name, 'OK')

    def failure(self, name: str, _: any):
        """Handle test failure"""
        self.failures += 1
        self.display('color:red', '❌', name, 'Failed')

    def error(self, name: str, result: any):
        """Handle errors while testing"""
        self.errors += 1
        self.display(
            'color:blue; background-color: rgb(255,242,242)'
            '❌❌❌',
            name,
            str(result)
        )

    def report(self):
        listing = "<br>".join(self.results.values())
        summary = f"{self.successes} successes, {self.failures} failures, {self.errors} errors"
        display({'text/html': f"{listing}<br>{summary}"}, raw=True)
