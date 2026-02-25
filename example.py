"""
Example script demonstrating the incremental Drupal static site update system.

This script shows how to use each component individually and demonstrates
the key concepts of detecting content changes and mapping them to affected pages.
"""

from datetime import datetime, timedelta

import config
from dependency_mapper import DependencyMapper
from drupal_client import DrupalClient
from page_generator import PageGenerator
from s3_uploader import S3Uploader


def example_1_detect_content_changes():
    """Example 1: Detect when Drupal content has changed."""
    print("\n" + "=" * 60)
    print("Example 1: Detecting Content Changes")
    print("=" * 60)

    client = DrupalClient()

    # Check for page changes in the last 24 hours
    yesterday = datetime.now() - timedelta(days=1)

    print(f"\nChecking for pages changed since: {yesterday}")
    changes = client.get_content_changes(config.CONTENT_TYPES["page"], since=yesterday)

    print(f"Found {len(changes)} changed pages")
    for change in changes[:5]:  # Show first 5
        print(f"  - {change['title']} (changed: {change['changed']})")

    # Check for facility changes
    print(f"\nChecking for facilities changed since: {yesterday}")
    facility_changes = client.get_content_changes(
        config.CONTENT_TYPES["facility"], since=yesterday
    )

    print(f"Found {len(facility_changes)} changed facilities")
    for change in facility_changes[:5]:
        print(f"  - {change['title']} (changed: {change['changed']})")


def example_2_map_dependencies():
    """Example 2: Map content to affected pages."""
    print("\n" + "=" * 60)
    print("Example 2: Mapping Content Dependencies")
    print("=" * 60)

    mapper = DependencyMapper()

    # Simulate adding dependencies for a facility page
    facility_id = "example-facility-uuid-123"
    facility_type = config.CONTENT_TYPES["facility"]

    print("\nAdding dependencies for Memorial Hospital facility:")

    # The facility detail page depends on the facility content
    mapper.add_dependency(
        "/facilities/memorial-hospital.html", facility_type, facility_id, "primary"
    )
    print("  - Added primary dependency: /facilities/memorial-hospital.html")

    # The facilities index page also depends on this facility
    mapper.add_dependency(
        "/facilities/index.html", facility_type, facility_id, "reference"
    )
    print("  - Added reference dependency: /facilities/index.html")

    # A locations page references this facility
    mapper.add_dependency(
        "/pages/locations.html", facility_type, facility_id, "reference"
    )
    print("  - Added reference dependency: /pages/locations.html")

    # Now check which pages are affected by this facility
    print(f"\nPages affected by facility {facility_id}:")
    affected = mapper.get_affected_pages(facility_type, facility_id)
    for page in affected:
        print(f"  - {page}")

    print(f"\nTotal pages that need regeneration: {len(affected)}")


def example_3_generate_static_page():
    """Example 3: Generate static HTML from content."""
    print("\n" + "=" * 60)
    print("Example 3: Generating Static HTML")
    print("=" * 60)

    generator = PageGenerator()

    # Create sample content data (simulating what comes from Drupal)
    sample_facility = {
        "id": "facility-123",
        "type": "node--facility",
        "title": "Memorial Hospital",
        "created": datetime.now(),
        "changed": datetime.now(),
        "attributes": {
            "name": "Memorial Hospital",
            "field_address": "123 Medical Drive, Health City, HC 12345",
            "field_phone": "(555) 123-4567",
            "field_services": ["Emergency Care", "Surgery", "Pediatrics", "Cardiology"],
            "field_region": "Northeast",
        },
    }

    # Generate HTML
    print("\nGenerating HTML for Memorial Hospital facility...")
    html = generator.generate_page("node--facility", sample_facility)

    # Show first 500 characters
    print("\nGenerated HTML (first 500 chars):")
    print("-" * 60)
    print(html[:500] + "...")
    print("-" * 60)

    print(f"\nTotal HTML length: {len(html)} bytes")


def example_4_upload_to_s3():
    """Example 4: Upload content to S3."""
    print("\n" + "=" * 60)
    print("Example 4: Uploading to S3")
    print("=" * 60)

    uploader = S3Uploader()

    # Sample HTML content
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Example Page</title>
</head>
<body>
    <h1>Example Static Page</h1>
    <p>This page was generated incrementally.</p>
</body>
</html>"""

    s3_key = "example/test-page.html"

    print(f"\nUploading HTML to S3...")
    print(f"  Bucket: {uploader.bucket_name}")
    print(f"  Key: {s3_key}")

    success = uploader.upload_html(html_content, s3_key)

    if success:
        url = uploader.get_public_url(s3_key)
        print(f"\n✓ Upload successful!")
        print(f"  Public URL: {url}")
    else:
        print(f"\n✗ Upload not completed (S3 client not configured)")
        print(f"  Would upload to: s3://{uploader.bucket_name}/{s3_key}")


def example_5_incremental_update_workflow():
    """Example 5: Complete incremental update workflow."""
    print("\n" + "=" * 60)
    print("Example 5: Complete Incremental Update Workflow")
    print("=" * 60)

    # Simulate a complete workflow
    print("\nScenario: Author updates a hospital facility in Drupal")
    print("-" * 60)

    # Step 1: Detect the change
    print("\nStep 1: Detecting changes...")
    print("  Query Drupal JSON:API for content changed in last hour")
    print("  Result: Found 1 facility changed (Memorial Hospital)")

    # Step 2: Map to affected pages
    print("\nStep 2: Mapping dependencies...")
    mapper = DependencyMapper()
    facility_id = "facility-123"
    facility_type = config.CONTENT_TYPES["facility"]

    affected_pages = mapper.get_affected_pages(facility_type, facility_id)
    if not affected_pages:
        # Simulate having dependencies
        affected_pages = {
            "/facilities/memorial-hospital.html",
            "/facilities/index.html",
            "/pages/locations.html",
        }

    print(f"  Result: Found {len(affected_pages)} affected pages:")
    for page in affected_pages:
        print(f"    - {page}")

    # Step 3: Generate static HTML
    print("\nStep 3: Generating static pages...")
    generator = PageGenerator()

    sample_content = {
        "id": facility_id,
        "type": facility_type,
        "title": "Memorial Hospital",
        "attributes": {
            "name": "Memorial Hospital",
            "field_address": "123 Medical Drive",
            "field_services": ["Emergency", "Surgery"],
        },
    }

    for page in affected_pages:
        html = generator.generate_page(facility_type, sample_content)
        print(f"    ✓ Generated {page} ({len(html)} bytes)")

    # Step 4: Upload to S3
    print("\nStep 4: Uploading to S3...")
    uploader = S3Uploader()

    for page in affected_pages:
        s3_key = page.lstrip("/")
        print(f"    → Uploading {s3_key}")

    # Step 5: Mark as processed
    print("\nStep 5: Marking content as processed...")
    mapper.mark_content_processed(facility_type, facility_id)
    print("    ✓ Content marked as processed")

    print("\n" + "=" * 60)
    print("✓ Incremental update complete!")
    print("=" * 60)
    print(f"\nTime saved vs full regeneration:")
    print(f"  Old approach: ~2 hours (regenerate all 10,000 pages)")
    print(f"  New approach: ~5 seconds (regenerate 3 affected pages)")
    print(f"  Time saved: 99.9%")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print(" Drupal Static CMS - Incremental Update System Examples")
    print("=" * 70)

    print("\nNOTE: These examples demonstrate the system components.")
    print("Some examples may show simulated data if Drupal/S3 are not configured.")

    try:
        example_1_detect_content_changes()
    except Exception as e:
        print(f"\nExample 1 error (expected if Drupal not configured): {e}")

    example_2_map_dependencies()
    example_3_generate_static_page()

    try:
        example_4_upload_to_s3()
    except Exception as e:
        print(f"\nExample 4 error (expected if S3 not configured): {e}")

    example_5_incremental_update_workflow()

    print("\n" + "=" * 70)
    print(" Examples Complete")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Configure Drupal API endpoint in config.py")
    print("  2. Configure AWS S3 credentials and bucket")
    print("  3. Run: python main.py")
    print("  4. Set up scheduled checks (cron, Lambda, etc.)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
    main()
