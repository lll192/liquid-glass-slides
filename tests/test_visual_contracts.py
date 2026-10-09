import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'assets' / 'engine.css').read_text(encoding='utf-8')
JS = (ROOT / 'assets' / 'engine.js').read_text(encoding='utf-8')


class VisualContractTests(unittest.TestCase):
    def test_data_table_has_alternating_rows(self):
        self.assertIn('.data-table tbody tr:nth-child(odd) > *', CSS)
        self.assertIn('.data-table tbody tr:nth-child(even) > *', CSS)

    def test_vs_tracks_the_actual_column_divider(self):
        self.assertIn('--compare-divider:58.333%', CSS)
        self.assertIn('--compare-divider:41.667%', CSS)
        self.assertIn('left:var(--compare-divider); top:50%', CSS)

    def test_closing_alignment_overrides_editorial_title_width(self):
        editorial_rule = '.typography-editorial .slide.title-size-long h1'
        closing_rule = '.composition-constructivist.typography-editorial .slide.closing .closing-title'
        self.assertGreater(CSS.find(closing_rule), CSS.find(editorial_rule))
        closing_block = CSS[CSS.find(closing_rule):CSS.find(closing_rule) + 220]
        self.assertIn('max-width:none', closing_block)
        self.assertIn('text-align:center', closing_block)

    def test_runtime_overflow_ignores_decorative_slide_layers(self):
        self.assertIn("const contentBox = slide.querySelector('.slide-content') || slide", JS)
        self.assertIn('contentBox.scrollWidth > contentBox.clientWidth', JS)
        self.assertIn('contentBox.scrollHeight > contentBox.clientHeight', JS)

    def test_presenter_cues_are_visible_and_discoverable(self):
        self.assertIn("notesToggle.className = 'presenter-toggle'", JS)
        self.assertIn("notesToggle.addEventListener('click'", JS)

    def test_reference_deck_builds_with_all_three_layouts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / 'deck.html'
            subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'build.py'),
                 '--outline', str(ROOT / 'examples' / 'narrative-visual-outline.json'),
                 '--out', str(output)],
                check=True,
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            html = output.read_text(encoding='utf-8')
            for layout in ('data-table', 'comparison', 'closing'):
                self.assertIn('data-layout="%s"' % layout, html)
            self.assertIn('<strong>故事角色</strong>', html)
            self.assertIn('<strong>情绪节拍</strong>', html)


if __name__ == '__main__':
    unittest.main()
