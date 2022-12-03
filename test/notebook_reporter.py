"""TestReporter for use in notbooks"""

from IPython.display import display
from tester import TestReporter

class NotebookTestReporter(TestReporter):
    """Test reporter for notebook tests"""

    def success(self, name: str, _: any):
        """Handle test success"""
        style = 'color:green'
        display(
            {"text/html": f"<span style='{style}'>✅: {name}</span>"}, raw=True)

    def failure(self, name: str, _: any):
        """Handle test failure"""
        style = 'color:red'
        display(
            {"text/html": f"<span style='{style}'>❌: {name}</span>"}, raw=True)

    def error(self, name: str, result: any):
        """Handle errors while testing"""
        style = 'color:blue; background-color: rgb(255,242,242)'
        display(
            {"text/html":
            f"<span style='{style}'>❌❌❌: {name} {result}</span>"},
            raw=True)
