# Drupal Static CMS - Incremental Update System

A demonstration system for incrementally updating static website content when Drupal CMS content changes, designed to replace slow full-site regeneration with fast, targeted updates.

## Problem Statement

Traditional static site generation from Drupal has two main problems:

1. **Outdated technology** - Legacy generation systems are no longer well-supported
2. **Slow regeneration** - As content grows, complete site regeneration takes too long, creating unacceptable delays between content updates and publication

## Solution

This system implements incremental updates where:

- Individual content changes trigger regeneration of only affected pages
- A page update regenerates just that one page
- A facility update regenerates the facility page and any pages that reference it
- A menu update regenerates all pages using that menu

This reduces update time from hours to seconds while maintaining the same Drupal content types and website appearance.

## Architecture

### Components

1. **DrupalClient** (`drupal_client.py`)
   - Queries Drupal JSON:API for content changes
   - Detects which content items have been modified
   - Retrieves specific content by ID
   - Fetches menu structures

2. **DependencyMapper** (`dependency_mapper.py`)
   - Tracks which static pages depend on which Drupal content
   - Maps content changes to affected pages
   - Uses SQLite database for persistent tracking
   - Maintains processing state (what's been updated)

3. **PageGenerator** (`page_generator.py`)
   - Generates static HTML from Drupal content
   - Uses Jinja2 templates for different content types
   - Supports pages, facilities, personnel, and procedures
   - Includes menu in generated pages

4. **S3Uploader** (`s3_uploader.py`)
   - Uploads generated HTML to AWS S3
   - Manages public access and cache headers
   - Provides file management operations

5. **StaticSiteUpdater** (`main.py`)
   - Orchestrates the entire update process
   - Checks for content changes
   - Determines affected pages
   - Regenerates and uploads only what's needed

### Data Flow

```
Drupal Content Change
        ↓
DrupalClient detects change
        ↓
DependencyMapper identifies affected pages
        ↓
PageGenerator creates HTML for each page
        ↓
S3Uploader publishes to AWS S3
        ↓
DependencyMapper marks change as processed
```

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Edit `config.py` or set environment variables:

```python
# Drupal Configuration
DRUPAL_BASE_URL = 'https://your-drupal-site.com'

# AWS S3 Configuration
S3_BUCKET_NAME = 'your-bucket-name'
S3_REGION = 'us-east-1'
```

Environment variables:

```bash
export DRUPAL_BASE_URL=https://your-drupal-site.com
export S3_BUCKET_NAME=your-bucket-name
export S3_REGION=us-east-1
```

## Usage

### Basic Usage

Run the demonstration:

```bash
python main.py
```

This will:

1. Check for content changes in the last hour
2. Process any unprocessed content
3. Display examples of how different update scenarios work

### Check for Changes Since Specific Time

```python
from main import StaticSiteUpdater
from datetime import datetime, timedelta

updater = StaticSiteUpdater()

# Check for changes in last 24 hours
yesterday = datetime.now() - timedelta(days=1)
stats = updater.check_and_process_changes(since=yesterday)
print(f"Updated {stats['pages_updated']} pages")
```

### Process Specific Content Types

```python
from drupal_client import DrupalClient
from datetime import datetime, timedelta

client = DrupalClient()

# Get facility changes in last hour
one_hour_ago = datetime.now() - timedelta(hours=1)
changes = client.get_content_changes('node--facility', since=one_hour_ago)

for facility in changes:
    print(f"Facility changed: {facility['title']}")
```

### Manual Page Generation

```python
from drupal_client import DrupalClient
from page_generator import PageGenerator
from s3_uploader import S3Uploader

# Fetch content
client = DrupalClient()
content = client.get_content_by_id('node--page', 'some-uuid')

# Generate HTML
generator = PageGenerator()
html = generator.generate_page('node--page', content)

# Upload to S3
uploader = S3Uploader()
uploader.upload_html(html, 'pages/example.html')
```

## Content Type Mapping

The system handles these Drupal content types:

- **Pages** (`node--page`) → `/pages/{slug}.html`
- **Facilities** (`node--facility`) → `/facilities/{slug}.html`
- **Personnel** (`node--personnel`) → `/personnel/{slug}.html`
- **Procedures** (`node--procedure`) → `/procedures/{slug}.html`
- **Regions** (`taxonomy_term--region`) → Taxonomy used by other content
- **Menus** (`menu_link_content--menu_link_content`) → Navigation structure

## Dependency Tracking

The system automatically tracks:

1. **Primary dependencies**: The main content for a page
2. **Reference dependencies**: Content referenced by a page (e.g., a facility mentioned in a procedure)
3. **Menu dependencies**: Pages that use specific menus

When content changes:

- System queries the dependency database
- Identifies all affected pages
- Regenerates only those pages
- Updates tracking to prevent duplicate processing

## Database Schema

### content_tracking

Tracks when content items were last changed and processed:

```sql
content_type TEXT    -- e.g., 'node--page'
content_id TEXT      -- UUID
last_changed         -- When Drupal content was modified
last_processed       -- When we last generated pages for it
```

### content_dependencies

Maps content to pages that use it:

```sql
page_path TEXT       -- e.g., '/pages/about.html'
content_type TEXT    -- Type of dependent content
content_id TEXT      -- UUID of dependent content
dependency_type TEXT -- 'primary', 'reference', 'menu'
```

### static_pages

Tracks generated static pages:

```sql
page_path TEXT       -- Page path
last_generated       -- When HTML was generated
s3_key TEXT          -- Where it's stored in S3
```

## Update Scenarios

### Scenario 1: Single Page Update

```
Author updates "About Us" page in Drupal
        ↓
System detects change to node--page/uuid-123
        ↓
Identifies affected page: /pages/about-us.html
        ↓
Regenerates 1 page
        ↓
Uploads 1 file to S3
        ↓
Takes: ~2 seconds
```

### Scenario 2: Facility Update

```
Author updates "Memorial Hospital" facility
        ↓
System detects change to node--facility/uuid-456
        ↓
Identifies affected pages:
  - /facilities/memorial-hospital.html (detail page)
  - /facilities/index.html (directory)
  - /pages/locations.html (references it)
        ↓
Regenerates 3 pages
        ↓
Uploads 3 files to S3
        ↓
Takes: ~5 seconds
```

### Scenario 3: Menu Update

```
Author changes main navigation menu
        ↓
System detects change to menu item
        ↓
Identifies all pages using main menu (could be hundreds)
        ↓
Regenerates all affected pages
        ↓
Uploads all to S3
        ↓
Takes: minutes instead of hours
```

## Comparison with Full Regeneration

### Old Approach (Full Regeneration)

- Processes ALL content every time
- Takes hours for large sites
- High AWS costs (thousands of S3 operations)
- Delays between authoring and publication

### New Approach (Incremental)

- Processes ONLY changed content
- Takes seconds to minutes
- Lower AWS costs (minimal S3 operations)
- Near-instant publication

## Scheduling

Set up automated checks using cron or similar:

```bash
# Check for changes every 5 minutes
*/5 * * * * cd /path/to/drupal-static-cms && /path/to/venv/bin/python main.py

# Or use a more sophisticated scheduler
```

For production, consider:

- AWS Lambda triggered by EventBridge (scheduled)
- Drupal webhook calling your service
- Continuous polling service

## Testing Without Drupal/S3

The code includes safety checks:

- If S3 client can't initialize, it logs what would be uploaded without failing
- You can run the demonstration to see how the system works
- The components are independent and can be tested separately

## Extending the System

### Adding New Content Types

1. Add to `config.py`:

```python
CONTENT_TYPES = {
    # ... existing types ...
    'event': 'node--event'
}
```

2. Create template in `page_generator.py`:

```python
def _get_default_event_template(self) -> str:
    return """..."""
```

3. Add URL mapping in `main.py`:

```python
elif type_name == 'event':
    return f"/events/{slug}.html"
```

### Custom Templates

Create a `templates/` directory with Jinja2 templates:

```
templates/
  page.html
  facility.html
  personnel.html
  procedure.html
```

The PageGenerator will automatically use these instead of inline templates.

## Performance Optimization

For high-volume sites:

1. **Batch processing**: Queue changes and process in batches
2. **Parallel generation**: Generate multiple pages concurrently
3. **CloudFront invalidation**: Invalidate CDN cache for changed pages only
4. **Incremental dependency updates**: Only recalculate dependencies when relationships change

## Monitoring

Track these metrics:

- Number of content changes per hour
- Average pages affected per change
- Generation time per page
- S3 upload success rate
- Time from Drupal update to S3 publication

## License

This is demonstration code for educational purposes.

## Author

Created to solve the problem of slow static site generation from Drupal CMS.
