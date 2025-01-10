"""SAML metadata handling utilities."""
from typing import Dict, Optional
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives import serialization

class SAMLMetadata:
    """SAML metadata handler for parsing and generating metadata."""
    
    NAMESPACES = {
        'md': 'urn:oasis:names:tc:SAML:2.0:metadata',
        'ds': 'http://www.w3.org/2000/09/xmldsig#',
        'saml': 'urn:oasis:names:tc:SAML:2.0:assertion'
    }

    def __init__(self, entity_id: str, cert_path: Optional[str] = None):
        """Initialize metadata handler.
        
        Args:
            entity_id: Unique identifier for the entity
            cert_path: Path to X.509 certificate file
        """
        self.entity_id = entity_id
        self.cert_path = cert_path
        self._certificate = None
        if cert_path:
            self._load_certificate()

    def _load_certificate(self) -> None:
        """Load X.509 certificate from file."""
        with open(self.cert_path, 'rb') as cert_file:
            cert_data = cert_file.read()
            self._certificate = load_pem_x509_certificate(cert_data)

    def generate_sp_metadata(self, 
                           acs_url: str,
                           name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
                           valid_days: int = 365) -> str:
        """Generate Service Provider metadata XML.
        
        Args:
            acs_url: Assertion Consumer Service URL
            name_id_format: Name ID format to request
            valid_days: Validity period in days
            
        Returns:
            str: XML metadata string
        """
        root = ET.Element(f"{{{self.NAMESPACES['md']}}}EntityDescriptor", {
            'entityID': self.entity_id,
            'validUntil': (datetime.utcnow() + timedelta(days=valid_days)).isoformat()
        })

        sp_sso = ET.SubElement(root, f"{{{self.NAMESPACES['md']}}}SPSSODescriptor", {
            'protocolSupportEnumeration': 'urn:oasis:names:tc:SAML:2.0:protocol'
        })

        # Add key descriptor if certificate is present
        if self._certificate:
            key_descriptor = ET.SubElement(sp_sso, f"{{{self.NAMESPACES['md']}}}KeyDescriptor", {
                'use': 'signing'
            })
            key_info = ET.SubElement(key_descriptor, f"{{{self.NAMESPACES['ds']}}}KeyInfo")
            x509_data = ET.SubElement(key_info, f"{{{self.NAMESPACES['ds']}}}X509Data")
            x509_cert = ET.SubElement(x509_data, f"{{{self.NAMESPACES['ds']}}}X509Certificate")
            x509_cert.text = self._certificate.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')

        # Name ID format
        name_id = ET.SubElement(sp_sso, f"{{{self.NAMESPACES['md']}}}NameIDFormat")
        name_id.text = name_id_format

        # Assertion Consumer Service
        ET.SubElement(sp_sso, f"{{{self.NAMESPACES['md']}}}AssertionConsumerService", {
            'Binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST',
            'Location': acs_url,
            'index': '0',
            'isDefault': 'true'
        })

        return ET.tostring(root, encoding='unicode')

    def parse_idp_metadata(self, metadata_xml: str) -> Dict:
        """Parse Identity Provider metadata XML.
        
        Args:
            metadata_xml: XML metadata string
            
        Returns:
            Dict containing parsed metadata
        """
        root = ET.fromstring(metadata_xml)
        
        # Register namespaces for XPath
        for prefix, uri in self.NAMESPACES.items():
            ET.register_namespace(prefix, uri)

        idp_descriptor = root.find(f"./md:IDPSSODescriptor", self.NAMESPACES)
        if idp_descriptor is None:
            raise ValueError("No IDPSSODescriptor found in metadata")

        # Extract SSO URLs
        sso_urls = {}
        for binding in idp_descriptor.findall(f"./md:SingleSignOnService", self.NAMESPACES):
            binding_type = binding.get('Binding')
            location = binding.get('Location')
            sso_urls[binding_type] = location

        # Extract signing certificate
        cert_data = None
        key_descriptor = idp_descriptor.find(
            f"./md:KeyDescriptor[@use='signing']//ds:X509Certificate",
            self.NAMESPACES
        )
        if key_descriptor is not None:
            cert_data = key_descriptor.text

        return {
            'entity_id': root.get('entityID'),
            'sso_urls': sso_urls,
            'signing_certificate': cert_data
        } 