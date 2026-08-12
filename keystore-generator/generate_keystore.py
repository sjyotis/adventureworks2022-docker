#!/usr/bin/env python3
"""
Automated Keystore Generator for DBeaver SQL Server Connection
This script creates a dummy Java keystore using Docker, displays connection details,
and automatically cleans up the container.
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def print_header():
    """Print a nice header"""
    print("\n" + "="*60)
    print("🔑 DBeaver SQL Server Keystore Generator")
    print("="*60 + "\n")

def check_docker():
    """Check if Docker is running"""
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def run_docker_compose():
    """Run docker compose to generate the keystore"""
    try:
        # Check if docker-compose file exists
        if not Path("docker-compose.yml").exists():
            print("❌ Error: docker-compose.yml not found in current directory")
            return False

        if not check_docker():
            print("❌ Docker is not running or not installed. Please start Docker first.")
            return False

        print("🐳 Starting keystore generation container...\n")

        # Try with docker-compose (V1) first, then docker compose (V2)
        compose_cmd = None
        for cmd in [["docker", "compose"], ["docker-compose"]]:
            try:
                subprocess.run(cmd + ["version"], capture_output=True, check=True)
                compose_cmd = cmd
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        if not compose_cmd:
            print("❌ Docker Compose not found. Please install Docker Compose.")
            return False

        # Run docker compose up
        result = subprocess.run(
            compose_cmd + ["up"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # Filter out pull progress lines for cleaner output
            output_lines = result.stdout.split('\n')
            filtered_output = []
            for line in output_lines:
                if not any(x in line for x in ['Pulling', 'Downloading', 'Extracting', 'Digest:', 'Status:']):
                    filtered_output.append(line)
            print('\n'.join(filtered_output))
            return True
        else:
            print("❌ Error running docker compose:")
            print(result.stderr)
            return False

    except FileNotFoundError:
        print("❌ Docker not found. Please ensure Docker is installed and running.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def cleanup_container():
    """Remove the container after generation"""
    try:
        print("\n🧹 Cleaning up container...")
        # Try both compose commands
        for cmd in [["docker", "compose"], ["docker-compose"]]:
            try:
                subprocess.run(
                    cmd + ["down"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print("✅ Container removed successfully!")
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        return False
    except Exception as e:
        print(f"⚠️ Warning: Could not remove container: {e}")
        return False

def display_connection_details():
    """Display DBeaver connection details"""
    current_dir = os.getcwd()
    keystore_path = Path(current_dir) / "dummy.jks"

    print("\n" + "="*60)
    print("📋 DBeaver Connection Configuration")
    print("="*60 + "\n")

    print("Add these properties to your DBeaver connection:\n")

    print("┌─────────────────────────────────────────────────┐")
    print("│ Property              │ Value                  │")
    print("├─────────────────────────────────────────────────┤")
    print(f"│ keyStoreAuthentication │ JavaKeyStorePassword  │")
    print(f"│ keyStoreLocation       │ {keystore_path} │")
    print(f"│ keyStoreSecret         │ dummy123               │")
    print(f"│ TrustServerCertificate │ true                   │")
    print("└─────────────────────────────────────────────────┘\n")

    print("🔑 Keystore password: dummy123")
    print(f"📂 Keystore location: {keystore_path}")
    print(f"✅ Keystore file exists: {keystore_path.exists()}\n")

    print("💡 Quick copy-paste values:")
    print(f"   keyStoreAuthentication=JavaKeyStorePassword")
    print(f"   keyStoreLocation={keystore_path}")
    print(f"   keyStoreSecret=dummy123")
    print(f"   TrustServerCertificate=true\n")

def verify_keystore():
    """Verify that the keystore file was created"""
    keystore_path = Path("dummy.jks")
    if keystore_path.exists():
        size = keystore_path.stat().st_size
        print(f"✅ Keystore verified: {keystore_path} ({size} bytes)")
        return True
    else:
        print("❌ Keystore file not found!")
        return False

def main():
    """Main execution flow"""
    print_header()

    # Check if keystore already exists
    if Path("dummy.jks").exists():
        print("ℹ️  Existing keystore found!")
        choice = input("Do you want to regenerate it? (y/N): ").lower()
        if choice != 'y':
            display_connection_details()
            sys.exit(0)
        print("\n🔄 Regenerating keystore...")

    # Generate the keystore
    if run_docker_compose():
        time.sleep(2)  # Wait for file system sync
        verify_keystore()
        display_connection_details()
    else:
        print("\n❌ Generation failed. Please check the errors above.")
        sys.exit(1)

    # Cleanup
    cleanup_container()

    print("\n" + "="*60)
    print("✨ All done! You can now configure DBeaver with the details above.")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user. Cleaning up...")
        cleanup_container()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        cleanup_container()
        sys.exit(1)
