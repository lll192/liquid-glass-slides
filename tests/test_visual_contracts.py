import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'assets' / 'engine.css').read_text(encoding='utf-8')
JS = (ROOT / 'assets' / 'engine.js').read_text(encoding='utf-8')
BUILD = (ROOT / 'scripts' / 'build.py').read_text(encoding='utf-8')


class VisualContractTests(unittest.TestCase):
    def test_calm_three_presets_use_swiss_flat_geometry(self):
        object_scene = BUILD[BUILD.index('function objectScene'):BUILD.index('function petalsScene')]
        orbs_scene = BUILD[BUILD.index('function orbsScene'):BUILD.index('function wavesScene')]
        for scene in (object_scene, orbs_scene):
            self.assertIn('OrthographicCamera', scene)
            self.assertIn('MeshBasicMaterial', scene)
            self.assertNotIn('MeshStandardMaterial', scene)
            self.assertNotIn('SphereGeometry', scene)
            self.assertNotIn('wireframe:true', scene)
        self.assertIn('group.position.set(7.0,0.25,0)', object_scene)
        self.assertIn('var specs=[', orbs_scene)
        self.assertNotIn('Math.random', orbs_scene)

    def test_bauhaus_motion_reference_builds_both_calm_presets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / 'motion.html'
            subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'build.py'),
                 '--outline', str(ROOT / 'examples' / 'bauhaus-motion-outline.json'),
                 '--out', str(output)],
                check=True, cwd=ROOT, capture_output=True, text=True,
            )
            html = output.read_text(encoding='utf-8')
            self.assertIn('data-three="object"', html)
            self.assertIn('data-three="orbs"', html)
            self.assertIn('Swiss/Bauhaus kinetic composition', html)

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

    def test_presenter_mode_docks_without_audience_controls(self):
        self.assertNotIn('presenter-toggle', JS)
        self.assertIn('.notes-visible .deck{ width:calc(100vw - var(--presenter-rail)); }', CSS)
        self.assertIn('.notes-visible .slide{ width:calc(100vw - var(--presenter-rail)); }', CSS)
        self.assertIn("e.key.toLowerCase() === 'n'", JS)

    def test_presenter_notes_are_editable_and_persist_locally(self):
        self.assertIn('presenter-notes-editor', JS)
        self.assertIn("notesEditor.addEventListener('input', saveNote)", JS)
        self.assertIn('localStorage.setItem(key, value)', JS)

    def test_narrative_example_has_natural_length_speaker_notes(self):
        outline = json.loads((ROOT / 'examples' / 'narrative-visual-outline.json').read_text(encoding='utf-8'))
        for page, slide in enumerate(outline['slides'], 1):
            note = ''.join(slide.get('speaker_notes', []))
            self.assertGreaterEqual(len(note), 70, 'slide %d note is too short' % page)
            self.assertLessEqual(len(note), 150, 'slide %d note is too long' % page)

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
            self.assertIn('<strong>核心结论</strong>', html)
            self.assertIn('<strong>转场提示</strong>', html)
            for redundant in ('故事角色', '情绪节拍', '观众问题', '讲述意图'):
                self.assertNotIn('<strong>%s</strong>' % redundant, html)


if __name__ == '__main__':
    unittest.main()
