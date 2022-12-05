"""TestReporter for use in notbooks"""

from IPython.display import display
from tester import TestReporter

class NotebookTestReporter(TestReporter):
    """Test reporter for notebook tests"""
    results: dict[str,tuple] = dict()
    successes: int = 0
    failures: int = 0
    errors: int = 0

    def display(self, style: str, token: str, name: str, msg: str) -> int:
        """Returns how many to add to the count of this kind of result (0 or 1)."""
        html = f"<span style='{style}'>{token} {name}: {msg}</span>"
        count = 1 if not name in self.results else 0
        self.results[name] = html
        display({"text/html": html}, raw=True)
        return count

    def success(self, name: str, _: any):
        """Handle test success"""
        self.successes += self.display("color:green", '✅', name, 'OK')

    def failure(self, name: str, _: any):
        """Handle test failure"""
        self.failures += self.display('color:red', '❌', name, 'Failed')

    def error(self, name: str, result: any):
        """Handle errors while testing"""
        self.errors += self.display(
            'color:blue; background-color: rgb(255,242,242)',
            '❌❌❌',
            name,
            str(result)
        )

    def report(self):
        listing = "<br>".join(self.results.values())
        summary = f"{self.successes} successes, {self.failures} failures, {self.errors} errors"
        display({'text/html': f"{listing}<br>{summary}"}, raw=True)
