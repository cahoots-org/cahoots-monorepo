"""Tests for base federation components."""
import pytest
from datetime import datetime
from src.auth.federation.base import FederatedIdentity, TrustChain

def test_federated_identity_creation():
    """Test federated identity creation."""
    identity = FederatedIdentity(
        external_id="ext123",
        provider_id="provider1",
        attributes={"name": "Test User", "email": "test@example.com"},
        metadata={"source": "test"}
    )
    
    assert identity.external_id == "ext123"
    assert identity.provider_id == "provider1"
    assert identity.attributes["name"] == "Test User"
    assert identity.attributes["email"] == "test@example.com"
    assert identity.metadata["source"] == "test"
    assert isinstance(identity.created_at, datetime)
    assert isinstance(identity.updated_at, datetime)

def test_federated_identity_to_dict():
    """Test federated identity serialization."""
    identity = FederatedIdentity(
        external_id="ext123",
        provider_id="provider1",
        attributes={"name": "Test User"}
    )
    
    data = identity.to_dict()
    assert isinstance(data, dict)
    assert data["external_id"] == "ext123"
    assert data["provider_id"] == "provider1"
    assert data["attributes"]["name"] == "Test User"
    assert "created_at" in data
    assert "updated_at" in data

def test_trust_chain_initialization():
    """Test trust chain initialization."""
    chain = TrustChain(max_depth=5)
    assert chain.max_depth == 5
    assert isinstance(chain._trust_relationships, dict)
    assert len(chain._trust_relationships) == 0

def test_trust_chain_add_trust():
    """Test adding trust relationships."""
    chain = TrustChain()
    chain.add_trust("provider1", "provider2")
    
    assert "provider1" in chain._trust_relationships
    assert "provider2" in chain._trust_relationships["provider1"]
    
    # Add another trust
    chain.add_trust("provider1", "provider3")
    assert len(chain._trust_relationships["provider1"]) == 2
    assert "provider3" in chain._trust_relationships["provider1"]

def test_trust_chain_remove_trust():
    """Test removing trust relationships."""
    chain = TrustChain()
    chain.add_trust("provider1", "provider2")
    chain.add_trust("provider1", "provider3")
    
    chain.remove_trust("provider1", "provider2")
    assert "provider2" not in chain._trust_relationships["provider1"]
    assert "provider3" in chain._trust_relationships["provider1"]

def test_trust_chain_validate_direct():
    """Test direct trust validation."""
    chain = TrustChain()
    chain.add_trust("provider1", "provider2")
    
    assert chain.validate_chain("provider1", "provider2") is True
    assert chain.validate_chain("provider1", "provider3") is False
    assert chain.validate_chain("provider2", "provider1") is False

def test_trust_chain_validate_transitive():
    """Test transitive trust validation."""
    chain = TrustChain()
    chain.add_trust("provider1", "provider2")
    chain.add_trust("provider2", "provider3")
    
    assert chain.validate_chain("provider1", "provider3") is True
    assert chain.validate_chain("provider1", "provider4") is False

def test_trust_chain_max_depth():
    """Test trust chain max depth limit."""
    chain = TrustChain(max_depth=2)
    chain.add_trust("provider1", "provider2")
    chain.add_trust("provider2", "provider3")
    chain.add_trust("provider3", "provider4")
    
    # Within depth limit
    assert chain.validate_chain("provider1", "provider3") is True
    # Exceeds depth limit
    assert chain.validate_chain("provider1", "provider4") is False

def test_trust_chain_cyclic():
    """Test cyclic trust relationships."""
    chain = TrustChain()
    chain.add_trust("provider1", "provider2")
    chain.add_trust("provider2", "provider3")
    chain.add_trust("provider3", "provider1")
    
    # Should still respect max_depth and not loop infinitely
    assert chain.validate_chain("provider1", "provider2") is True
    assert chain.validate_chain("provider2", "provider3") is True
    assert chain.validate_chain("provider3", "provider1") is True 