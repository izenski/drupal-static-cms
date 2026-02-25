"""Content dependency mapping system to track relationships between Drupal content and static pages."""

import sqlite3
from datetime import datetime
from typing import Dict, List, Set

import config


class DependencyMapper:
    """Tracks dependencies between Drupal content and static pages."""

    def __init__(self, db_path: str = None):
        """Initialize the dependency mapper.

        Args:
            db_path: Path to SQLite database for tracking
        """
        self.db_path = db_path or config.CHANGE_TRACKING_DB
        self._init_database()

    def _init_database(self):
        """Initialize the SQLite database with necessary tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Table to track content item last changed times
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS content_tracking (
                content_type TEXT NOT NULL,
                content_id TEXT NOT NULL,
                last_changed TIMESTAMP,
                last_processed TIMESTAMP,
                PRIMARY KEY (content_type, content_id)
            )
        """
        )

        # Table to track dependencies (which pages use which content)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS content_dependencies (
                page_path TEXT NOT NULL,
                content_type TEXT NOT NULL,
                content_id TEXT NOT NULL,
                dependency_type TEXT,
                PRIMARY KEY (page_path, content_type, content_id)
            )
        """
        )

        # Table to track static page metadata
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS static_pages (
                page_path TEXT PRIMARY KEY,
                last_generated TIMESTAMP,
                s3_key TEXT
            )
        """
        )

        conn.commit()
        conn.close()

    def record_content_change(
        self, content_type: str, content_id: str, changed_time: datetime
    ):
        """Record that a content item has changed.

        Args:
            content_type: Type of content (e.g., 'node--page')
            content_id: UUID of the content item
            changed_time: When the content was changed
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO content_tracking 
            (content_type, content_id, last_changed, last_processed)
            VALUES (?, ?, ?, ?)
        """,
            (content_type, content_id, changed_time, None),
        )

        conn.commit()
        conn.close()

    def mark_content_processed(self, content_type: str, content_id: str):
        """Mark a content item as processed.

        Args:
            content_type: Type of content
            content_id: UUID of the content item
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE content_tracking 
            SET last_processed = ? 
            WHERE content_type = ? AND content_id = ?
        """,
            (datetime.now(), content_type, content_id),
        )

        conn.commit()
        conn.close()

    def get_unprocessed_content(self) -> List[Dict]:
        """Get all content items that have changed but not been processed.

        Returns:
            List of unprocessed content items
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT content_type, content_id, last_changed 
            FROM content_tracking 
            WHERE last_processed IS NULL 
               OR last_changed > last_processed
            ORDER BY last_changed DESC
        """
        )

        items = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return items

    def add_dependency(
        self,
        page_path: str,
        content_type: str,
        content_id: str,
        dependency_type: str = "reference",
    ):
        """Add a dependency relationship.

        Args:
            page_path: Path to the static page (e.g., '/facilities/hospital-1.html')
            content_type: Type of Drupal content
            content_id: UUID of the content item
            dependency_type: Type of dependency (e.g., 'primary', 'reference', 'menu')
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO content_dependencies 
            (page_path, content_type, content_id, dependency_type)
            VALUES (?, ?, ?, ?)
        """,
            (page_path, content_type, content_id, dependency_type),
        )

        conn.commit()
        conn.close()

    def get_affected_pages(self, content_type: str, content_id: str) -> Set[str]:
        """Get all pages that depend on a specific content item.

        Args:
            content_type: Type of content
            content_id: UUID of the content item

        Returns:
            Set of page paths that need to be regenerated
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT page_path 
            FROM content_dependencies 
            WHERE content_type = ? AND content_id = ?
        """,
            (content_type, content_id),
        )

        pages = {row[0] for row in cursor.fetchall()}
        conn.close()

        return pages

    def get_pages_using_menu(self, menu_id: str) -> Set[str]:
        """Get all pages that use a specific menu.

        Menu changes can affect many pages, so this is a special case.

        Args:
            menu_id: Menu identifier

        Returns:
            Set of page paths affected by menu changes
        """
        # In a real system, this might query which pages use which menus
        # For demonstration, we'll return all pages since menus are typically global
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT page_path FROM static_pages")
        pages = {row[0] for row in cursor.fetchall()}
        conn.close()

        return pages

    def record_page_generated(self, page_path: str, s3_key: str):
        """Record that a static page has been generated.

        Args:
            page_path: Path to the page
            s3_key: S3 key where the page is stored
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO static_pages 
            (page_path, last_generated, s3_key)
            VALUES (?, ?, ?)
        """,
            (page_path, datetime.now(), s3_key),
        )

        conn.commit()
        conn.close()

    def clear_dependencies_for_page(self, page_path: str):
        """Clear all dependencies for a page (useful before rebuilding dependency map).

        Args:
            page_path: Path to the page
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM content_dependencies 
            WHERE page_path = ?
        """,
            (page_path,),
        )

        conn.commit()
        conn.close()
        conn.close()
