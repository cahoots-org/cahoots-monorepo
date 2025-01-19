"""Integration tests for policy enforcement system."""
import pytest
from datetime import datetime
from src.utils.security import (
    PolicyManager,
    SecurityPolicy,
    RateLimiter,
    SecurityScope,
    Permission,
    ResourceType,
    PermissionLevel
)

@pytest.mark.integration
class TestPolicyEnforcement:
    """Test comprehensive policy enforcement."""
    
    @pytest.mark.asyncio
    async def test_layered_policy_enforcement(self, policy_manager: PolicyManager):
        """Test enforcement of layered policies with different scopes."""
        # Given a base security policy
        base_policy = SecurityPolicy(
            name="base-security",
            rules={
                "ip_whitelist": ["127.0.0.1"],
                "required_scopes": ["read"],
                "time_window": {"start": "09:00", "end": "17:00"}
            }
        )
        await policy_manager.create_policy(base_policy)
        
        # And a more restrictive policy that extends it
        restrictive_policy = SecurityPolicy(
            name="restrictive-security",
            rules={
                "required_scopes": ["read", "write"],
                "resource_access": {
                    "projects": ["secure-project"],
                    "roles": ["admin"]
                }
            },
            extends="base-security"
        )
        await policy_manager.create_policy(restrictive_policy)
        
        # Test scenarios
        test_cases = [
            {
                "name": "Valid request within base policy",
                "data": {
                    "client_ip": "127.0.0.1",
                    "scopes": ["read"],
                    "request_time": "13:00"
                },
                "should_pass": True
            },
            {
                "name": "Invalid IP",
                "data": {
                    "client_ip": "192.168.1.1",
                    "scopes": ["read", "write"],
                    "request_time": "13:00"
                },
                "should_pass": False
            },
            {
                "name": "Outside time window",
                "data": {
                    "client_ip": "127.0.0.1",
                    "scopes": ["read"],
                    "request_time": "18:00"
                },
                "should_pass": False
            },
            {
                "name": "Missing required scope",
                "data": {
                    "client_ip": "127.0.0.1",
                    "request_time": "13:00",
                    "scopes": []
                },
                "should_pass": False
            }
        ]
        
        for case in test_cases:
            result = await policy_manager.validate_key_usage("test_key", case["data"])
            assert result is case["should_pass"], f"Failed: {case['name']}"
            
    @pytest.mark.asyncio
    async def test_resource_specific_enforcement(self, policy_manager: PolicyManager):
        """Test enforcement for specific resources."""
        # Given a resource-specific policy
        policy = SecurityPolicy(
            name="resource-policy",
            rules={
                "resource_access": {
                    "projects": ["project-1", "project-2"],
                    "roles": ["admin", "developer"]
                },
                "required_scopes": ["read", "write"]
            }
        )
        await policy_manager.create_policy(policy)
        
        # Test different resource access patterns
        test_cases = [
            {
                "name": "Valid project and role",
                "data": {
                    "project_id": "project-1",
                    "role": "admin",
                    "scopes": ["read", "write"]
                },
                "should_pass": True
            },
            {
                "name": "Invalid project",
                "data": {
                    "project_id": "project-3",
                    "role": "admin",
                    "scopes": ["read", "write"]
                },
                "should_pass": False
            },
            {
                "name": "Invalid role",
                "data": {
                    "project_id": "project-1",
                    "role": "guest",
                    "scopes": ["read", "write"]
                },
                "should_pass": False
            }
        ]
        
        for case in test_cases:
            result = await policy_manager.validate_key_usage("test_key", case["data"])
            assert result is case["should_pass"], f"Failed: {case['name']}"
            
    @pytest.mark.asyncio
    async def test_scope_inheritance(self, policy_manager: PolicyManager):
        """Test scope inheritance and override behavior."""
        # Given a base policy with basic scopes
        base_policy = SecurityPolicy(
            name="base-scope",
            rules={
                "required_scopes": ["read"]
            }
        )
        await policy_manager.create_policy(base_policy)
        
        # And an extending policy that adds scopes
        extended_policy = SecurityPolicy(
            name="extended-scope",
            rules={
                "required_scopes": ["read", "write", "admin"]
            },
            extends="base-scope"
        )
        await policy_manager.create_policy(extended_policy)
        
        # Test scope inheritance
        test_cases = [
            {
                "name": "Base scope only",
                "data": {"scopes": ["read"]},
                "should_pass": True
            },
            {
                "name": "Extended scope complete",
                "data": {"scopes": ["read", "write", "admin"]},
                "should_pass": True
            },
            {
                "name": "Missing required scope",
                "data": {"scopes": ["write", "admin"]},
                "should_pass": False
            }
        ]
        
        for case in test_cases:
            result = await policy_manager.validate_key_usage("test_key", case["data"])
            assert result is case["should_pass"], f"Failed: {case['name']}" 