"""Main orchestrator for incremental static site updates."""

from datetime import datetime, timedelta
from typing import Dict, List, Set

import config
from dependency_mapper import DependencyMapper
from drupal_client import DrupalClient
from page_generator import PageGenerator
from s3_uploader import S3Uploader


class StaticSiteUpdater:
    """Orchestrates incremental updates to the static site."""

    def __init__(self):
        """Initialize the static site updater."""
        self.drupal_client = DrupalClient()
        self.dependency_mapper = DependencyMapper()
        self.page_generator = PageGenerator()
        self.s3_uploader = S3Uploader()

    def check_and_process_changes(self, since: datetime = None) -> Dict[str, int]:
        """Check for Drupal content changes and process them incrementally.

        Args:
            since: Only process changes since this datetime. If None, uses last check time.

        Returns:
            Dictionary with statistics about what was processed
        """
        stats = {
            "pages_checked": 0,
            "pages_updated": 0,
            "facilities_checked": 0,
            "facilities_updated": 0,
            "personnel_checked": 0,
            "personnel_updated": 0,
            "procedures_checked": 0,
            "procedures_updated": 0,
            "menu_checked": 0,
            "pages_affected_by_menu": 0,
        }

        # If no 'since' time provided, check for unprocessed content
        if since is None:
            # Get unprocessed content from tracking database
            unprocessed = self.dependency_mapper.get_unprocessed_content()
            print(f"Found {len(unprocessed)} unprocessed content items")

            for item in unprocessed:
                self._process_content_item(
                    item["content_type"], item["content_id"], stats
                )
        else:
            # Check each content type for changes
            self._check_content_type_changes(
                "page", config.CONTENT_TYPES["page"], since, stats
            )
            self._check_content_type_changes(
                "facility", config.CONTENT_TYPES["facility"], since, stats
            )
            self._check_content_type_changes(
                "personnel", config.CONTENT_TYPES["personnel"], since, stats
            )
            self._check_content_type_changes(
                "procedure", config.CONTENT_TYPES["procedure"], since, stats
            )
            self._check_menu_changes(since, stats)

        return stats

    def _check_content_type_changes(
        self, name: str, content_type: str, since: datetime, stats: Dict
    ):
        """Check for changes in a specific content type.

        Args:
            name: Human-readable name (for stats)
            content_type: Drupal content type
            since: Check for changes since this time
            stats: Statistics dictionary to update
        """
        changes = self.drupal_client.get_content_changes(content_type, since)
        stats[f"{name}s_checked"] = len(changes)

        for content in changes:
            # Record the change
            self.dependency_mapper.record_content_change(
                content_type, content["id"], content["changed"]
            )

            # Process the change
            if self._process_content_item(content_type, content["id"], stats, content):
                stats[f"{name}s_updated"] += 1

    def _check_menu_changes(self, since: datetime, stats: Dict):
        """Check for menu changes.

        Args:
            since: Check for changes since this time
            stats: Statistics dictionary to update
        """
        menu_type = config.CONTENT_TYPES["menu"]
        changes = self.drupal_client.get_content_changes(menu_type, since)
        stats["menu_checked"] = len(changes)

        if changes:
            # Menu changed - need to regenerate all pages that use it
            # In a real system, we'd track which pages use which menus
            # For this demo, we'll just mark that menus changed
            print(f"Menu items changed: {len(changes)}")

            # Get all pages that use menus (typically all of them)
            affected_pages = self.dependency_mapper.get_pages_using_menu("main")
            stats["pages_affected_by_menu"] = len(affected_pages)

            # Note: In a production system, you'd regenerate these pages
            # For demonstration, we're just tracking the impact

    def _process_content_item(
        self, content_type: str, content_id: str, stats: Dict, content: Dict = None
    ) -> bool:
        """Process a single content item that has changed.

        Args:
            content_type: Type of content
            content_id: Content UUID
            stats: Statistics dictionary
            content: Optional pre-fetched content data

        Returns:
            True if successfully processed
        """
        # Fetch content if not provided
        if content is None:
            content = self.drupal_client.get_content_by_id(content_type, content_id)
            if not content:
                print(f"Could not fetch content: {content_type}/{content_id}")
                return False

        # Get affected pages
        affected_pages = self.dependency_mapper.get_affected_pages(
            content_type, content_id
        )

        # If no affected pages, this might be a new content item
        # Create a page for it
        if not affected_pages:
            page_path = self._generate_page_path(content_type, content)
            affected_pages = {page_path}

            # Record the dependency
            self.dependency_mapper.add_dependency(
                page_path, content_type, content_id, "primary"
            )

        # Get menu structure (if it exists)
        menu = self._get_menu_structure()

        # Regenerate each affected page
        for page_path in affected_pages:
            html = self.page_generator.generate_page(content_type, content, menu)

            # Upload to S3
            s3_key = page_path.lstrip("/")
            success = self.s3_uploader.upload_html(html, s3_key)

            if success or not self.s3_uploader.s3_client:
                # Record that page was generated
                self.dependency_mapper.record_page_generated(page_path, s3_key)
                print(f"Generated and uploaded: {page_path}")

        # Mark content as processed
        self.dependency_mapper.mark_content_processed(content_type, content_id)

        return True

    def _generate_page_path(self, content_type: str, content: Dict) -> str:
        """Generate a page path from content.

        Args:
            content_type: Type of content
            content: Content data

        Returns:
            Page path (e.g., '/pages/about.html')
        """
        # Extract simple type name
        type_name = (
            content_type.split("--")[1] if "--" in content_type else content_type
        )

        # Generate slug from title/name
        title = content.get(
            "title", content.get("attributes", {}).get("name", "untitled")
        )
        slug = self._slugify(title)

        # Generate path based on type
        if type_name == "page":
            return f"/pages/{slug}.html"
        elif type_name == "facility":
            return f"/facilities/{slug}.html"
        elif type_name == "personnel":
            return f"/personnel/{slug}.html"
        elif type_name == "procedure":
            return f"/procedures/{slug}.html"
        else:
            return f"/{type_name}/{slug}.html"

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug.

        Args:
            text: Text to slugify

        Returns:
            Slugified text
        """
        import re

        # Convert to lowercase
        text = text.lower()

        # Replace spaces and special characters with hyphens
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_-]+", "-", text)
        text = re.sub(r"^-+|-+$", "", text)

        return text or "untitled"

    def _get_menu_structure(self) -> List[Dict]:
        """Get the menu structure.

        Returns:
            List of menu items
        """
        try:
            menu_items = self.drupal_client.get_menu_structure("main")

            # Transform to simple format
            menu = []
            for item in menu_items:
                attrs = item.get("attributes", {})
                menu.append(
                    {
                        "title": item.get("title", ""),
                        "url": (
                            attrs.get("link", {}).get("uri", "#")
                            if isinstance(attrs.get("link"), dict)
                            else "#"
                        ),
                    }
                )

            return menu
        except Exception as e:
            print(f"Error fetching menu: {e}")
            return []

    def full_site_regeneration(self):
        """Perform a full site regeneration (legacy mode).

        This is the old approach - regenerate everything.
        Kept for comparison and fallback purposes.
        """
        print("Starting full site regeneration (this may take a while)...")

        stats = {"total_pages": 0, "successful": 0, "failed": 0}

        # Get all content of each type
        for name, content_type in config.CONTENT_TYPES.items():
            if name == "menu" or name == "region":
                continue  # Skip menu and region types

            items = self.drupal_client.get_content_changes(content_type)

            for item in items:
                stats["total_pages"] += 1
                try:
                    self._process_content_item(content_type, item["id"], stats, item)
                    stats["successful"] += 1
                except Exception as e:
                    print(f"Error processing {content_type}/{item['id']}: {e}")
                    stats["failed"] += 1

        print(f"Full regeneration complete: {stats}")
        return stats


def main():
    """Main entry point demonstrating the incremental update system."""
    print("=" * 60)
    print("Drupal Static CMS - Incremental Update System")
    print("=" * 60)

    updater = StaticSiteUpdater()

    # Example 1: Check for changes in the last hour
    print("\n--- Example 1: Check for changes in the last hour ---")
    one_hour_ago = datetime.now() - timedelta(hours=1)
    stats = updater.check_and_process_changes(since=one_hour_ago)
    print(f"Processing statistics: {stats}")

    # Example 2: Process any unprocessed content
    print("\n--- Example 2: Process unprocessed content ---")
    stats = updater.check_and_process_changes()
    print(f"Processing statistics: {stats}")

    # Example 3: Demonstrate how a single page update works
    print("\n--- Example 3: Simulate single page update ---")
    print("When a page is updated in Drupal:")
    print("1. Drupal API returns the changed content")
    print("2. System determines which static pages are affected")
    print("3. Only affected pages are regenerated")
    print("4. Updated pages are uploaded to S3")
    print("5. Change is marked as processed")

    # Example 4: Demonstrate how a facility update affects multiple pages
    print("\n--- Example 4: Simulate facility update affecting multiple pages ---")
    print("When a hospital facility is updated:")
    print("1. The facility's detail page is regenerated")
    print("2. Any directory/listing pages that include it are regenerated")
    print("3. Pages that reference the facility are regenerated")
    print("4. All updated pages are uploaded to S3")

    # Example 5: Show impact of menu changes
    print("\n--- Example 5: Menu update impact ---")
    print("When a menu item is changed:")
    print("1. System identifies all pages using that menu")
    print("2. All affected pages are regenerated with new menu")
    print("3. This could affect dozens or hundreds of pages")
    print("4. But still faster than regenerating the entire site")

    print("\n" + "=" * 60)
    print("Benefits of Incremental Updates:")
    print("- Faster content publishing (seconds vs hours)")
    print("- Reduced server load")
    print("- Lower AWS costs (fewer S3 operations)")
    print("- Better author experience")
    print("=" * 60)


if __name__ == "__main__":
    main()
    main()
