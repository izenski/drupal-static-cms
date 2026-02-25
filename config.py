"""Configuration settings for the Drupal Static CMS system."""

import os

# Drupal API Configuration
DRUPAL_BASE_URL = os.getenv("DRUPAL_BASE_URL", "https://example.com")
DRUPAL_API_ENDPOINT = f"{DRUPAL_BASE_URL}/jsonapi"

# S3 Configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "hospital-static-site")
S3_REGION = os.getenv("S3_REGION", "us-east-1")

# Content Types
CONTENT_TYPES = {
    "page": "node--page",
    "facility": "node--facility",
    "personnel": "node--personnel",
    "procedure": "node--procedure",
    "region": "taxonomy_term--region",
    "menu": "menu_link_content--menu_link_content",
}

# Change tracking database (SQLite for simplicity)
CHANGE_TRACKING_DB = "content_changes.db"

# Webhook Configuration
WEBHOOK_SECRET = os.getenv("DRUPAL_WEBHOOK_SECRET", "")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "5000"))
WEBHOOK_ENABLED = os.getenv("WEBHOOK_ENABLED", "true").lower() == "true"
