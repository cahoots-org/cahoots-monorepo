"""SAML request and response processing."""
from typing import Dict, Optional
import base64
import zlib
from datetime import datetime
import uuid
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate
import xml.etree.ElementTree as ET

class SAMLProcessor:
    """Processor for SAML requests and responses."""

    NAMESPACES = {
        'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
        'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
        'ds': 'http://www.w3.org/2000/09/xmldsig#'
    }

    def __init__(self, entity_id: str, cert_path: Optional[str] = None, private_key_path: Optional[str] = None):
        """Initialize SAML processor.
        
        Args:
            entity_id: Entity ID for the service provider
            cert_path: Path to X.509 certificate file
            private_key_path: Path to private key file
        """
        self.entity_id = entity_id
        self._certificate = None
        self._private_key = None
        
        if cert_path:
            with open(cert_path, 'rb') as cert_file:
                self._certificate = load_pem_x509_certificate(cert_file.read())
                
        if private_key_path:
            with open(private_key_path, 'rb') as key_file:
                self._private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None
                )

    def create_auth_request(self, 
                          idp_url: str,
                          acs_url: str,
                          force_authn: bool = False,
                          name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified") -> str:
        """Create a SAML authentication request.
        
        Args:
            idp_url: Identity Provider SSO URL
            acs_url: Assertion Consumer Service URL
            force_authn: Whether to force re-authentication
            name_id_format: Name ID format to request
            
        Returns:
            str: Base64 encoded and deflated SAML request
        """
        # Create the AuthnRequest
        root = ET.Element(f"{{{self.NAMESPACES['samlp']}}}AuthnRequest", {
            'xmlns:samlp': self.NAMESPACES['samlp'],
            'xmlns:saml': self.NAMESPACES['saml'],
            'ID': f"_{uuid.uuid4()}",
            'Version': '2.0',
            'IssueInstant': datetime.utcnow().isoformat(),
            'Destination': idp_url,
            'ForceAuthn': str(force_authn).lower(),
            'IsPassive': 'false',
            'ProtocolBinding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST',
            'AssertionConsumerServiceURL': acs_url
        })

        # Add Issuer
        issuer = ET.SubElement(root, f"{{{self.NAMESPACES['saml']}}}Issuer")
        issuer.text = self.entity_id

        # Add NameIDPolicy
        name_id_policy = ET.SubElement(root, f"{{{self.NAMESPACES['samlp']}}}NameIDPolicy", {
            'Format': name_id_format,
            'AllowCreate': 'true'
        })

        # Convert to string
        request_xml = ET.tostring(root, encoding='utf-8')
        
        # Deflate and base64 encode
        compressed = zlib.compress(request_xml)[2:-4]
        return base64.b64encode(compressed).decode('utf-8')

    def process_response(self, response: str, idp_cert: Optional[str] = None) -> Dict:
        """Process and validate a SAML response.
        
        Args:
            response: Base64 encoded SAML response
            idp_cert: IdP certificate for signature validation
            
        Returns:
            Dict containing the validated assertion data
        """
        # Decode response
        xml = base64.b64decode(response)
        root = ET.fromstring(xml)

        # Validate signature if certificate provided
        if idp_cert:
            self._validate_signature(root, idp_cert)

        # Process assertion
        assertion = root.find(f".//{{{self.NAMESPACES['saml']}}}Assertion")
        if assertion is None:
            raise ValueError("No assertion found in response")

        # Extract subject
        subject = assertion.find(f".//{{{self.NAMESPACES['saml']}}}Subject")
        if subject is None:
            raise ValueError("No subject found in assertion")

        name_id = subject.find(f".//{{{self.NAMESPACES['saml']}}}NameID")
        if name_id is None:
            raise ValueError("No NameID found in subject")

        # Extract attributes
        attributes = {}
        for attribute in assertion.findall(f".//{{{self.NAMESPACES['saml']}}}Attribute"):
            name = attribute.get('Name')
            values = [v.text for v in attribute.findall(f".//{{{self.NAMESPACES['saml']}}}AttributeValue")]
            attributes[name] = values[0] if len(values) == 1 else values

        return {
            'name_id': name_id.text,
            'name_id_format': name_id.get('Format'),
            'attributes': attributes,
            'audience': self._get_audience(assertion),
            'not_before': self._get_condition_timestamp(assertion, 'NotBefore'),
            'not_on_or_after': self._get_condition_timestamp(assertion, 'NotOnOrAfter')
        }

    def _validate_signature(self, root: ET.Element, cert_pem: str) -> None:
        """Validate XML signature using certificate.
        
        Args:
            root: Root XML element
            cert_pem: PEM encoded certificate
            
        Raises:
            ValueError: If signature validation fails
        """
        signature = root.find(f".//{{{self.NAMESPACES['ds']}}}Signature")
        if signature is None:
            raise ValueError("No signature found in response")

        # Load certificate
        cert = load_pem_x509_certificate(cert_pem.encode())
        
        # Get signed info
        signed_info = signature.find(f".//{{{self.NAMESPACES['ds']}}}SignedInfo")
        if signed_info is None:
            raise ValueError("No SignedInfo found in signature")

        # Get signature value
        signature_value = signature.find(f".//{{{self.NAMESPACES['ds']}}}SignatureValue")
        if signature_value is None:
            raise ValueError("No SignatureValue found in signature")

        # Canonicalize SignedInfo
        signed_info_canon = ET.tostring(signed_info, method='c14n')
        
        try:
            # Verify signature
            cert.public_key().verify(
                base64.b64decode(signature_value.text),
                signed_info_canon,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
        except Exception as e:
            raise ValueError(f"Signature validation failed: {str(e)}")

    def _get_audience(self, assertion: ET.Element) -> Optional[str]:
        """Extract audience from assertion conditions.
        
        Args:
            assertion: Assertion element
            
        Returns:
            Optional[str]: Audience value if found
        """
        audience = assertion.find(
            f".//{{{self.NAMESPACES['saml']}}}Conditions//"
            f"{{{self.NAMESPACES['saml']}}}AudienceRestriction//"
            f"{{{self.NAMESPACES['saml']}}}Audience"
        )
        return audience.text if audience is not None else None

    def _get_condition_timestamp(self, assertion: ET.Element, attribute: str) -> Optional[datetime]:
        """Extract timestamp from conditions.
        
        Args:
            assertion: Assertion element
            attribute: Attribute name to extract
            
        Returns:
            Optional[datetime]: Timestamp if found
        """
        conditions = assertion.find(f".//{{{self.NAMESPACES['saml']}}}Conditions")
        if conditions is not None and attribute in conditions.attrib:
            return datetime.fromisoformat(conditions.get(attribute)) 