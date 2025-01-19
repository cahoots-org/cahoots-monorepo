"""Policy manager integration tests."""
import pytest
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock

from cahoots_core.utils.security import PolicyManager, SecurityPolicy
from cahoots_core.utils.rate_limiter import RateLimiter

@pytest.mark.integration
class TestPolicyEnforcement:
    """Integration tests for policy enforcement."""
    
    @pytest.mark.asyncio
    async def test_policy_lifecycle(self, policy_manager: PolicyManager):
        """Test complete policy lifecycle - creation, retrieval, and validation."""
        # Given a security policy with IP whitelist
        policy = SecurityPolicy(
            name="test-policy",
            rules={
                "ip_whitelist": ["127.0.0.1"],
                "rate_limit": {"requests": 100, "window": 60}
            },
            description="Test policy for integration"
        )
        
        # When we create the policy
        await policy_manager.create_policy(policy)
        
        # Then we can retrieve it
        retrieved = await policy_manager.get_policy("test-policy")
        assert retrieved is not None
        assert retrieved.name == "test-policy"
        assert "127.0.0.1" in retrieved.rules["ip_whitelist"]
        assert retrieved.rules["rate_limit"]["requests"] == 100
        
    @pytest.mark.asyncio
    async def test_policy_validation(self, policy_manager: PolicyManager):
        """Test policy validation with different scenarios."""
        # Given policies for different scenarios
        policies = [
            SecurityPolicy(
                name="ip-policy",
                rules={"ip_whitelist": ["127.0.0.1"]}
            ),
            SecurityPolicy(
                name="time-policy",
                rules={"allowed_hours": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17]}
            )
        ]
        
        # When we create the policies
        for policy in policies:
            await policy_manager.create_policy(policy)
            
        # Then validation should work for valid cases
        assert await policy_manager.validate_key_usage(
            "test_key",
            {"client_ip": "127.0.0.1", "request_hour": 10}
        ) is True
        
        # And fail for invalid cases
        assert await policy_manager.validate_key_usage(
            "test_key",
            {"client_ip": "192.168.1.1", "request_hour": 10}
        ) is False
        
        assert await policy_manager.validate_key_usage(
            "test_key",
            {"client_ip": "127.0.0.1", "request_hour": 23}
        ) is False
        
    @pytest.mark.asyncio
    async def test_policy_ttl(self, policy_manager: PolicyManager):
        """Test policy time-to-live functionality."""
        # Given a policy with short TTL
        policy = SecurityPolicy(
            name="temp-policy",
            rules={"ip_whitelist": ["127.0.0.1"]},
            description="Temporary policy"
        )
        
        # When we create with TTL
        await policy_manager.create_policy(policy, ttl=2)
        
        # Then it should exist initially
        assert await policy_manager.get_policy("temp-policy") is not None
        
        # But expire after TTL
        await asyncio.sleep(3)
        assert await policy_manager.get_policy("temp-policy") is None
        
    @pytest.mark.asyncio
    async def test_multiple_policy_validation(self, policy_manager: PolicyManager):
        """Test validation against multiple policies."""
        # Given multiple policies
        policies = [
            SecurityPolicy(
                name="ip-policy",
                rules={"ip_whitelist": ["127.0.0.1"]}
            ),
            SecurityPolicy(
                name="org-policy",
                rules={"allowed_orgs": ["test-org"]}
            ),
            SecurityPolicy(
                name="scope-policy",
                rules={"required_scopes": ["read", "write"]}
            )
        ]
        
        # When we create all policies
        for policy in policies:
            await policy_manager.create_policy(policy)
            
        # Then validation should check all policies
        valid_data = {
            "client_ip": "127.0.0.1",
            "organization": "test-org",
            "scopes": ["read", "write"]
        }
        assert await policy_manager.validate_key_usage("test_key", valid_data) is True
        
        # And fail if any policy fails
        invalid_data = {
            "client_ip": "127.0.0.1",  # Valid IP
            "organization": "test-org",  # Valid org
            "scopes": ["read"]  # Missing write scope
        }
        assert await policy_manager.validate_key_usage("test_key", invalid_data) is False 

    @pytest.mark.asyncio
    async def test_complex_policy_rules(self, policy_manager: PolicyManager):
        """Test complex policy rules with multiple conditions."""
        # Given a complex policy with multiple rules
        policy = SecurityPolicy(
            name="complex-policy",
            rules={
                "ip_whitelist": ["127.0.0.1", "10.0.0.1"],
                "time_window": {"start": "09:00", "end": "17:00"},
                "required_scopes": ["read", "write", "admin"],
                "rate_limit": {"requests": 100, "window": 60},
                "resource_access": {
                    "projects": ["project-1", "project-2"],
                    "roles": ["admin", "developer"]
                }
            }
        )
        await policy_manager.create_policy(policy)

        # Test valid complex scenario
        valid_data = {
            "client_ip": "127.0.0.1",
            "request_time": "13:00",
            "scopes": ["read", "write", "admin"],
            "project_id": "project-1",
            "role": "admin"
        }
        assert await policy_manager.validate_key_usage("test_key", valid_data) is True

        # Test invalid scenarios
        invalid_scenarios = [
            {
                "scenario": "Invalid IP",
                "data": {**valid_data, "client_ip": "192.168.1.1"},
                "should_pass": False
            },
            {
                "scenario": "Outside time window",
                "data": {**valid_data, "request_time": "20:00"},
                "should_pass": False
            },
            {
                "scenario": "Missing required scope",
                "data": {**valid_data, "scopes": ["read", "write"]},
                "should_pass": False
            },
            {
                "scenario": "Invalid project access",
                "data": {**valid_data, "project_id": "project-3"},
                "should_pass": False
            },
            {
                "scenario": "Invalid role",
                "data": {**valid_data, "role": "guest"},
                "should_pass": False
            }
        ]

        for scenario in invalid_scenarios:
            result = await policy_manager.validate_key_usage("test_key", scenario["data"])
            assert result is scenario["should_pass"], f"Failed: {scenario['scenario']}"

    @pytest.mark.asyncio
    async def test_policy_inheritance(self, policy_manager: PolicyManager):
        """Test policy inheritance and override behavior."""
        # Given a base policy
        base_policy = SecurityPolicy(
            name="base-policy",
            rules={
                "ip_whitelist": ["127.0.0.1"],
                "scopes": ["read"]
            }
        )
        await policy_manager.create_policy(base_policy)

        # And an extending policy
        extended_policy = SecurityPolicy(
            name="extended-policy",
            rules={
                "ip_whitelist": ["127.0.0.1", "10.0.0.1"],
                "scopes": ["read", "write"],
                "additional_rule": "new_value"
            },
            extends="base-policy"
        )
        await policy_manager.create_policy(extended_policy)

        # Test inheritance scenarios
        scenarios = [
            {
                "name": "Base policy only",
                "data": {
                    "client_ip": "127.0.0.1",
                    "scopes": ["read"]
                },
                "should_pass": True
            },
            {
                "name": "Extended IP allowed",
                "data": {
                    "client_ip": "10.0.0.1",
                    "scopes": ["read", "write"]
                },
                "should_pass": True
            },
            {
                "name": "Invalid IP for both",
                "data": {
                    "client_ip": "192.168.1.1",
                    "scopes": ["read", "write"]
                },
                "should_pass": False
            }
        ]

        for scenario in scenarios:
            result = await policy_manager.validate_key_usage("test_key", scenario["data"])
            assert result is scenario["should_pass"], f"Failed: {scenario['name']}"

    @pytest.mark.asyncio
    async def test_policy_conflict_resolution(self, policy_manager: PolicyManager):
        """Test how conflicting policies are resolved."""
        # Given two conflicting policies
        policies = [
            SecurityPolicy(
                name="restrictive-policy",
                rules={
                    "ip_whitelist": ["127.0.0.1"],
                    "allowed_hours": [9, 10, 11, 12]
                }
            ),
            SecurityPolicy(
                name="permissive-policy",
                rules={
                    "ip_whitelist": ["127.0.0.1", "10.0.0.1"],
                    "allowed_hours": list(range(0, 24))
                }
            )
        ]

        # When we create both policies
        for policy in policies:
            await policy_manager.create_policy(policy)

        # Then the most restrictive rules should apply
        test_cases = [
            {
                "name": "Within restrictive bounds",
                "data": {
                    "client_ip": "127.0.0.1",
                    "request_hour": 10
                },
                "should_pass": True
            },
            {
                "name": "Outside restrictive hours",
                "data": {
                    "client_ip": "127.0.0.1",
                    "request_hour": 15
                },
                "should_pass": False
            },
            {
                "name": "IP allowed in permissive only",
                "data": {
                    "client_ip": "10.0.0.1",
                    "request_hour": 10
                },
                "should_pass": False
            }
        ]

        for case in test_cases:
            result = await policy_manager.validate_key_usage("test_key", case["data"])
            assert result is case["should_pass"], f"Failed: {case['name']}" 

    @pytest.mark.asyncio
    async def test_policy_rate_limit_integration(self, policy_manager: PolicyManager, redis_client):
        """Test integration between policy enforcement and rate limiting."""
        # Given a policy with rate limiting rules
        policy = SecurityPolicy(
            name="rate-limit-policy",
            rules={
                "ip_whitelist": ["127.0.0.1"],
                "rate_limit": {"requests": 3, "window": 1}
            }
        )
        await policy_manager.create_policy(policy)

        # And a rate limiter
        rate_limiter = RateLimiter(redis=redis_client)

        # When making requests within policy and rate limits
        results = []
        for _ in range(3):
            # Check policy
            policy_check = await policy_manager.validate_key_usage(
                "test_key",
                {"client_ip": "127.0.0.1"}
            )
            # Check rate limit
            rate_check = await rate_limiter.check_rate_limit(
                "test_key",
                policy.rules["rate_limit"]["requests"],
                policy.rules["rate_limit"]["window"]
            )
            results.append(policy_check and rate_check)

        # Then all should succeed
        assert all(results), "All requests within limits should succeed"

        # When exceeding rate limit
        policy_check = await policy_manager.validate_key_usage(
            "test_key",
            {"client_ip": "127.0.0.1"}
        )
        rate_check = await rate_limiter.check_rate_limit(
            "test_key",
            policy.rules["rate_limit"]["requests"],
            policy.rules["rate_limit"]["window"]
        )

        # Then it should be blocked
        assert policy_check, "Policy should still pass"
        assert not rate_check, "Rate limit should be exceeded"

        # When using invalid IP
        policy_check = await policy_manager.validate_key_usage(
            "test_key",
            {"client_ip": "192.168.1.1"}
        )
        rate_check = await rate_limiter.check_rate_limit(
            "test_key",
            policy.rules["rate_limit"]["requests"],
            policy.rules["rate_limit"]["window"]
        )

        # Then policy should fail regardless of rate limit
        assert not policy_check, "Policy should fail for invalid IP"
        assert not rate_check, "Rate limit should still be exceeded" 