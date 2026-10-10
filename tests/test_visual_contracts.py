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
from scripts.build import image_has_alpha


class VisualContractTests(unittest.TestCase):
    def test_retired_object_and_orbs_scenes_render_nothing(self):
        self.assertNotIn('function objectScene', BUILD)
        self.assertNotIn('function orbsScene', BUILD)
        self.assertIn("REMOVED_THREE_SCENES = {'object', 'orbs'}", BUILD)
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = json.loads(
                (ROOT / 'examples' / 'narrative-visual-outline.json').read_text(encoding='utf-8')
            )
            outline['slides'][1]['three'] = {'scene': 'object'}
            outline['slides'][2]['three'] = {'scene': 'orbs'}
            source = Path(temp_dir) / 'outline.json'
            source.write_text(json.dumps(outline, ensure_ascii=False), encoding='utf-8')
            output = Path(temp_dir) / 'motion.html'
            subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'build.py'),
                 '--outline', str(source),
                 '--out', str(output)],
                check=True, cwd=ROOT, capture_output=True, text=True,
            )
            html = output.read_text(encoding='utf-8')
            self.assertNotIn('data-three="object"', html)
            self.assertNotIn('data-three="orbs"', html)

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

    def test_cover_preserves_complete_artwork_by_default(self):
        self.assertIn('.cover-hero.hero-fit-contain img', CSS)
        self.assertIn('object-fit:contain', CSS)
        self.assertIn('.cover-hero.hero-mode-float', CSS)
        cover = (ROOT / 'templates' / 'single-page' / 'cover.html').read_text(encoding='utf-8')
        self.assertIn('hero-mode-{{hero_mode}}', cover)
        self.assertIn('hero-fit-{{hero_fit}}', cover)
        self.assertIn('--hero-position:{{hero_position}}', cover)

    def test_png_alpha_header_selects_floating_cover_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image = Path(temp_dir) / 'hero.png'
            image.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\0' * 17 + bytes([6]))
            self.assertTrue(image_has_alpha('hero.png', temp_dir))

    def test_sourced_images_have_non_obstructive_layout_contracts(self):
        self.assertIn('.slide-web-background', CSS)
        self.assertIn('.slide-web-scrim', CSS)
        self.assertIn('.slide-support-image', CSS)
        self.assertIn('.slide.has-support-image.support-right .slide-content', CSS)
        self.assertIn("universal_media_markup(slide)", BUILD)

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
