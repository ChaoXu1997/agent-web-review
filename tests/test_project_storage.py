"""Tests for ProjectMappingStorage — get_urls_by_project_path."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from project_storage import ProjectMappingStorage


class TestGetUrlsByProjectPath(unittest.TestCase):
    """Tests for ProjectMappingStorage.get_urls_by_project_path."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.storage = ProjectMappingStorage(data_dir=self.tmp)

    def test_exact_match(self):
        """Exact project_path match returns associated URLs."""
        self.storage.create({"page_url": "http://a.com", "project_path": "/home/user/project"})
        self.storage.create({"page_url": "http://b.com", "project_path": "/home/user/other"})

        result = self.storage.get_urls_by_project_path("/home/user/project")

        self.assertEqual(result, ["http://a.com"])

    def test_trailing_slash_normalization(self):
        """Trailing slash is normalized — /home/user/project matches /home/user/project/."""
        self.storage.create({"page_url": "http://a.com", "project_path": "/home/user/project"})
        self.storage.create({"page_url": "http://b.com", "project_path": "/home/user/project/"})

        result = self.storage.get_urls_by_project_path("/home/user/project/")

        self.assertEqual(sorted(result), sorted(["http://a.com", "http://b.com"]))

    def test_no_match_returns_empty(self):
        """Unknown project_path returns empty list."""
        self.storage.create({"page_url": "http://a.com", "project_path": "/home/user/project"})

        result = self.storage.get_urls_by_project_path("/no/such/path")

        self.assertEqual(result, [])

    def test_empty_storage_returns_empty(self):
        """Empty storage returns empty list for any path."""
        result = self.storage.get_urls_by_project_path("/anything")

        self.assertEqual(result, [])

    def test_multiple_urls_per_project(self):
        """Multiple URLs mapped to same project_path are all returned."""
        self.storage.create({"page_url": "http://a.com", "project_path": "/home/user/project"})
        self.storage.create({"page_url": "http://b.com", "project_path": "/home/user/project"})
        self.storage.create({"page_url": "http://c.com", "project_path": "/home/user/project/"})

        result = self.storage.get_urls_by_project_path("/home/user/project")

        self.assertEqual(sorted(result), sorted(["http://a.com", "http://b.com", "http://c.com"]))

    def test_query_without_trailing_slash_matches_stored_with_slash(self):
        """Query without trailing slash matches stored paths that have trailing slash."""
        self.storage.create({"page_url": "http://a.com", "project_path": "/home/user/project/"})

        result = self.storage.get_urls_by_project_path("/home/user/project")

        self.assertEqual(result, ["http://a.com"])


if __name__ == "__main__":
    unittest.main()
