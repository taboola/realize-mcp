#!/usr/bin/env python3
"""
PyPI Deployment Script for Realize MCP Server
Handles versioning, building, and publishing to PyPI/TestPyPI
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from dotenv import load_dotenv
import re
import json

# Load environment variables
load_dotenv()

class DeploymentManager:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root or Path(__file__).parent.parent)
        self.pyproject_path = self.project_root / "pyproject.toml"
        self.version_file = self.project_root / "src" / "realize" / "_version.py"
        self.dist_dir = self.project_root / "dist"
        
        # Validate environment
        self.validate_environment()
    
    def validate_environment(self):
        """Validate required environment variables and tools"""
        required_env = ["PYPI_API_TOKEN", "TEST_PYPI_API_TOKEN"]
        missing = [var for var in required_env if not os.getenv(var)]
        
        if missing:
            print(f"❌ Missing environment variables: {', '.join(missing)}")
            print("Please check your .env file")
            sys.exit(1)
        
        # Check required tools
        required_tools = ["python3"]
        for tool in required_tools:
            if subprocess.run(["which", tool], capture_output=True).returncode != 0:
                print(f"❌ Required tool not found: {tool}")
                sys.exit(1)
        
        # Check pip via python3 -m pip
        if subprocess.run(["python3", "-m", "pip", "--version"], capture_output=True).returncode != 0:
            print("❌ pip not available via python3 -m pip")
            sys.exit(1)
        
        print("✅ Environment validation passed")
    
    def get_current_version(self):
        """Get current version from _version.py"""
        if not self.version_file.exists():
            return "0.0.0"
        
        with open(self.version_file) as f:
            content = f.read()
            match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            return match.group(1) if match else "0.0.0"
    
    def update_version(self, new_version):
        """Update version in _version.py and pyproject.toml"""
        # Update _version.py
        self.version_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.version_file, "w") as f:
            f.write(f'__version__ = "{new_version}"\n')
        
        # Update pyproject.toml
        if self.pyproject_path.exists():
            content = self.pyproject_path.read_text()
            content = re.sub(
                r'version\s*=\s*["\'][^"\']+["\']',
                f'version = "{new_version}"',
                content
            )
            self.pyproject_path.write_text(content)
        
        print(f"✅ Updated version to {new_version}")
    
    def clean_build(self):
        """Clean previous build artifacts"""
        import shutil
        
        dirs_to_clean = [self.dist_dir, "build", "*.egg-info"]
        for pattern in dirs_to_clean:
            if pattern == self.dist_dir:
                if self.dist_dir.exists():
                    shutil.rmtree(self.dist_dir)
            else:
                for path in self.project_root.glob(pattern):
                    if path.is_dir():
                        shutil.rmtree(path)
        
        print("✅ Cleaned build artifacts")
    
    def install_build_deps(self):
        """Install build dependencies"""
        subprocess.run([
            sys.executable, "-m", "pip", "install", "--upgrade",
            "build", "twine", "python-dotenv"
        ], check=True)
        print("✅ Installed build dependencies")
    
    def build_package(self):
        """Build the package"""
        subprocess.run([
            sys.executable, "-m", "build"
        ], cwd=self.project_root, check=True)
        print("✅ Package built successfully")
    
    def validate_package(self):
        """Validate built package"""
        subprocess.run([
            "twine", "check", "dist/*"
        ], cwd=self.project_root, check=True)
        print("✅ Package validation passed")
    
    def upload_to_testpypi(self):
        """Upload to TestPyPI"""
        env = os.environ.copy()
        env["TWINE_USERNAME"] = "__token__"
        env["TWINE_PASSWORD"] = os.getenv("TEST_PYPI_API_TOKEN")
        
        subprocess.run([
            "twine", "upload", "--repository", "testpypi", "dist/*"
        ], cwd=self.project_root, env=env, check=True)
        print("✅ Uploaded to TestPyPI")
    
    def upload_to_pypi(self):
        """Upload to production PyPI"""
        env = os.environ.copy()
        env["TWINE_USERNAME"] = "__token__"
        env["TWINE_PASSWORD"] = os.getenv("PYPI_API_TOKEN")
        
        subprocess.run([
            "twine", "upload", "dist/*"
        ], cwd=self.project_root, env=env, check=True)
        print("✅ Uploaded to PyPI")
    
    def run_tests(self):
        """Run test suite"""
        if (self.project_root / "pytest.ini").exists():
            result = subprocess.run([
                sys.executable, "-m", "pytest"
            ], cwd=self.project_root)
            
            if result.returncode != 0:
                print("❌ Tests failed")
                return False
            print("✅ Tests passed")
        else:
            print("⚠️ No tests found - skipping")
        return True
    
    def create_git_tag(self, version):
        """Create git tag for version"""
        try:
            subprocess.run([
                "git", "tag", f"v{version}"
            ], cwd=self.project_root, check=True)
            print(f"✅ Created git tag v{version}")
            
            # Ask if user wants to push tag
            response = input("Push tag to remote? (y/N): ")
            if response.lower() == 'y':
                subprocess.run([
                    "git", "push", "origin", f"v{version}"
                ], cwd=self.project_root, check=True)
                print("✅ Pushed tag to remote")
        except subprocess.CalledProcessError:
            print("⚠️ Git tag creation failed (may already exist)")

def main():
    parser = argparse.ArgumentParser(description="Deploy Realize MCP Server to PyPI")
    parser.add_argument("--version", help="New version number (e.g., 1.0.1)")
    parser.add_argument("--test-only", action="store_true", help="Only upload to TestPyPI")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--skip-git-tag", action="store_true", help="Skip creating git tag")
    
    args = parser.parse_args()
    
    dm = DeploymentManager()
    
    print("🚀 Starting deployment process...")
    
    # Get version
    current_version = dm.get_current_version()
    print(f"📦 Current version: {current_version}")
    
    if args.version:
        new_version = args.version
    else:
        new_version = input(f"Enter new version (current: {current_version}): ").strip()
        if not new_version:
            print("❌ Version required")
            sys.exit(1)
    
    # Validate version format
    if not re.match(r'^\d+\.\d+\.\d+', new_version):
        print("❌ Version must be in format X.Y.Z")
        sys.exit(1)
    
    print(f"🎯 Target version: {new_version}")
    
    try:
        # Run tests
        if not args.skip_tests:
            if not dm.run_tests():
                sys.exit(1)
        
        # Update version
        dm.update_version(new_version)
        
        # Clean and build
        dm.clean_build()
        dm.install_build_deps()
        dm.build_package()
        dm.validate_package()
        
        # Upload to TestPyPI first
        print("📤 Uploading to TestPyPI...")
        dm.upload_to_testpypi()
        
        # Test installation from TestPyPI
        package_name = os.getenv("PACKAGE_NAME", "realize-mcp")
        print(f"\n🧪 Test installation with:")
        print(f"pip install --index-url https://test.pypi.org/simple/ {package_name}=={new_version}")
        
        if not args.test_only:
            response = input("\n✅ TestPyPI upload successful. Continue to production PyPI? (y/N): ")
            if response.lower() == 'y':
                print("📤 Uploading to production PyPI...")
                dm.upload_to_pypi()
                
                if not args.skip_git_tag:
                    dm.create_git_tag(new_version)
                
                print(f"\n🎉 Successfully deployed version {new_version} to PyPI!")
                print(f"📦 Install with: pip install {package_name}=={new_version}")
            else:
                print("⏸️ Deployment stopped at TestPyPI")
        else:
            print("✅ TestPyPI-only deployment completed")
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏸️ Deployment cancelled by user")
        sys.exit(1)

if __name__ == "__main__":
    main() 