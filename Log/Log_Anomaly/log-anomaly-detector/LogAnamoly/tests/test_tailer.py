import tempfile
import unittest
from pathlib import Path

from log_ingestion.tailer import LogTailer


class LogTailerTests(unittest.TestCase):
    def test_reads_only_newly_appended_content_and_remembers_offset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.log"
            path.write_text("A\nB\nC\n", encoding="utf-8")
            tailer = LogTailer(path)
            try:
                self.assertEqual(tailer.read_available(), ["A", "B", "C"])
                first_offset = tailer.offset
                self.assertEqual(tailer.read_available(), [])
                self.assertEqual(tailer.offset, first_offset)

                with path.open("a", encoding="utf-8", newline="\n") as output:
                    output.write("D\nE\n")
                self.assertEqual(tailer.read_available(), ["D", "E"])
                self.assertEqual(tailer.read_available(), [])
            finally:
                tailer.close()

    def test_handles_empty_file_and_later_appends(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.log"
            path.touch()
            tailer = LogTailer(path)
            try:
                self.assertEqual(tailer.read_available(), [])
                with path.open("a", encoding="utf-8") as output:
                    output.write("later\n")
                self.assertEqual(tailer.read_available(), ["later"])
            finally:
                tailer.close()

    def test_waits_for_a_complete_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.log"
            tailer = LogTailer(path)
            try:
                self.assertEqual(tailer.read_available(), [])
                with path.open("a", encoding="utf-8") as output:
                    output.write("partial")
                self.assertEqual(tailer.read_available(), [])
                with path.open("a", encoding="utf-8") as output:
                    output.write(" line\nnext\n")
                self.assertEqual(tailer.read_available(), ["partial line", "next"])
            finally:
                tailer.close()

    def test_replacement_rotation_starts_at_new_file_beginning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app.log"
            replacement = Path(directory) / "replacement.log"
            path.write_text("old\n", encoding="utf-8")
            tailer = LogTailer(path)
            try:
                self.assertEqual(tailer.read_available(), ["old"])
                replacement.write_text("new\n", encoding="utf-8")
                replacement.replace(path)
                self.assertEqual(tailer.read_available(), ["new"])
            finally:
                tailer.close()


if __name__ == "__main__":
    unittest.main()