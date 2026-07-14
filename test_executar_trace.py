import tempfile
import unittest
from pathlib import Path

from executar_trace import execute_trace


class TraceExecutionTests(unittest.TestCase):
    def test_execute_trace_writes_only_search_answers(self) -> None:
        trace = """\
# universe=100 mix=35:30:35 theta=0.6 seed=16
I 20
I 10
S 20
D 20
S 20
I 30
S 25
D 999
S 30
"""
        expected = """\
20 FOUND
20 NOT_FOUND
25 NOT_FOUND
30 FOUND
"""

        with tempfile.TemporaryDirectory() as directory:
            trace_path = Path(directory) / "sample.trace"
            output_path = Path(directory) / "sample.out"
            trace_path.write_text(trace, encoding="utf-8")

            root, counts = execute_trace(
                trace_path,
                output_path,
                validate_every=1,
            )

            self.assertEqual(output_path.read_text(encoding="utf-8"), expected)
            self.assertEqual(counts, {"I": 3, "D": 2, "S": 4})
            self.assertEqual(root.size, 2)
            self.assertEqual(root.subtree_sum, 40)


if __name__ == "__main__":
    unittest.main()
