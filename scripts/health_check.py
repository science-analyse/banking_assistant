#!/usr/bin/env python3
"""
Health Check Script for Kapital Bank AI Assistant
Monitors application health, external APIs, and system resources
"""

import asyncio
import aiohttp
import argparse
import sys
import json
import time
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

class HealthChecker:
    """Comprehensive health monitoring for the banking assistant"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "checks": {},
            "metrics": {},
            "alerts": []
        }
        
        # Thresholds for alerts
        self.thresholds = {
            "response_time_warning": 1.0,  # seconds
            "response_time_critical": 5.0,  # seconds
            "memory_usage_warning": 80,     # percentage
            "memory_usage_critical": 95,    # percentage
            "disk_usage_warning": 80,       # percentage
            "disk_usage_critical": 95,      # percentage
            "cpu_usage_warning": 80,        # percentage
            "cpu_usage_critical": 95        # percentage
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def print_status(self, check_name: str, status: str, details: str = "", response_time: float = 0):
        """Print formatted check status"""
        status_icons = {
            "healthy": "✅",
            "warning": "⚠️",
            "critical": "❌",
            "unknown": "❓"
        }
        
        icon = status_icons.get(status, "❓")
        time_str = f" ({response_time:.3f}s)" if response_time > 0 else ""
        print(f"{icon} {check_name}: {status.upper()}{time_str}")
        
        if details:
            print(f"   {details}")
    
    async def check_application_health(self) -> Dict[str, Any]:
        """Check main application health endpoint"""
        check_name = "Application Health"
        start_time = time.time()
        
        try:
            async with self.session.get(f"{self.base_url}/api/health") as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Determine status based on response data
                    status = "healthy"
                    if data.get("status") == "degraded":
                        status = "warning"
                    elif data.get("status") == "unhealthy":
                        status = "critical"
                    
                    # Check response time
                    if response_time > self.thresholds["response_time_critical"]:
                        status = "critical"
                        self.results["alerts"].append(f"Application response time critical: {response_time:.3f}s")
                    elif response_time > self.thresholds["response_time_warning"]:
                        if status == "healthy":
                            status = "warning"
                        self.results["alerts"].append(f"Application response time slow: {response_time:.3f}s")
                    
                    self.print_status(check_name, status, 
                                    f"Database: {data.get('database', 'unknown')}, "
                                    f"MCP: {data.get('mcp_client', 'unknown')}", 
                                    response_time)
                    
                    return {
                        "status": status,
                        "response_time": response_time,
                        "data": data
                    }
                else:
                    self.print_status(check_name, "critical", 
                                    f"HTTP {response.status}: {response.reason}", response_time)
                    return {
                        "status": "critical",
                        "response_time": response_time,
                        "error": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            response_time = time.time() - start_time
            self.print_status(check_name, "critical", f"Connection failed: {str(e)}", response_time)
            return {
                "status": "critical",
                "response_time": response_time,
                "error": str(e)
            }
    
    async def check_api_endpoints(self) -> Dict[str, Any]:
        """Check key API endpoints"""
        endpoints = {
            "Currency Rates": "/api/currency/rates",
            "Location Search": "/api/locations/find",
            "AI Chat": "/api/chat"
        }
        
        results = {}
        
        for name, endpoint in endpoints.items():
            start_time = time.time()
            
            try:
                if endpoint == "/api/locations/find":
                    # POST endpoint
                    async with self.session.post(f"{self.base_url}{endpoint}", 
                                               json={
                                                   "latitude": 40.4093,
                                                   "longitude": 49.8671,
                                                   "service_type": "branch",
                                                   "radius_km": 5,
                                                   "limit": 5
                                               }) as response:
                        response_time = time.time() - start_time
                        status = "healthy" if response.status == 200 else "critical"
                        
                elif endpoint == "/api/chat":
                    # POST endpoint
                    async with self.session.post(f"{self.base_url}{endpoint}",
                                               json={
                                                   "message": "health check",
                                                   "language": "en"
                                               }) as response:
                        response_time = time.time() - start_time
                        status = "healthy" if response.status == 200 else "critical"
                
                else:
                    # GET endpoint
                    async with self.session.get(f"{self.base_url}{endpoint}") as response:
                        response_time = time.time() - start_time
                        status = "healthy" if response.status == 200 else "critical"
                
                self.print_status(name, status, f"HTTP {response.status}", response_time)
                
                results[name.lower().replace(" ", "_")] = {
                    "status": status,
                    "response_time": response_time,
                    "http_status": response.status
                }
                
            except Exception as e:
                response_time = time.time() - start_time
                self.print_status(name, "critical", f"Failed: {str(e)}", response_time)
                
                results[name.lower().replace(" ", "_")] = {
                    "status": "critical",
                    "response_time": response_time,
                    "error": str(e)
                }
        
        return results
    
    async def check_external_apis(self) -> Dict[str, Any]:
        """Check external API connectivity"""
        external_apis = {
            "CBAR Currency": "https://www.cbar.az/currencies/06.06.2025.xml",
            "Kapital Bank Locations": "https://www.kapitalbank.az/locations/region?type=branch",
            "Currency Market Data": "https://www.azn.az/data/data.json"
        }
        
        results = {}
        
        for name, url in external_apis.items():
            start_time = time.time()
            
            try:
                async with self.session.get(url) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        status = "healthy"
                        if response_time > self.thresholds["response_time_warning"]:
                            status = "warning"
                    else:
                        status = "critical"
                    
                    self.print_status(name, status, f"HTTP {response.status}", response_time)
                    
                    results[name.lower().replace(" ", "_")] = {
                        "status": status,
                        "response_time": response_time,
                        "http_status": response.status
                    }
                    
            except Exception as e:
                response_time = time.time() - start_time
                self.print_status(name, "critical", f"Failed: {str(e)}", response_time)
                
                results[name.lower().replace(" ", "_")] = {
                    "status": "critical",
                    "response_time": response_time,
                    "error": str(e)
                }
        
        return results
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        print("\n🖥️  System Resources:")
        
        # CPU Usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_status = self._get_resource_status(cpu_percent, "cpu_usage")
        self.print_status("CPU Usage", cpu_status, f"{cpu_percent:.1f}%")
        
        # Memory Usage
        memory = psutil.virtual_memory()
        memory_status = self._get_resource_status(memory.percent, "memory_usage")
        self.print_status("Memory Usage", memory_status, 
                         f"{memory.percent:.1f}% ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)")
        
        # Disk Usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        disk_status = self._get_resource_status(disk_percent, "disk_usage")
        self.print_status("Disk Usage", disk_status,
                         f"{disk_percent:.1f}% ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)")
        
        # Load Average (Unix only)
        load_avg = None
        if hasattr(os, 'getloadavg'):
            load_avg = os.getloadavg()
            load_status = "healthy"
            if load_avg[0] > psutil.cpu_count():
                load_status = "warning"
            if load_avg[0] > psutil.cpu_count() * 2:
                load_status = "critical"
            
            self.print_status("Load Average", load_status, 
                             f"1m: {load_avg[0]:.2f}, 5m: {load_avg[1]:.2f}, 15m: {load_avg[2]:.2f}")
        
        # Network Connections
        connections = len(psutil.net_connections())
        conn_status = "healthy"
        if connections > 1000:
            conn_status = "warning"
        if connections > 5000:
            conn_status = "critical"
        
        self.print_status("Network Connections", conn_status, f"{connections} active")
        
        return {
            "cpu": {
                "status": cpu_status,
                "percent": cpu_percent
            },
            "memory": {
                "status": memory_status,
                "percent": memory.percent,
                "used_gb": memory.used // (1024**3),
                "total_gb": memory.total // (1024**3)
            },
            "disk": {
                "status": disk_status,
                "percent": disk_percent,
                "used_gb": disk.used // (1024**3),
                "total_gb": disk.total // (1024**3)
            },
            "load_average": load_avg,
            "network_connections": connections
        }
    
    def _get_resource_status(self, percent: float, resource_type: str) -> str:
        """Get status based on resource usage percentage"""
        warning_threshold = self.thresholds[f"{resource_type}_warning"]
        critical_threshold = self.thresholds[f"{resource_type}_critical"]
        
        if percent >= critical_threshold:
            self.results["alerts"].append(f"{resource_type.replace('_', ' ').title()} critical: {percent:.1f}%")
            return "critical"
        elif percent >= warning_threshold:
            self.results["alerts"].append(f"{resource_type.replace('_', ' ').title()} high: {percent:.1f}%")
            return "warning"
        else:
            return "healthy"
    
    def check_database_files(self) -> Dict[str, Any]:
        """Check database file status"""
        print("\n🗄️  Database Status:")
        
        db_files = [
            "kapital_assistant.db",
            "./data/kapital_assistant.db",
            "kapital_assistant_dev.db"
        ]
        
        results = {}
        
        for db_file in db_files:
            if Path(db_file).exists():
                stat = Path(db_file).stat()
                size_mb = stat.st_size / (1024 * 1024)
                modified = datetime.fromtimestamp(stat.st_mtime)
                age = datetime.now() - modified
                
                status = "healthy"
                details = f"Size: {size_mb:.1f}MB, Modified: {age.days}d ago"
                
                if size_mb > 1000:  # > 1GB
                    status = "warning"
                    details += " (Large file)"
                
                if age.days > 7:  # Not modified in a week
                    status = "warning"
                    details += " (Stale)"
                
                self.print_status(f"Database {db_file}", status, details)
                
                results[db_file.replace(".", "_").replace("/", "_")] = {
                    "status": status,
                    "size_mb": size_mb,
                    "modified": modified.isoformat(),
                    "age_days": age.days
                }
            else:
                self.print_status(f"Database {db_file}", "warning", "File not found")
                results[db_file.replace(".", "_").replace("/", "_")] = {
                    "status": "warning",
                    "error": "File not found"
                }
        
        return results
    
    async def run_comprehensive_check(self) -> Dict[str, Any]:
        """Run all health checks"""
        print("🏛️ Kapital Bank AI Assistant - Health Check")
        print("=" * 60)
        
        # Application health
        print("\n🚀 Application Health:")
        app_health = await self.check_application_health()
        self.results["checks"]["application"] = app_health
        
        # API endpoints
        print("\n🔗 API Endpoints:")
        api_health = await self.check_api_endpoints()
        self.results["checks"]["api_endpoints"] = api_health
        
        # External APIs
        print("\n🌐 External APIs:")
        external_health = await self.check_external_apis()
        self.results["checks"]["external_apis"] = external_health
        
        # System resources
        system_health = self.check_system_resources()
        self.results["checks"]["system_resources"] = system_health
        
        # Database files
        db_health = self.check_database_files()
        self.results["checks"]["database_files"] = db_health
        
        # Calculate overall status
        self._calculate_overall_status()
        
        # Print summary
        self._print_summary()
        
        return self.results
    
    def _calculate_overall_status(self):
        """Calculate overall system status"""
        all_statuses = []
        
        # Collect all status values
        for check_category in self.results["checks"].values():
            if isinstance(check_category, dict):
                if "status" in check_category:
                    all_statuses.append(check_category["status"])
                else:
                    for check in check_category.values():
                        if isinstance(check, dict) and "status" in check:
                            all_statuses.append(check["status"])
        
        # Determine overall status
        if "critical" in all_statuses:
            self.results["overall_status"] = "critical"
        elif "warning" in all_statuses:
            self.results["overall_status"] = "warning"
        elif "healthy" in all_statuses:
            self.results["overall_status"] = "healthy"
        else:
            self.results["overall_status"] = "unknown"
    
    def _print_summary(self):
        """Print health check summary"""
        print("\n" + "=" * 60)
        print("📊 HEALTH CHECK SUMMARY")
        print("=" * 60)
        
        status_icons = {
            "healthy": "✅",
            "warning": "⚠️",
            "critical": "❌",
            "unknown": "❓"
        }
        
        overall_icon = status_icons.get(self.results["overall_status"], "❓")
        print(f"{overall_icon} Overall Status: {self.results['overall_status'].upper()}")
        
        if self.results["alerts"]:
            print(f"\n⚠️  Alerts ({len(self.results['alerts'])}):")
            for alert in self.results["alerts"]:
                print(f"   • {alert}")
        
        # Quick metrics
        app_check = self.results["checks"].get("application", {})
        if "response_time" in app_check:
            print(f"\n📈 Key Metrics:")
            print(f"   • Application Response Time: {app_check['response_time']:.3f}s")
            
            sys_check = self.results["checks"].get("system_resources", {})
            if sys_check:
                print(f"   • CPU Usage: {sys_check.get('cpu', {}).get('percent', 'N/A')}%")
                print(f"   • Memory Usage: {sys_check.get('memory', {}).get('percent', 'N/A')}%")
                print(f"   • Disk Usage: {sys_check.get('disk', {}).get('percent', 'N/A')}%")
        
        print(f"\n🕐 Check completed at: {self.results['timestamp']}")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Kapital Bank AI Assistant Health Check")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the application")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    parser.add_argument("--continuous", type=int, help="Run continuously every N seconds")
    parser.add_argument("--alert-only", action="store_true", help="Only show alerts")
    
    args = parser.parse_args()
    
    async with HealthChecker(args.url) as checker:
        if args.continuous:
            print(f"Running health checks every {args.continuous} seconds...")
            print("Press Ctrl+C to stop")
            
            try:
                while True:
                    if not args.quiet:
                        print(f"\n{'='*60}")
                        print(f"Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"{'='*60}")
                    
                    results = await checker.run_comprehensive_check()
                    
                    if args.output:
                        with open(args.output, 'w') as f:
                            json.dump(results, f, indent=2)
                    
                    if args.alert_only and results["alerts"]:
                        print(f"🚨 ALERTS: {', '.join(results['alerts'])}")
                    
                    await asyncio.sleep(args.continuous)
                    
            except KeyboardInterrupt:
                print("\n👋 Health monitoring stopped")
        else:
            # Single run
            results = await checker.run_comprehensive_check()
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"\n📁 Results saved to {args.output}")
            
            # Exit with appropriate code
            if results["overall_status"] == "critical":
                sys.exit(2)
            elif results["overall_status"] == "warning":
                sys.exit(1)
            else:
                sys.exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"💥 Health check failed: {e}")
        sys.exit(3)