"""Load testing configuration using Locust."""
from locust import HttpUser, task, between
from typing import Dict, Any
import json
import random

class APIUser(HttpUser):
    """Simulated API user for load testing."""
    
    # Wait between 1-5 seconds between tasks
    wait_time = between(1, 5)
    
    def on_start(self):
        """Setup before tests start."""
        # Add any setup code here (e.g., authentication)
        pass
    
    @task(10)  # Higher weight for health checks
    def health_check(self):
        """Test the health check endpoint."""
        with self.client.get("/health", name="Health Check") as response:
            if response.status_code != 200:
                response.failure(f"Health check failed with status {response.status_code}")
    
    @task(5)
    def publish_message(self):
        """Test message publishing."""
        channels = ["system", "project_manager", "developer", "ux_designer"]
        message = {
            "type": "test_message",
            "payload": {
                "test_id": random.randint(1, 1000),
                "timestamp": "2024-02-20T12:00:00Z"
            }
        }
        
        headers = {"Content-Type": "application/json"}
        channel = random.choice(channels)
        
        with self.client.post(
            f"/messages/{channel}",
            json=message,
            headers=headers,
            name="Publish Message"
        ) as response:
            if response.status_code != 202:
                response.failure(f"Message publish failed with status {response.status_code}")
    
    @task(3)
    def create_project(self):
        """Test project creation."""
        project = {
            "name": f"Test Project {random.randint(1, 1000)}",
            "description": "A test project for load testing"
        }
        
        headers = {"Content-Type": "application/json"}
        
        with self.client.post(
            "/projects",
            json=project,
            headers=headers,
            name="Create Project"
        ) as response:
            if response.status_code != 201:
                response.failure(f"Project creation failed with status {response.status_code}")

class APIMonitor(HttpUser):
    """Monitor critical endpoints continuously."""
    
    wait_time = between(10, 30)  # Longer wait times for monitoring
    
    @task
    def monitor_health(self):
        """Continuously monitor system health."""
        with self.client.get("/health", name="Health Monitor") as response:
            if response.status_code != 200:
                self.environment.events.request_failure.fire(
                    request_type="GET",
                    name="Health Monitor",
                    response_time=response.elapsed.total_seconds() * 1000,
                    exception=f"Health check failed with status {response.status_code}"
                )
            
            # Check specific metrics
            data = response.json()
            metrics = data.get("system_metrics", {})
            
            # Alert on high resource usage
            if metrics.get("cpu_percent", 0) > 80:
                self.environment.events.request_failure.fire(
                    request_type="GET",
                    name="CPU Usage Alert",
                    response_time=0,
                    exception=f"High CPU usage: {metrics['cpu_percent']}%"
                )
            
            if metrics.get("memory_percent", 0) > 80:
                self.environment.events.request_failure.fire(
                    request_type="GET",
                    name="Memory Usage Alert",
                    response_time=0,
                    exception=f"High memory usage: {metrics['memory_percent']}%"
                ) 