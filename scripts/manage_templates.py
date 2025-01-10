#!/usr/bin/env python3
"""Script to manage email templates."""
import os
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

def validate_template(template_path: str) -> bool:
    """Validate a template file.
    
    Args:
        template_path: Path to template file
        
    Returns:
        bool: Whether template is valid
    """
    try:
        # Set up Jinja environment
        env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
        
        # Try to load and parse template
        template = env.get_template(os.path.basename(template_path))
        
        # Try to render with dummy data
        template.render(
            organization_name="Test Org",
            tier_name="Test Tier",
            amount=99.99,
            next_billing_date="2024-01-01",
            invoice_number="INV-001",
            payment_date="2024-01-01",
            retry_date="2024-01-01",
            metric="API Calls",
            current_usage=1000,
            limit=2000,
            percentage=50.0,
            recipient_email="test@example.com",
            unsubscribe_url="http://example.com/unsubscribe",
            dashboard_url="http://example.com/dashboard",
            billing_url="http://example.com/billing",
            usage_url="http://example.com/usage"
        )
        
        return True
    except Exception as e:
        print(f"Template validation failed: {str(e)}")
        return False

def backup_template(template_path: str) -> None:
    """Create a backup of a template file.
    
    Args:
        template_path: Path to template file
    """
    backup_path = f"{template_path}.bak"
    shutil.copy2(template_path, backup_path)
    print(f"Created backup: {backup_path}")

def list_templates() -> None:
    """List all email templates."""
    template_dir = Path("src/templates/email")
    
    print("\nAvailable templates:")
    for template in template_dir.glob("*.html"):
        is_valid = validate_template(str(template))
        status = "✅" if is_valid else "❌"
        print(f"{status} {template.name}")

def validate_all_templates() -> None:
    """Validate all email templates."""
    template_dir = Path("src/templates/email")
    
    print("\nValidating templates:")
    all_valid = True
    
    for template in template_dir.glob("*.html"):
        is_valid = validate_template(str(template))
        status = "✅" if is_valid else "❌"
        print(f"{status} {template.name}")
        
        if not is_valid:
            all_valid = False
    
    if all_valid:
        print("\nAll templates are valid!")
    else:
        print("\nSome templates have errors!")

def backup_all_templates() -> None:
    """Create backups of all email templates."""
    template_dir = Path("src/templates/email")
    
    print("\nBacking up templates:")
    for template in template_dir.glob("*.html"):
        backup_template(str(template))

def main() -> None:
    """Main function."""
    while True:
        print("\n=== Email Template Manager ===")
        print("1. List templates")
        print("2. Validate all templates")
        print("3. Backup all templates")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == "1":
            list_templates()
        elif choice == "2":
            validate_all_templates()
        elif choice == "3":
            backup_all_templates()
        elif choice == "4":
            print("\nGoodbye!")
            break
        else:
            print("\nInvalid choice!")

if __name__ == "__main__":
    main() 