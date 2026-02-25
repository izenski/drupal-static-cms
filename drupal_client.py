"""Client for interacting with Drupal JSON:API to detect content changes."""

from datetime import datetime
from typing import Dict, List, Optional

import config
import requests
from dateutil import parser as date_parser


class DrupalClient:
    """Client for querying Drupal JSON:API and tracking content changes."""

    def __init__(self, base_url: str = None):
        """Initialize the Drupal client.

        Args:
            base_url: Base URL for Drupal JSON:API endpoint
        """
        self.base_url = base_url or config.DRUPAL_API_ENDPOINT
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json",
            }
        )

    def get_content_changes(
        self, content_type: str, since: datetime = None
    ) -> List[Dict]:
        """Get content items of a specific type that have changed since a given time.

        Args:
            content_type: The Drupal content type (e.g., 'node--page')
            since: Only return items changed after this datetime

        Returns:
            List of content items with their metadata
        """
        url = f"{self.base_url}/{content_type}"
        params = {}

        # Filter by changed date if provided
        if since:
            # Format datetime for Drupal API filter
            since_str = since.strftime("%Y-%m-%dT%H:%M:%S")
            params["filter[changed][condition][path]"] = "changed"
            params["filter[changed][condition][operator]"] = ">"
            params["filter[changed][condition][value]"] = since_str

        # Sort by most recently changed
        params["sort"] = "-changed"

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            return self._parse_content_items(data)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching content changes: {e}")
            return []

    def get_content_by_id(self, content_type: str, entity_id: str) -> Optional[Dict]:
        """Get a specific content item by its ID.

        Args:
            content_type: The Drupal content type
            entity_id: The entity UUID

        Returns:
            Content item data or None if not found
        """
        url = f"{self.base_url}/{content_type}/{entity_id}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()

            if "data" in data:
                return self._parse_content_item(data["data"])
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching content by ID: {e}")
            return None

    def get_menu_structure(self, menu_name: str = "main") -> List[Dict]:
        """Get the menu structure.

        Args:
            menu_name: Name of the menu to retrieve

        Returns:
            List of menu items
        """
        content_type = config.CONTENT_TYPES["menu"]
        url = f"{self.base_url}/{content_type}"
        params = {"filter[menu_name]": menu_name, "sort": "weight"}

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            return self._parse_content_items(data)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching menu structure: {e}")
            return []

    def _parse_content_items(self, data: Dict) -> List[Dict]:
        """Parse multiple content items from JSON:API response.

        Args:
            data: JSON:API response data

        Returns:
            List of parsed content items
        """
        items = []
        if "data" in data:
            for item in data["data"]:
                items.append(self._parse_content_item(item))
        return items

    def _parse_content_item(self, item: Dict) -> Dict:
        """Parse a single content item from JSON:API format.

        Args:
            item: JSON:API item data

        Returns:
            Parsed content item
        """
        attributes = item.get("attributes", {})

        # Extract common fields
        parsed = {
            "id": item.get("id"),
            "type": item.get("type"),
            "title": attributes.get("title", attributes.get("name", "Untitled")),
            "created": self._parse_datetime(attributes.get("created")),
            "changed": self._parse_datetime(attributes.get("changed")),
            "published": attributes.get("status", True),
            "attributes": attributes,
            "relationships": item.get("relationships", {}),
        }

        return parsed

    def _parse_datetime(self, dt_string: str) -> Optional[datetime]:
        """Parse datetime string to datetime object.

        Args:
            dt_string: Datetime string

        Returns:
            Datetime object or None
        """
        if not dt_string:
            return None
        try:
            return date_parser.parse(dt_string)
        except (ValueError, TypeError):
            return None
            return None
