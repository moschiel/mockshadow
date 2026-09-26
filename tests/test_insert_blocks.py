import tempfile
import unittest
from pathlib import Path
from mock_utils import insert_mock_top_or_bottom


class InsertBlocksTest(unittest.TestCase):
    def test_bottom_is_outside_last_function_and_inside_header_guard(self):
        for suffix, source, expected in [
            ('.c', 'void f(void) {\n}', 'void f(void) {\n}\n'),
            ('.c', '', ''),
            ('.h', '#ifndef F_H\n#define F_H\nint f(void);\n#endif\n',
             '#ifndef F_H\n#define F_H\nint f(void);\n'),
            ('.h', '#pragma once\nint f(void);', '#pragma once\nint f(void);\n'),
        ]:
            with self.subTest(source=source), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                recipe, target = root / 'recipe', root / ('target' + suffix)
                block = '//__MOCK_BOTTOM_START\nint appended;\n//__MOCK_BOTTOM_END\n'
                recipe.write_text(block)
                target.write_text(source)
                insert_mock_top_or_bottom(str(recipe), str(target))
                tail = '#endif\n' if '#ifndef' in source else ''
                self.assertEqual(target.read_text(), expected + block + tail)
