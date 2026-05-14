"""Tests for MCP Server — awr_get_comments tool."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from models import Comment
from storage import CommentStorage
from project_storage import ProjectMappingStorage
from mcp_server import awr_get_comments, awr_resolve_comment, awr_delete_comment, create_mcp_server


class TestMCPAwRGetCommentsCycle1(unittest.TestCase):
    """Cycle 1: awr_get_comments with no parameters returns all comments."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.storage = CommentStorage(data_dir=self.tmp)

    def test_no_params_returns_all_comments(self):
        """awr_get_comments() with no arguments returns every comment as a list of dicts."""
        c1 = Comment(page_url="http://example.com", comment_text="fix nav")
        c2 = Comment(page_url="http://other.com", comment_text="broken link")
        self.storage.create(c1)
        self.storage.create(c2)

        result = awr_get_comments(self.storage)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        for item in result:
            self.assertIsInstance(item, dict)
        texts = [r["comment_text"] for r in result]
        self.assertIn("fix nav", texts)
        self.assertIn("broken link", texts)

    def test_no_params_returns_empty_list_when_no_comments(self):
        """awr_get_comments() returns empty list when storage is empty."""
        result = awr_get_comments(self.storage)
        self.assertEqual(result, [])


class TestMCPAwRGetCommentsCycle2(unittest.TestCase):
    """Cycle 2: awr_get_comments filtered by page_url."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.storage = CommentStorage(data_dir=self.tmp)
        self.storage.create(Comment(page_url="http://example.com", comment_text="fix nav"))
        self.storage.create(Comment(page_url="http://other.com", comment_text="broken link"))
        self.storage.create(Comment(page_url="http://example.com", comment_text="bad color"))

    def test_filter_by_page_url(self):
        """awr_get_comments(page_url=...) returns only comments for that page."""
        result = awr_get_comments(self.storage, page_url="http://example.com")
        self.assertEqual(len(result), 2)
        for item in result:
            self.assertEqual(item["page_url"], "http://example.com")

    def test_filter_by_nonexistent_page_url(self):
        """awr_get_comments(page_url=...) returns empty list when no matches."""
        result = awr_get_comments(self.storage, page_url="http://nope.com")
        self.assertEqual(result, [])


class TestMCPAwRGetCommentsCycle3(unittest.TestCase):
    """Cycle 3: awr_get_comments filtered by status."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.storage = CommentStorage(data_dir=self.tmp)
        self.storage.create(Comment(page_url="http://example.com", comment_text="open 1"))
        c2 = Comment(page_url="http://example.com", comment_text="resolved 1")
        self.storage.create(c2)
        self.storage.update_status(c2.id, "resolved")
        self.storage.create(Comment(page_url="http://example.com", comment_text="open 2"))

    def test_filter_by_status_open(self):
        """awr_get_comments(status='open') returns only open comments."""
        result = awr_get_comments(self.storage, status="open")
        self.assertEqual(len(result), 2)
        for item in result:
            self.assertEqual(item["status"], "open")

    def test_filter_by_status_resolved(self):
        """awr_get_comments(status='resolved') returns only resolved comments."""
        result = awr_get_comments(self.storage, status="resolved")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["comment_text"], "resolved 1")

    def test_filter_by_page_url_and_status(self):
        """awr_get_comments(page_url=..., status=...) combines both filters."""
        result = awr_get_comments(self.storage, page_url="http://example.com", status="open")
        self.assertEqual(len(result), 2)

    def test_create_mcp_server_returns_fastmcp_instance(self):
        """create_mcp_server() returns a FastMCP instance."""
        app = create_mcp_server(self.storage)
        from mcp.server.fastmcp import FastMCP
        self.assertIsInstance(app, FastMCP)


class TestMCPResolveComment(unittest.TestCase):
    """awr_resolve_comment: mark a comment as resolved."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.storage = CommentStorage(data_dir=self.tmp)

    def test_resolve_existing_comment(self):
        """awr_resolve_comment(storage, comment_id) returns updated comment dict with status='resolved'."""
        c = Comment(page_url="http://example.com", comment_text="fix nav")
        self.storage.create(c)

        result = awr_resolve_comment(self.storage, c.id)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], c.id)
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["comment_text"], "fix nav")

    def test_resolve_nonexistent_comment(self):
        """awr_resolve_comment with a nonexistent id returns error dict."""
        result = awr_resolve_comment(self.storage, "nonexistent-id")

        self.assertIsInstance(result, dict)
        self.assertEqual(result["error"], "Comment not found")
        self.assertEqual(result["comment_id"], "nonexistent-id")


class TestMCPDeleteComment(unittest.TestCase):
    """awr_delete_comment: delete a comment."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.storage = CommentStorage(data_dir=self.tmp)

    def test_delete_existing_comment(self):
        """awr_delete_comment(storage, comment_id) returns {'deleted': True} and comment is gone."""
        c = Comment(page_url="http://example.com", comment_text="remove me")
        self.storage.create(c)

        result = awr_delete_comment(self.storage, c.id)

        self.assertIsInstance(result, dict)
        self.assertEqual(result, {"deleted": True})
        # Verify comment is gone from storage
        remaining = self.storage.get_all()
        self.assertEqual(len(remaining), 0)

    def test_delete_nonexistent_comment(self):
        """awr_delete_comment with a nonexistent id returns error dict."""
        result = awr_delete_comment(self.storage, "ghost-id")

        self.assertIsInstance(result, dict)
        self.assertEqual(result["error"], "Comment not found")
        self.assertEqual(result["comment_id"], "ghost-id")


class TestMCPGetCommentsByProjectPath(unittest.TestCase):
    """awr_get_comments with project_path parameter."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.storage = CommentStorage(data_dir=self.tmp)
        self.project_storage = ProjectMappingStorage(data_dir=self.tmp)
        # Set up project mappings
        self.project_storage.create({"page_url": "http://a.com", "project_path": "/home/user/project"})
        self.project_storage.create({"page_url": "http://b.com", "project_path": "/home/user/project"})
        self.project_storage.create({"page_url": "http://c.com", "project_path": "/home/user/other"})
        # Create comments across different URLs
        self.storage.create(Comment(page_url="http://a.com", comment_text="fix a"))
        self.storage.create(Comment(page_url="http://b.com", comment_text="fix b"))
        self.storage.create(Comment(page_url="http://c.com", comment_text="fix c"))

    def test_filter_by_project_path(self):
        """awr_get_comments(project_path=...) returns comments for URLs mapped to that project."""
        result = awr_get_comments(
            self.storage,
            project_storage=self.project_storage,
            project_path="/home/user/project",
        )
        texts = {r["comment_text"] for r in result}
        self.assertEqual(texts, {"fix a", "fix b"})

    def test_filter_by_unknown_project_path(self):
        """awr_get_comments(project_path=...) with unknown path returns empty list."""
        result = awr_get_comments(
            self.storage,
            project_storage=self.project_storage,
            project_path="/no/such/path",
        )
        self.assertEqual(result, [])

    def test_project_path_combined_with_status(self):
        """awr_get_comments(project_path=..., status=...) applies both filters (AND logic)."""
        # Resolve one comment
        comments_a = self.storage.get_all(page_url="http://a.com")
        self.storage.update_status(comments_a[0].id, "resolved")

        result = awr_get_comments(
            self.storage,
            project_storage=self.project_storage,
            project_path="/home/user/project",
            status="resolved",
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["comment_text"], "fix a")
        self.assertEqual(result[0]["status"], "resolved")

    def test_project_path_and_page_url_intersect(self):
        """When both project_path and page_url provided, intersect results (AND logic)."""
        result = awr_get_comments(
            self.storage,
            project_storage=self.project_storage,
            project_path="/home/user/project",
            page_url="http://a.com",
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["comment_text"], "fix a")

    def test_project_path_and_page_url_no_overlap(self):
        """When project_path URLs don't include page_url, result is empty."""
        result = awr_get_comments(
            self.storage,
            project_storage=self.project_storage,
            project_path="/home/user/project",
            page_url="http://c.com",
        )
        self.assertEqual(result, [])

    def test_result_includes_page_url(self):
        """Each comment dict in the result includes page_url field."""
        result = awr_get_comments(
            self.storage,
            project_storage=self.project_storage,
            project_path="/home/user/project",
        )
        for item in result:
            self.assertIn("page_url", item)
            self.assertIn(item["page_url"], {"http://a.com", "http://b.com"})

    def test_project_path_with_trailing_slash(self):
        """Trailing slash normalization works through to awr_get_comments."""
        result = awr_get_comments(
            self.storage,
            project_storage=self.project_storage,
            project_path="/home/user/project/",
        )
        texts = {r["comment_text"] for r in result}
        self.assertEqual(texts, {"fix a", "fix b"})

    def test_no_project_storage_returns_empty(self):
        """When project_path provided but no project_storage, returns empty list."""
        result = awr_get_comments(
            self.storage,
            project_path="/home/user/project",
        )
        self.assertEqual(result, [])
