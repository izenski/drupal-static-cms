"""Static page generator for creating HTML from Drupal content."""

import os
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader, Template


class PageGenerator:
    """Generates static HTML pages from Drupal content."""
    
    def __init__(self, template_dir: str = None):
        """Initialize the page generator.
        
        Args:
            template_dir: Directory containing Jinja2 templates
        """
        self.template_dir = template_dir or self._get_default_template_dir()
        
        # Set up Jinja2 environment
        if os.path.exists(self.template_dir):
            self.env = Environment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=True
            )
        else:
            # Use inline templates if directory doesn't exist
            self.env = Environment(autoescape=True)
            self._create_default_templates()
    
    def _get_default_template_dir(self) -> str:
        """Get default template directory."""
        return os.path.join(os.path.dirname(__file__), 'templates')
    
    def _create_default_templates(self):
        """Create default inline templates."""
        # These are simple default templates for demonstration
        self.templates = {
            'page': self._get_default_page_template(),
            'facility': self._get_default_facility_template(),
            'personnel': self._get_default_personnel_template(),
            'procedure': self._get_default_procedure_template()
        }
    
    def _get_default_page_template(self) -> str:
        """Get default page template."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Hospital System</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    {% if menu %}
    <nav class="main-nav">
        <ul>
        {% for item in menu %}
            <li><a href="{{ item.url }}">{{ item.title }}</a></li>
        {% endfor %}
        </ul>
    </nav>
    {% endif %}
    
    <main>
        <article>
            <h1>{{ title }}</h1>
            {% if created %}
            <p class="meta">Published: {{ created }}</p>
            {% endif %}
            <div class="content">
                {{ body|safe }}
            </div>
        </article>
    </main>
    
    <footer>
        <p>&copy; 2026 National Hospital System</p>
    </footer>
</body>
</html>"""
    
    def _get_default_facility_template(self) -> str:
        """Get default facility template."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ name }} - Hospital Facilities</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    {% if menu %}
    <nav class="main-nav">
        <ul>
        {% for item in menu %}
            <li><a href="{{ item.url }}">{{ item.title }}</a></li>
        {% endfor %}
        </ul>
    </nav>
    {% endif %}
    
    <main>
        <article class="facility">
            <h1>{{ name }}</h1>
            
            {% if address %}
            <div class="address">
                <h2>Location</h2>
                <p>{{ address }}</p>
            </div>
            {% endif %}
            
            {% if phone %}
            <div class="contact">
                <h2>Contact</h2>
                <p>Phone: {{ phone }}</p>
            </div>
            {% endif %}
            
            {% if services %}
            <div class="services">
                <h2>Services</h2>
                <ul>
                {% for service in services %}
                    <li>{{ service }}</li>
                {% endfor %}
                </ul>
            </div>
            {% endif %}
            
            {% if region %}
            <div class="region">
                <p>Region: {{ region }}</p>
            </div>
            {% endif %}
        </article>
    </main>
    
    <footer>
        <p>&copy; 2026 National Hospital System</p>
    </footer>
</body>
</html>"""
    
    def _get_default_personnel_template(self) -> str:
        """Get default personnel template."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ name }} - Medical Personnel</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    {% if menu %}
    <nav class="main-nav">
        <ul>
        {% for item in menu %}
            <li><a href="{{ item.url }}">{{ item.title }}</a></li>
        {% endfor %}
        </ul>
    </nav>
    {% endif %}
    
    <main>
        <article class="personnel">
            <h1>{{ name }}</h1>
            
            {% if title %}
            <p class="job-title">{{ title }}</p>
            {% endif %}
            
            {% if specialties %}
            <div class="specialties">
                <h2>Specialties</h2>
                <ul>
                {% for specialty in specialties %}
                    <li>{{ specialty }}</li>
                {% endfor %}
                </ul>
            </div>
            {% endif %}
            
            {% if bio %}
            <div class="bio">
                <h2>Biography</h2>
                <p>{{ bio }}</p>
            </div>
            {% endif %}
        </article>
    </main>
    
    <footer>
        <p>&copy; 2026 National Hospital System</p>
    </footer>
</body>
</html>"""
    
    def _get_default_procedure_template(self) -> str:
        """Get default procedure template."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ name }} - Medical Procedures</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    {% if menu %}
    <nav class="main-nav">
        <ul>
        {% for item in menu %}
            <li><a href="{{ item.url }}">{{ item.title }}</a></li>
        {% endfor %}
        </ul>
    </nav>
    {% endif %}
    
    <main>
        <article class="procedure">
            <h1>{{ name }}</h1>
            
            {% if description %}
            <div class="description">
                <h2>Description</h2>
                <p>{{ description }}</p>
            </div>
            {% endif %}
            
            {% if preparation %}
            <div class="preparation">
                <h2>Preparation</h2>
                <p>{{ preparation }}</p>
            </div>
            {% endif %}
            
            {% if recovery %}
            <div class="recovery">
                <h2>Recovery</h2>
                <p>{{ recovery }}</p>
            </div>
            {% endif %}
        </article>
    </main>
    
    <footer>
        <p>&copy; 2026 National Hospital System</p>
    </footer>
</body>
</html>"""
    
    def generate_page(self, content_type: str, content: Dict, 
                     menu: List[Dict] = None) -> str:
        """Generate HTML for a page.
        
        Args:
            content_type: Type of content (page, facility, etc.)
            content: Content data from Drupal
            menu: Optional menu structure
            
        Returns:
            Generated HTML string
        """
        # Determine which template to use
        template_name = self._get_template_name(content_type)
        
        # Prepare template context
        context = self._prepare_context(content, menu)
        
        # Render template
        try:
            if hasattr(self, 'templates'):
                # Using inline templates
                template = Template(self.templates.get(template_name, self.templates['page']))
            else:
                # Using file-based templates
                template = self.env.get_template(f"{template_name}.html")
            
            return template.render(**context)
        except Exception as e:
            print(f"Error generating page: {e}")
            return self._generate_error_page(content.get('title', 'Error'))
    
    def _get_template_name(self, content_type: str) -> str:
        """Determine template name from content type.
        
        Args:
            content_type: Drupal content type
            
        Returns:
            Template name
        """
        # Extract simple name from Drupal type (e.g., 'node--page' -> 'page')
        if '--' in content_type:
            return content_type.split('--')[1]
        return 'page'
    
    def _prepare_context(self, content: Dict, menu: List[Dict] = None) -> Dict:
        """Prepare template context from content data.
        
        Args:
            content: Content data
            menu: Menu structure
            
        Returns:
            Template context dictionary
        """
        attributes = content.get('attributes', {})
        
        context = {
            'title': content.get('title', 'Untitled'),
            'created': content.get('created'),
            'changed': content.get('changed'),
            'menu': menu or []
        }
        
        # Add type-specific fields
        if 'body' in attributes:
            # Handle Drupal's body field structure
            body = attributes['body']
            if isinstance(body, dict):
                context['body'] = body.get('value', '')
            elif isinstance(body, list) and len(body) > 0:
                context['body'] = body[0].get('value', '')
            else:
                context['body'] = str(body)
        
        # Add all attributes to context for flexibility
        context.update(attributes)
        
        # Handle facility-specific fields
        if 'field_address' in attributes:
            context['address'] = attributes['field_address']
        if 'field_phone' in attributes:
            context['phone'] = attributes['field_phone']
        if 'field_services' in attributes:
            context['services'] = attributes['field_services']
        
        # Handle personnel-specific fields
        if 'field_specialties' in attributes:
            context['specialties'] = attributes['field_specialties']
        if 'field_bio' in attributes:
            context['bio'] = attributes['field_bio']
        
        # Handle procedure-specific fields
        if 'field_description' in attributes:
            context['description'] = attributes['field_description']
        if 'field_preparation' in attributes:
            context['preparation'] = attributes['field_preparation']
        if 'field_recovery' in attributes:
            context['recovery'] = attributes['field_recovery']
        
        # Use 'name' field for non-page content if available
        if 'name' in attributes and 'title' not in context:
            context['name'] = attributes['name']
        elif 'title' in context:
            context['name'] = context['title']
        
        return context
    
    def _generate_error_page(self, title: str = "Error") -> str:
        """Generate a simple error page.
        
        Args:
            title: Page title
            
        Returns:
            HTML error page
        """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
</head>
<body>
    <h1>Error Generating Page</h1>
    <p>Sorry, there was an error generating this page.</p>
</body>
</html>"""
</html>"""
