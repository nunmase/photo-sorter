import os
from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image

from photo_sorter import PhotoSorterApp


class PhotoSorterTests(unittest.TestCase):
    def setUp(self):
        workspace = TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        base = Path(workspace.name)
        self.source = base / 'source'
        self.destination = base / 'destination'
        self.source.mkdir()
        self.destination.mkdir()
        self.original = self.source / 'photo.png'
        self.sorted = self.destination / 'photo.png'
        Image.new('RGB', (8, 8), 'red').save(self.original)

        self.enterContext(patch.dict(os.environ, {'APPDATA': str(base / 'settings')}))
        self.errors = self.enterContext(patch('photo_sorter.messagebox.showerror'))
        self.enterContext(patch('photo_sorter.messagebox.showinfo'))
        root = tk.Tk()
        self.addCleanup(self.close_root, root)
        root.withdraw()
        self.app = PhotoSorterApp(root)
        self.app.source_folder = str(self.source)
        self.app.destination_folders = {1: str(self.destination)}
        self.app.load_photos()

    @staticmethod
    def close_root(root):
        root.unbind('<Configure>')
        for callback in root.tk.splitlist(root.tk.call('after', 'info')):
            root.after_cancel(callback)
        root.destroy()

    def test_moving_keeps_both_files_when_a_name_is_taken(self):
        original = self.original.read_bytes()
        Image.new('RGB', (8, 8), 'blue').save(self.sorted)
        existing = self.sorted.read_bytes()

        self.app.move_photo(1)
        self.app.root.update()

        self.assertTrue(self.original.exists(), 'The source photo was removed')
        self.assertEqual(self.original.read_bytes(), original)
        self.assertEqual(self.sorted.read_bytes(), existing)
        self.assertEqual(self.app.photo_list, ['photo.png'])
        self.errors.assert_called_once()

    def test_moving_does_not_nest_under_a_same_name_directory(self):
        self.sorted.mkdir()

        self.app.move_photo(1)
        self.app.root.update()

        self.assertTrue(self.original.exists(), 'The source photo was removed')
        self.assertEqual(list(self.sorted.iterdir()), [])
        self.errors.assert_called_once()

    def test_move_and_undo_restore_the_photo(self):
        original = self.original.read_bytes()
        self.app.toggle_sorting_mode()
        self.app.handle_keypress(SimpleNamespace(char='1'))
        self.app.root.update()
        self.assertFalse(self.original.exists())
        self.assertEqual(self.sorted.read_bytes(), original)

        self.app.undo_move()

        self.assertEqual(self.original.read_bytes(), original)
        self.assertFalse(self.sorted.exists())
        self.assertEqual(self.app.photo_list, ['photo.png'])

    def test_undo_cannot_overwrite_a_new_source_photo_and_can_retry(self):
        original = self.original.read_bytes()
        self.app.move_photo(1)
        self.app.root.update()
        Image.new('RGB', (8, 8), 'blue').save(self.original)
        replacement = self.original.read_bytes()

        self.app.undo_move()

        self.assertEqual(self.original.read_bytes(), replacement)
        self.assertEqual(self.sorted.read_bytes(), original)
        self.errors.assert_called_once()
        self.original.unlink()
        self.app.undo_move()
        self.assertEqual(self.original.read_bytes(), original)
        self.assertFalse(self.sorted.exists())

    def test_undo_after_switching_source_keeps_the_current_preview(self):
        self.app.move_photo(1)
        self.app.root.update()
        second_source = self.source.parent / 'second'
        second_source.mkdir()
        Image.new('RGB', (8, 8), 'green').save(second_source / 'other.png')
        self.app.source_folder = str(second_source)
        self.app.load_photos()

        self.app.undo_move()

        self.assertTrue(self.original.exists())
        self.assertFalse(self.sorted.exists())
        self.assertEqual(self.app.photo_list, ['other.png'])
