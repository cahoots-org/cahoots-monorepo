"""Integration tests for SAML federation."""
import pytest
from datetime import datetime, timedelta
import base64
import xml.etree.ElementTree as ET
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes

from src.auth.federation.base import FederatedIdentity
from src.models.federation import FederatedIdentityMapping
from src.models.identity_provider import IdentityProvider
from src.services.federation import FederationService

class MockSAMLIdP:
    """Mock SAML Identity Provider for testing."""
    
    NAMESPACES = {
        'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
        'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
        'ds': 'http://www.w3.org/2000/09/xmldsig#'
    }
    
    def __init__(self):
        """Initialize mock IdP with test certificates."""
        # Generate test key pair
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
        
        # Generate self-signed certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, u"Test IdP")
        ])
        
        self.certificate = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            self.public_key
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=10)
        ).sign(self.private_key, hashes.SHA256())
        
        self.entity_id = "https://test.idp/metadata"
        self.sso_url = "https://test.idp/sso"
        self.acs_url = "https://test.sp/acs"
    
    def get_metadata(self) -> str:
        """Generate IdP metadata XML."""
        root = ET.Element(f"{{{self.NAMESPACES['md']}}}EntityDescriptor", {
            'entityID': self.entity_id
        })
        
        idp = ET.SubElement(root, f"{{{self.NAMESPACES['md']}}}IDPSSODescriptor", {
            'protocolSupportEnumeration': 'urn:oasis:names:tc:SAML:2.0:protocol'
        })
        
        # Add certificate
        key_descriptor = ET.SubElement(idp, f"{{{self.NAMESPACES['md']}}}KeyDescriptor", {
            'use': 'signing'
        })
        key_info = ET.SubElement(key_descriptor, f"{{{self.NAMESPACES['ds']}}}KeyInfo")
        x509_data = ET.SubElement(key_info, f"{{{self.NAMESPACES['ds']}}}X509Data")
        x509_cert = ET.SubElement(x509_data, f"{{{self.NAMESPACES['ds']}}}X509Certificate")
        x509_cert.text = base64.b64encode(
            self.certificate.public_bytes(serialization.Encoding.DER)
        ).decode('utf-8')
        
        # Add SSO endpoint
        sso = ET.SubElement(idp, f"{{{self.NAMESPACES['md']}}}SingleSignOnService", {
            'Binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect',
            'Location': self.sso_url
        })
        
        return ET.tostring(root, encoding='unicode')
    
    def create_response(self, request_id: str, user_attrs: dict) -> str:
        """Create SAML response with user attributes."""
        root = ET.Element(f"{{{self.NAMESPACES['samlp']}}}Response", {
            'ID': f"_{request_id}_response",
            'Version': '2.0',
            'IssueInstant': datetime.utcnow().isoformat(),
            'Destination': self.acs_url,
            'InResponseTo': request_id
        })
        
        issuer = ET.SubElement(root, f"{{{self.NAMESPACES['saml']}}}Issuer")
        issuer.text = self.entity_id
        
        assertion = ET.SubElement(root, f"{{{self.NAMESPACES['saml']}}}Assertion", {
            'ID': f"_{request_id}_assertion",
            'Version': '2.0',
            'IssueInstant': datetime.utcnow().isoformat()
        })
        
        assertion_issuer = ET.SubElement(assertion, f"{{{self.NAMESPACES['saml']}}}Issuer")
        assertion_issuer.text = self.entity_id
        
        subject = ET.SubElement(assertion, f"{{{self.NAMESPACES['saml']}}}Subject")
        name_id = ET.SubElement(subject, f"{{{self.NAMESPACES['saml']}}}NameID")
        name_id.text = user_attrs.get('email', 'test@example.com')
        
        conditions = ET.SubElement(assertion, f"{{{self.NAMESPACES['saml']}}}Conditions", {
            'NotBefore': (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            'NotOnOrAfter': (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        })
        
        attr_statement = ET.SubElement(assertion, f"{{{self.NAMESPACES['saml']}}}AttributeStatement")
        for key, value in user_attrs.items():
            attr = ET.SubElement(attr_statement, f"{{{self.NAMESPACES['saml']}}}Attribute", {
                'Name': key
            })
            attr_val = ET.SubElement(attr, f"{{{self.NAMESPACES['saml']}}}AttributeValue")
            attr_val.text = str(value)
        
        return base64.b64encode(
            ET.tostring(root, encoding='utf-8')
        ).decode('utf-8')

@pytest.fixture
async def mock_idp():
    """Create mock SAML IdP."""
    return MockSAMLIdP()

@pytest.fixture
async def saml_provider(db_session, mock_idp):
    """Create SAML identity provider."""
    provider = IdentityProvider(
        name="Test SAML IdP",
        entity_id=mock_idp.entity_id,
        metadata={
            'sso_urls': {
                'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect': mock_idp.sso_url
            },
            'signing_certificate': base64.b64encode(
                mock_idp.certificate.public_bytes(serialization.Encoding.DER)
            ).decode('utf-8')
        }
    )
    db_session.add(provider)
    await db_session.commit()
    return provider

@pytest.mark.asyncio
async def test_saml_federation_flow(
    client,
    mock_idp,
    saml_provider,
    federation_service,
    test_user
):
    """Test complete SAML federation flow."""
    # 1. Start authentication
    response = await client.get(
        f"/federation/saml/login/{saml_provider.id}"
    )
    assert response.status_code == 302
    assert mock_idp.sso_url in response.headers['location']
    
    # Extract SAMLRequest from redirect URL
    saml_request = response.headers['location'].split('SAMLRequest=')[1]
    request_xml = base64.b64decode(saml_request).decode('utf-8')
    request_doc = ET.fromstring(request_xml)
    request_id = request_doc.get('ID')
    
    # 2. Mock IdP creates response
    user_attrs = {
        'email': 'test@example.com',
        'name': 'Test User',
        'role': 'user'
    }
    saml_response = mock_idp.create_response(request_id, user_attrs)
    
    # 3. Handle SAML response
    response = await client.post(
        "/federation/saml/acs",
        data={'SAMLResponse': saml_response}
    )
    assert response.status_code == 200
    
    # 4. Verify federation was established
    identity = await federation_service.get_federated_identity(
        str(test_user.id),
        str(saml_provider.id)
    )
    assert identity is not None
    assert identity.attributes['email'] == 'test@example.com'
    assert identity.attributes['name'] == 'Test User'
    
    # 5. Verify attribute mapping
    mapping = await FederatedIdentityMapping.get_by_user_provider(
        test_user.id,
        saml_provider.id
    )
    assert mapping is not None
    assert mapping.is_active is True
    assert mapping.attributes['email'] == 'test@example.com'

@pytest.mark.asyncio
async def test_saml_metadata_exchange(
    client,
    mock_idp,
    saml_provider
):
    """Test SAML metadata exchange."""
    # 1. Get SP metadata
    response = await client.get("/federation/saml/metadata")
    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/xml'
    
    # Verify SP metadata structure
    sp_metadata = ET.fromstring(response.content)
    assert sp_metadata.tag.endswith('EntityDescriptor')
    assert sp_metadata.find('.//{*}SPSSODescriptor') is not None
    
    # 2. Update IdP metadata
    response = await client.post(
        f"/federation/saml/providers/{saml_provider.id}/metadata",
        content=mock_idp.get_metadata()
    )
    assert response.status_code == 200
    
    # Verify IdP metadata was updated
    data = response.json()
    assert data['entity_id'] == mock_idp.entity_id
    assert 'sso_urls' in data
    assert 'signing_certificate' in data

@pytest.mark.asyncio
async def test_saml_attribute_mapping(
    client,
    mock_idp,
    saml_provider,
    federation_service,
    db_session
):
    """Test SAML attribute mapping."""
    # Create attribute mappings
    mappings = [
        AttributeMapping(
            provider_id=saml_provider.id,
            source_attribute="name",
            target_attribute="display_name",
            is_required=True
        ),
        AttributeMapping(
            provider_id=saml_provider.id,
            source_attribute="role",
            target_attribute="user_role",
            is_required=False
        )
    ]
    for mapping in mappings:
        db_session.add(mapping)
    await db_session.commit()
    
    # Create SAML response with attributes
    user_attrs = {
        'name': 'Test User',
        'role': 'admin',
        'email': 'test@example.com',
        'extra': 'ignored'
    }
    saml_response = mock_idp.create_response('test_req_id', user_attrs)
    
    # Process response
    response = await client.post(
        "/federation/saml/acs",
        data={'SAMLResponse': saml_response}
    )
    assert response.status_code == 200
    
    # Verify attribute mapping
    identity = await federation_service.get_federated_identity(
        str(test_user.id),
        str(saml_provider.id)
    )
    assert identity is not None
    assert identity.attributes['display_name'] == 'Test User'
    assert identity.attributes['user_role'] == 'admin'
    assert 'extra' not in identity.attributes 