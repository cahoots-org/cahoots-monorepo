"""Migration CLI tool."""
import os
import click
from tabulate import tabulate
from utils.migrations import MigrationManager

def get_manager() -> MigrationManager:
    """Get migration manager instance."""
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/postgres"
    )
    return MigrationManager(db_url)

@click.group()
def cli():
    """Database migration management tool."""
    pass

@cli.command()
@click.option("--message", "-m", required=True, help="Migration description")
@click.option("--no-autogenerate", is_flag=True, help="Create empty migration")
def create(message: str, no_autogenerate: bool):
    """Create a new migration."""
    manager = get_manager()
    revision = manager.create_migration(message, not no_autogenerate)
    
    if revision:
        click.echo(f"Created migration {revision}")
    else:
        click.echo("Failed to create migration", err=True)
        exit(1)

@cli.command()
@click.option("--target", "-t", default="head", help="Target revision")
def upgrade(target: str):
    """Upgrade database to target revision."""
    manager = get_manager()
    
    if manager.upgrade(target):
        click.echo("Upgrade successful")
    else:
        click.echo("Upgrade failed", err=True)
        exit(1)

@cli.command()
@click.argument("target")
def downgrade(target: str):
    """Downgrade database to target revision."""
    manager = get_manager()
    
    if manager.downgrade(target):
        click.echo("Downgrade successful")
    else:
        click.echo("Downgrade failed", err=True)
        exit(1)

@cli.command()
def status():
    """Show migration status."""
    manager = get_manager()
    status = manager.check_migration_status()
    
    if "error" in status:
        click.echo(f"Error: {status['error']}", err=True)
        exit(1)
    
    # Print status summary
    click.echo("\nMigration Status:")
    click.echo("-" * 50)
    click.echo(f"Current Revision: {status['current_revision']}")
    click.echo(f"Available Migrations: {status['available_migrations']}")
    click.echo(f"Pending Migrations: {status['pending_migrations']}")
    click.echo(f"Database is {'up to date' if status['is_latest'] else 'needs upgrade'}")
    
    # Print available migrations
    migrations = manager.get_available_migrations()
    if migrations:
        click.echo("\nAvailable Migrations:")
        click.echo("-" * 50)
        
        table = [[
            m["revision"],
            m["down_revision"] or "None",
            m["description"],
            m["created_date"].strftime("%Y-%m-%d %H:%M:%S")
        ] for m in migrations]
        
        headers = ["Revision", "Parent", "Description", "Created"]
        click.echo(tabulate(table, headers=headers, tablefmt="grid"))

@cli.command()
def verify():
    """Verify database connection and migration state."""
    manager = get_manager()
    
    if manager.verify_database():
        click.echo("Database verification successful")
    else:
        click.echo("Database verification failed", err=True)
        exit(1)

if __name__ == "__main__":
    cli() 