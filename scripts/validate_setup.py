#!/usr/bin/env python3
"""
Project Setup Validator for Kapital Bank AI Assistant
Validates that all components are properly configured and working
"""

import os
import sys
import json
import asyncio
import importlib.util
from pathlib import Path
from typing import List, Dict, Any, Tuple
import subprocess

class SetupValidator:
    """Validates complete project setup"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.issues = []
        self.warnings = []
        self.passed_checks = []
        
        # Required files and directories
        self.required_files = [
            ".env.example",
            "requirements.txt", 
            "main.py",
            "models.py",
            "database.py",
            "mcp_client.py",
            "run.py",
            "Dockerfile",
            "docker-compose.yml",
            "Makefile",
            "README.md"
        ]
        
        self.required_dirs = [
            "mcp-servers",
            "scripts",
            "templates",
            "static",
            "static/css",
            "static/js",
            "static/favicon_io"
        ]
        
        self.required_scripts = [
            "scripts/init_db.py",
            "scripts/test_apis.py",
            "scripts/health_check.py"
        ]
        
        self.required_templates = [
            "templates/base.html",
            "templates/index.html",
            "templates/chat.html",
            "templates/currency.html",
            "templates/locations.html"
        ]
        
        self.required_static = [
            "static/css/styles.css",
            "static/js/app.js",
            "static/sw.js"
        ]
        
        self.mcp_servers = [
            "mcp-servers/__init__.py",
            "mcp-servers/kapital_bank_server.py",
            "mcp-servers/currency_server.py"
        ]
    
    def print_status(self, check_name: str, status: str, details: str = ""):
        """Print formatted check status"""
        icons = {"pass": "✅", "fail": "❌", "warning": "⚠️", "info": "ℹ️"}
        icon = icons.get(status, "❓")
        print(f"{icon} {check_name}")
        if details:
            print(f"   {details}")
    
    def check_file_structure(self) -> bool:
        """Check if all required files and directories exist"""
        print("\n📁 Checking File Structure...")
        all_good = True
        
        # Check required files
        for file_path in self.required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                self.print_status(f"File: {file_path}", "pass")
                self.passed_checks.append(f"File exists: {file_path}")
            else:
                self.print_status(f"File: {file_path}", "fail", "Missing required file")
                self.issues.append(f"Missing required file: {file_path}")
                all_good = False
        
        # Check required directories
        for dir_path in self.required_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists() and full_path.is_dir():
                self.print_status(f"Directory: {dir_path}", "pass")
                self.passed_checks.append(f"Directory exists: {dir_path}")
            else:
                self.print_status(f"Directory: {dir_path}", "fail", "Missing required directory")
                self.issues.append(f"Missing required directory: {dir_path}")
                all_good = False
        
        return all_good
    
    def check_python_files(self) -> bool:
        """Check if Python files are valid and importable"""
        print("\n🐍 Checking Python Files...")
        all_good = True
        
        python_files = [
            "main.py", "models.py", "database.py", "mcp_client.py", "run.py"
        ] + self.required_scripts + self.mcp_servers
        
        for file_path in python_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue
                
            try:
                # Check syntax by attempting to compile
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                compile(content, str(full_path), 'exec')
                self.print_status(f"Python: {file_path}", "pass", "Syntax OK")
                self.passed_checks.append(f"Python syntax valid: {file_path}")
                
            except SyntaxError as e:
                self.print_status(f"Python: {file_path}", "fail", f"Syntax error: {e}")
                self.issues.append(f"Python syntax error in {file_path}: {e}")
                all_good = False
            except Exception as e:
                self.print_status(f"Python: {file_path}", "warning", f"Could not validate: {e}")
                self.warnings.append(f"Could not validate {file_path}: {e}")
        
        return all_good
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        print("\n📦 Checking Dependencies...")
        all_good = True
        
        # Core dependencies
        core_deps = [
            'fastapi', 'uvicorn', 'aiohttp', 'jinja2', 
            'google.generativeai', 'pydantic', 'asyncpg'
        ]
        
        for dep in core_deps:
            try:
                if '.' in dep:
                    # Handle nested imports like google.generativeai
                    parts = dep.split('.')
                    module = __import__(parts[0])
                    for part in parts[1:]:
                        module = getattr(module, part)
                else:
                    __import__(dep)
                
                self.print_status(f"Dependency: {dep}", "pass")
                self.passed_checks.append(f"Dependency available: {dep}")
                
            except ImportError:
                self.print_status(f"Dependency: {dep}", "fail", "Not installed")
                self.issues.append(f"Missing dependency: {dep}")
                all_good = False
            except Exception as e:
                self.print_status(f"Dependency: {dep}", "warning", f"Import issue: {e}")
                self.warnings.append(f"Dependency {dep} import issue: {e}")
        
        return all_good
    
    def check_environment(self) -> bool:
        """Check environment configuration"""
        print("\n🌍 Checking Environment...")
        all_good = True
        
        # Check .env.example exists
        env_example = self.project_root / ".env.example"
        if env_example.exists():
            self.print_status("Environment: .env.example", "pass")
            self.passed_checks.append("Environment template exists")
        else:
            self.print_status("Environment: .env.example", "fail", "Template missing")
            self.issues.append("Missing .env.example template")
            all_good = False
        
        # Check .env file
        env_file = self.project_root / ".env"
        if env_file.exists():
            self.print_status("Environment: .env", "pass")
            self.passed_checks.append("Environment file exists")
            
            # Check for required environment variables
            required_vars = ['GEMINI_API_KEY', 'DATABASE_URL']
            
            from dotenv import load_dotenv
            load_dotenv(env_file)
            
            for var in required_vars:
                if os.getenv(var):
                    self.print_status(f"Environment: {var}", "pass", "Set")
                    self.passed_checks.append(f"Environment variable set: {var}")
                else:
                    self.print_status(f"Environment: {var}", "warning", "Not set")
                    self.warnings.append(f"Environment variable not set: {var}")
        
        else:
            self.print_status("Environment: .env", "warning", "Copy .env.example to .env")
            self.warnings.append("No .env file found - copy .env.example to .env")
        
        return all_good
    
    def check_static_files(self) -> bool:
        """Check static files and assets"""
        print("\n🎨 Checking Static Files...")
        all_good = True
        
        for file_path in self.required_static:
            full_path = self.project_root / file_path
            if full_path.exists():
                self.print_status(f"Static: {file_path}", "pass")
                self.passed_checks.append(f"Static file exists: {file_path}")
            else:
                self.print_status(f"Static: {file_path}", "fail", "Missing static file")
                self.issues.append(f"Missing static file: {file_path}")
                all_good = False
        
        # Check favicon files
        favicon_dir = self.project_root / "static" / "favicon_io"
        if favicon_dir.exists():
            favicon_files = ["favicon.ico", "android-chrome-192x192.png", "site.webmanifest"]
            for favicon in favicon_files:
                favicon_path = favicon_dir / favicon
                if favicon_path.exists():
                    self.print_status(f"Favicon: {favicon}", "pass")
                    self.passed_checks.append(f"Favicon exists: {favicon}")
                else:
                    self.print_status(f"Favicon: {favicon}", "warning", "Missing favicon file")
                    self.warnings.append(f"Missing favicon: {favicon}")
        
        return all_good
    
    def check_templates(self) -> bool:
        """Check template files"""
        print("\n📄 Checking Templates...")
        all_good = True
        
        for template_path in self.required_templates:
            full_path = self.project_root / template_path
            if full_path.exists():
                # Check if it's a valid HTML file (basic check)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Basic HTML validation
                    if '<html' in content or '<!DOCTYPE' in content or '{% extends' in content:
                        self.print_status(f"Template: {template_path}", "pass")
                        self.passed_checks.append(f"Template valid: {template_path}")
                    else:
                        self.print_status(f"Template: {template_path}", "warning", "Might not be valid HTML")
                        self.warnings.append(f"Template might be invalid: {template_path}")
                
                except Exception as e:
                    self.print_status(f"Template: {template_path}", "warning", f"Could not validate: {e}")
                    self.warnings.append(f"Could not validate template {template_path}: {e}")
            else:
                self.print_status(f"Template: {template_path}", "fail", "Missing template")
                self.issues.append(f"Missing template: {template_path}")
                all_good = False
        
        return all_good
    
    def check_docker_setup(self) -> bool:
        """Check Docker configuration"""
        print("\n🐳 Checking Docker Setup...")
        all_good = True
        
        # Check Dockerfile
        dockerfile = self.project_root / "Dockerfile"
        if dockerfile.exists():
            self.print_status("Docker: Dockerfile", "pass")
            self.passed_checks.append("Dockerfile exists")
        else:
            self.print_status("Docker: Dockerfile", "fail", "Missing Dockerfile")
            self.issues.append("Missing Dockerfile")
            all_good = False
        
        # Check docker-compose.yml
        compose_file = self.project_root / "docker-compose.yml"
        if compose_file.exists():
            self.print_status("Docker: docker-compose.yml", "pass")
            self.passed_checks.append("Docker Compose file exists")
            
            # Basic YAML validation
            try:
                import yaml
                with open(compose_file, 'r') as f:
                    yaml.safe_load(f)
                self.print_status("Docker: YAML syntax", "pass")
                self.passed_checks.append("Docker Compose YAML valid")
            except ImportError:
                self.print_status("Docker: YAML syntax", "warning", "PyYAML not available for validation")
                self.warnings.append("Could not validate YAML - PyYAML not installed")
            except Exception as e:
                self.print_status("Docker: YAML syntax", "fail", f"Invalid YAML: {e}")
                self.issues.append(f"Invalid Docker Compose YAML: {e}")
                all_good = False
        else:
            self.print_status("Docker: docker-compose.yml", "fail", "Missing docker-compose.yml")
            self.issues.append("Missing docker-compose.yml")
            all_good = False
        
        # Check if Docker is available (optional)
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.print_status("Docker: Installation", "pass", result.stdout.strip())
                self.passed_checks.append("Docker is available")
            else:
                self.print_status("Docker: Installation", "warning", "Docker not available")
                self.warnings.append("Docker not available - install for containerization")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.print_status("Docker: Installation", "warning", "Docker not available")
            self.warnings.append("Docker not available - install for containerization")
        
        return all_good
    
    def check_project_structure(self) -> bool:
        """Check overall project structure"""
        print("\n🏗️  Checking Project Structure...")
        all_good = True
        
        # Check if this looks like a proper Python project
        if (self.project_root / "__init__.py").exists():
            self.print_status("Project: Package structure", "pass", "Python package")
            self.passed_checks.append("Proper Python package structure")
        else:
            self.print_status("Project: Package structure", "info", "Application (not package)")
        
        # Check for common project files
        project_files = {
            "README.md": "Documentation",
            "LICENSE": "License file",
            ".gitignore": "Git ignore rules",
            "Makefile": "Build automation"
        }
        
        for file_name, description in project_files.items():
            if (self.project_root / file_name).exists():
                self.print_status(f"Project: {file_name}", "pass", description)
                self.passed_checks.append(f"Project file exists: {file_name}")
            else:
                self.print_status(f"Project: {file_name}", "warning", f"Missing {description.lower()}")
                self.warnings.append(f"Missing {file_name}")
        
        return all_good
    
    async def check_runtime_functionality(self) -> bool:
        """Check if the application can actually start (basic test)"""
        print("\n🚀 Checking Runtime Functionality...")
        all_good = True
        
        try:
            # Try to import main modules
            sys.path.insert(0, str(self.project_root))
            
            # Test database module
            try:
                import database
                self.print_status("Runtime: Database module", "pass")
                self.passed_checks.append("Database module imports successfully")
            except Exception as e:
                self.print_status("Runtime: Database module", "fail", str(e))
                self.issues.append(f"Database module import error: {e}")
                all_good = False
            
            # Test models module
            try:
                import models
                self.print_status("Runtime: Models module", "pass")
                self.passed_checks.append("Models module imports successfully")
            except Exception as e:
                self.print_status("Runtime: Models module", "fail", str(e))
                self.issues.append(f"Models module import error: {e}")
                all_good = False
            
            # Test MCP client
            try:
                import mcp_client
                self.print_status("Runtime: MCP Client", "pass")
                self.passed_checks.append("MCP Client imports successfully")
            except Exception as e:
                self.print_status("Runtime: MCP Client", "fail", str(e))
                self.issues.append(f"MCP Client import error: {e}")
                all_good = False
            
            # Test main application
            try:
                import main
                self.print_status("Runtime: Main application", "pass")
                self.passed_checks.append("Main application imports successfully")
            except Exception as e:
                self.print_status("Runtime: Main application", "fail", str(e))
                self.issues.append(f"Main application import error: {e}")
                all_good = False
        
        except Exception as e:
            self.print_status("Runtime: General", "fail", f"Runtime check failed: {e}")
            self.issues.append(f"Runtime check failed: {e}")
            all_good = False
        
        finally:
            # Clean up sys.path
            if str(self.project_root) in sys.path:
                sys.path.remove(str(self.project_root))
        
        return all_good
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive validation report"""
        total_checks = len(self.passed_checks) + len(self.issues) + len(self.warnings)
        
        report = {
            "validation_summary": {
                "total_checks": total_checks,
                "passed": len(self.passed_checks),
                "failed": len(self.issues),
                "warnings": len(self.warnings),
                "success_rate": (len(self.passed_checks) / total_checks * 100) if total_checks > 0 else 0
            },
            "passed_checks": self.passed_checks,
            "issues": self.issues,
            "warnings": self.warnings,
            "recommendations": []
        }
        
        # Add recommendations based on issues
        if self.issues:
            report["recommendations"].append("Fix all critical issues before deployment")
        
        if self.warnings:
            report["recommendations"].append("Review and address warnings for optimal setup")
        
        if not any("GEMINI_API_KEY" in warning for warning in self.warnings):
            report["recommendations"].append("Ensure GEMINI_API_KEY is set for AI functionality")
        
        if not any("Docker" in check for check in self.passed_checks):
            report["recommendations"].append("Install Docker for containerized deployment")
        
        return report
    
    def print_summary(self, report: Dict[str, Any]):
        """Print validation summary"""
        print("\n" + "="*60)
        print("📊 SETUP VALIDATION SUMMARY")
        print("="*60)
        
        summary = report["validation_summary"]
        success_rate = summary["success_rate"]
        
        if success_rate >= 90:
            status_icon = "✅"
            status_text = "EXCELLENT"
            status_color = "\033[92m"  # Green
        elif success_rate >= 75:
            status_icon = "⚠️"
            status_text = "GOOD"
            status_color = "\033[93m"  # Yellow
        elif success_rate >= 50:
            status_icon = "⚠️"
            status_text = "NEEDS WORK"
            status_color = "\033[93m"  # Yellow
        else:
            status_icon = "❌"
            status_text = "CRITICAL ISSUES"
            status_color = "\033[91m"  # Red
        
        reset_color = "\033[0m"
        
        print(f"{status_icon} Overall Status: {status_color}{status_text}{reset_color}")
        print(f"   • Total Checks: {summary['total_checks']}")
        print(f"   • Passed: {summary['passed']}")
        print(f"   • Failed: {summary['failed']}")
        print(f"   • Warnings: {summary['warnings']}")
        print(f"   • Success Rate: {success_rate:.1f}%")
        
        if report["issues"]:
            print(f"\n❌ Critical Issues ({len(report['issues'])}):")
            for issue in report["issues"]:
                print(f"   • {issue}")
        
        if report["warnings"]:
            print(f"\n⚠️  Warnings ({len(report['warnings'])}):")
            for warning in report["warnings"]:
                print(f"   • {warning}")
        
        if report["recommendations"]:
            print(f"\n💡 Recommendations:")
            for rec in report["recommendations"]:
                print(f"   • {rec}")
        
        print(f"\n🚀 Next Steps:")
        if report["issues"]:
            print("   1. Fix all critical issues listed above")
            print("   2. Re-run validation: python scripts/validate_setup.py")
        else:
            print("   1. Initialize database: python scripts/init_db.py")
            print("   2. Start application: python run.py")
            print("   3. Visit: http://localhost:8000")
        
        print("\n📖 For help, see README.md or run: make help")

async def main():
    """Main validation function"""
    print("🏛️ Kapital Bank AI Assistant - Setup Validation")
    print("=" * 60)
    
    validator = SetupValidator()
    
    # Run all validation checks
    checks = [
        validator.check_file_structure(),
        validator.check_python_files(),
        validator.check_dependencies(),
        validator.check_environment(),
        validator.check_static_files(),
        validator.check_templates(),
        validator.check_docker_setup(),
        validator.check_project_structure(),
        await validator.check_runtime_functionality()
    ]
    
    # Generate and display report
    report = validator.generate_report()
    
    # Save report to file
    report_file = validator.project_root / "validation_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    validator.print_summary(report)
    
    print(f"\n📁 Detailed report saved to: {report_file}")
    
    # Exit with appropriate code
    if validator.issues:
        sys.exit(1)  # Critical issues found
    elif validator.warnings:
        sys.exit(2)  # Warnings found
    else:
        sys.exit(0)  # All good

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"💥 Validation failed: {e}")
        sys.exit(3)