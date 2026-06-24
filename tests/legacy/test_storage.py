"""Unit tests for CommentStorage."""

import json
import os
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from storage import CommentStorage
from models import Comment


class TestCommentStorage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.storage = CommentStorage(data_dir=self.tmp)

    def _read_file(self):
        path = os.path.join(self.tmp, "comments.json")
        if not os.path.exists(path):
            return {"comments": []}
        with open(path, "r") as f:
            return json.load(f)

    def test_create_and_get_all(self):
        c = Comment(page_url="http://example.com", comment_text="fix this")
        self.storage.create(c)
        all_c = self.storage.get_all()
        self.assertEqual(len(all_c), 1)
        self.assertEqual(all_c[0].comment_text, "fix this")
        self.assertTrue(all_c[0].id)

    def test_get_by_id(self):
        c = Comment(page_url="http://a.com", comment_text="hello")
        created = self.storage.create(c)
        found = self.storage.get_by_id(created.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.comment_text, "hello")

    def test_get_by_id_not_found(self):
        self.assertIsNone(self.storage.get_by_id("nonexistent"))

    def test_get_all_filtered_by_page_url(self):
        self.storage.create(Comment(page_url="http://a.com", comment_text="a"))
        self.storage.create(Comment(page_url="http://b.com", comment_text="b"))
        self.storage.create(Comment(page_url="http://a.com", comment_text="a2"))
        a_comments = self.storage.get_all(page_url="http://a.com")
        self.assertEqual(len(a_comments), 2)
        b_comments = self.storage.get_all(page_url="http://b.com")
        self.assertEqual(len(b_comments), 1)

    def test_delete(self):
        c = Comment(page_url="http://a.com", comment_text="del me")
        created = self.storage.create(c)
        self.assertTrue(self.storage.delete(created.id))
        self.assertIsNone(self.storage.get_by_id(created.id))
        self.assertFalse(self.storage.delete("nonexistent"))

    def test_delete_all_for_page(self):
        self.storage.create(Comment(page_url="http://a.com", comment_text="1"))
        self.storage.create(Comment(page_url="http://a.com", comment_text="2"))
        self.storage.create(Comment(page_url="http://b.com", comment_text="3"))
        removed = self.storage.delete_all("http://a.com")
        self.assertEqual(removed, 2)
        self.assertEqual(len(self.storage.get_all()), 1)

    def test_atomic_write(self):
        c = Comment(page_url="http://a.com", comment_text="atomic")
        self.storage.create(c)
        data = self._read_file()
        self.assertIn("comments", data)
        self.assertEqual(len(data["comments"]), 1)
        # no tmp file should remain
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "comments.json.tmp")))

    def test_corrupt_file_recovery(self):
        path = os.path.join(self.tmp, "comments.json")
        with open(path, "w") as f:
            f.write("{broken json!!!")
        comments = self.storage.get_all()
        self.assertEqual(len(comments), 0)
        # backup should exist
        self.assertTrue(os.path.exists(path + ".corrupt"))

    def test_concurrent_writes(self):
        barrier = threading.Barrier(4)
        errors = []

        def writer(i):
            try:
                barrier.wait(timeout=2)
                for _ in range(20):
                    self.storage.create(Comment(page_url="http://race.com", comment_text=f"t{i}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)
        self.assertEqual(len(errors), 0, f"Errors during concurrent writes: {errors}")
        self.assertEqual(len(self.storage.get_all()), 80)

    def test_from_dict_filters_unknown_fields(self):
        c = Comment.from_dict({
            "page_url": "http://a.com",
            "comment_text": "test",
            "unknown_field": "should be ignored",
        })
        self.assertFalse(hasattr(c, "unknown_field"))

    def test_to_dict_roundtrip(self):
        original = Comment(
            page_url="http://a.com",
            comment_text="round trip",
            element_selector="#foo",
            area={"x": 10, "y": 20, "width": 100, "height": 50},
        )
        d = original.to_dict()
        restored = Comment.from_dict(d)
        self.assertEqual(restored.page_url, original.page_url)
        self.assertEqual(restored.area, original.area)
        self.assertEqual(restored.element_selector, original.element_selector)


    # ---- update status ----

    def test_update_status_resolved(self):
        c = Comment(page_url="http://a.com", comment_text="resolve me")
        created = self.storage.create(c)
        updated = self.storage.update_status(created.id, "resolved")
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, "resolved")
        self.assertEqual(updated.id, created.id)
        self.assertEqual(updated.comment_text, "resolve me")

    def test_update_status_nonexistent(self):
        result = self.storage.update_status("nonexistent123", "resolved")
        self.assertIsNone(result)

    def test_update_status_persists(self):
        c = Comment(page_url="http://a.com", comment_text="persist")
        created = self.storage.create(c)
        self.storage.update_status(created.id, "resolved")
        found = self.storage.get_by_id(created.id)
        self.assertEqual(found.status, "resolved")


    # ---- get_all with status filter ----

    def test_get_all_filter_by_status_open(self):
        c1 = Comment(page_url="http://a.com", comment_text="open1")
        c2 = Comment(page_url="http://a.com", comment_text="open2")
        c3 = Comment(page_url="http://a.com", comment_text="resolved1")
        self.storage.create(c1)
        self.storage.create(c2)
        created3 = self.storage.create(c3)
        self.storage.update_status(created3.id, "resolved")
        open_comments = self.storage.get_all(status="open")
        self.assertEqual(len(open_comments), 2)
        for c in open_comments:
            self.assertEqual(c.status, "open")

    def test_get_all_filter_by_status_resolved(self):
        c1 = Comment(page_url="http://a.com", comment_text="open1")
        c2 = Comment(page_url="http://a.com", comment_text="resolved1")
        self.storage.create(c1)
        created2 = self.storage.create(c2)
        self.storage.update_status(created2.id, "resolved")
        resolved = self.storage.get_all(status="resolved")
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].status, "resolved")

    def test_get_all_filter_by_status_no_match(self):
        c = Comment(page_url="http://a.com", comment_text="open1")
        self.storage.create(c)
        resolved = self.storage.get_all(status="resolved")
        self.assertEqual(len(resolved), 0)

    def test_get_all_filter_combined_page_url_and_status(self):
        self.storage.create(Comment(page_url="http://a.com", comment_text="a-open"))
        c2 = Comment(page_url="http://a.com", comment_text="a-resolved")
        self.storage.create(c2)
        self.storage.update_status(c2.id, "resolved")
        self.storage.create(Comment(page_url="http://b.com", comment_text="b-open"))
        result = self.storage.get_all(page_url="http://a.com", status="resolved")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].comment_text, "a-resolved")

    def test_get_all_no_status_returns_all(self):
        c1 = Comment(page_url="http://a.com", comment_text="open1")
        c2 = Comment(page_url="http://a.com", comment_text="resolved1")
        self.storage.create(c1)
        created2 = self.storage.create(c2)
        self.storage.update_status(created2.id, "resolved")
        all_c = self.storage.get_all()
        self.assertEqual(len(all_c), 2)

    # ---- delete_all with status filter ----

    def test_delete_all_by_status(self):
        c1 = Comment(page_url="http://a.com", comment_text="open1")
        c2 = Comment(page_url="http://a.com", comment_text="resolved1")
        self.storage.create(c1)
        created2 = self.storage.create(c2)
        self.storage.update_status(created2.id, "resolved")
        removed = self.storage.delete_all(status="resolved")
        self.assertEqual(removed, 1)
        remaining = self.storage.get_all()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].status, "open")

    def test_delete_all_by_status_no_match(self):
        c = Comment(page_url="http://a.com", comment_text="open1")
        self.storage.create(c)
        removed = self.storage.delete_all(status="resolved")
        self.assertEqual(removed, 0)
        self.assertEqual(len(self.storage.get_all()), 1)

    def test_delete_all_combined_page_url_and_status(self):
        self.storage.create(Comment(page_url="http://a.com", comment_text="a-open"))
        c2 = Comment(page_url="http://a.com", comment_text="a-resolved")
        self.storage.create(c2)
        self.storage.update_status(c2.id, "resolved")
        self.storage.create(Comment(page_url="http://b.com", comment_text="b-resolved"))
        # also create resolved on b.com
        c4 = Comment(page_url="http://b.com", comment_text="b-resolved2")
        self.storage.create(c4)
        self.storage.update_status(c4.id, "resolved")
        removed = self.storage.delete_all(page_url="http://a.com", status="resolved")
        self.assertEqual(removed, 1)
        self.assertEqual(len(self.storage.get_all(page_url="http://a.com")), 1)
        self.assertEqual(len(self.storage.get_all(page_url="http://b.com")), 2)


if __name__ == "__main__":
    unittest.main()
