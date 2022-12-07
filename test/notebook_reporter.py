"""TestReporter for use in notbooks"""

from itertools import zip_longest
from IPython.display import display
from tester import TestReporter

class NotebookTestReporter(TestReporter):
    """Test reporter for notebook tests"""
    results: dict[str,tuple] = dict()
    successes: int = 0
    failures: int = 0
    errors: int = 0

    def _display(self, type: int, style: str, token: str, name: str, msg: str) -> int:
        """Returns how many to add to the count of each kind of result (0 or 1)."""
        html = f"<span style='{style}'>{token} {name}: {msg}</span>"
        s_count, f_count, e_count = (0, 0, 0)
        if name in self.results:
            (old_type, old_heml) = self.results[name]
            if old_type == 0:
                s_count = -1
            elif old_type == 1:
                f_count = -1
            elif old_type == 2:
                e_count = -1
        if type == 0:
            s_count += 1
        elif type == 1:
            f_count += 1
        elif type == 2:
            e_count += 1
        self.results[name] = (type, name, html)
        display({"text/html": html}, raw=True)
        return (s_count, f_count, e_count)

    def update_count(self, s, f, e):
        self.successes += s
        self.failures += f
        self.errors += e

    def success(self, name: str, _: any):
        """Handle test success"""
        self.update_count(*self._display(0, "color:green", '✅', name, 'OK'))

    def failure(self, name: str, _: any):
        """Handle test failure"""
        self.update_count(*self._display(1, 'color:red', '❌', name, 'Failed'))

    def error(self, name: str, result: any):
        """Handle errors while testing"""
        self.update_count(*self._display(
            2,
            'color:blue; background-color: rgb(255,242,242)',
            '❌❌❌',
            name,
            str(result)
        ))

    def report(self, /, columns=3):
        results = list(self.results.values())
        def mkrow(p)-> str:
            def cell(content):
                _, name, text = content
                return f"<td style='text-align:left'>{text}</td>"
            return f"<tr>{''.join(map(cell, p))}</tr>"
        rows = "\n".join(map(mkrow, zip_longest(*[iter(results)]*columns, fillvalue=(None, None, '—'))))
        table = f"<table>{rows}</table>"
        summary = f"{self.successes} successes, {self.failures} failures, {self.errors} errors"
        display({'text/html': f"{table}<br>{summary}"}, raw=True)
