"""
Encryption utilities for VeritasAI Legal Research System
Provides secure encryption/decryption for user data, queries, and results
"""

import os
import base64
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Dict, Any, Optional, Union
from common.logging import logger
from common.config import Config
import json

class EncryptionManager:
    """Manages encryption and decryption of sensitive data"""
    
    def __init__(self):
        self.encryption_key = self._get_or_create_key()
        try:
            self.cipher_suite = Fernet(self.encryption_key)
        except Exception as e:
            logger.error(f"Failed to create cipher suite: {e}")
            # Generate a fresh key
            self.encryption_key = Fernet.generate_key()
            self.cipher_suite = Fernet(self.encryption_key)
    
    def _get_or_create_key(self) -> bytes:
        """Get encryption key from config or create new one"""
        encryption_key_str = Config.ENCRYPTION_KEY
        
        if not encryption_key_str:
            logger.warning("No encryption key found in config, generating new one")
            key = Fernet.generate_key()
            logger.warning("IMPORTANT: Save this key to ENCRYPTION_KEY environment variable")
            logger.warning(f"Generated key: {key.decode()}")
            return key
        
        try:
            # The key should already be in the correct format (base64 encoded bytes)
            if isinstance(encryption_key_str, str):
                return encryption_key_str.encode()
            return encryption_key_str
        except Exception as e:
            logger.error(f"Invalid encryption key format: {e}")
            # Generate new key
            key = Fernet.generate_key()
            logger.warning(f"Generated new key: {key.decode()}")
            return key
    
    def encrypt_data(self, data: Union[str, Dict[str, Any]]) -> str:
        """Encrypt data and return base64 encoded string"""
        try:
            if isinstance(data, dict):
                data_str = json.dumps(data)
            else:
                data_str = str(data)
            
            encrypted_data = self.cipher_suite.encrypt(data_str.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise ValueError(f"Failed to encrypt data: {e}")
    
    def decrypt_data(self, encrypted_data: str) -> Union[str, Dict[str, Any]]:
        """Decrypt base64 encoded data"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
            data_str = decrypted_data.decode()
            
            # Try to parse as JSON, fallback to string
            try:
                return json.loads(data_str)
            except json.JSONDecodeError:
                return data_str
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise ValueError(f"Failed to decrypt data: {e}")
    
    def encrypt_user_query(self, query: str, user_id: str) -> Dict[str, str]:
        """Encrypt user query with metadata"""
        query_data = {
            "query": query,
            "user_id": user_id,
            "timestamp": str(datetime.utcnow()),
            "type": "user_query"
        }
        return {
            "encrypted_data": self.encrypt_data(query_data),
            "encryption_version": "1.0"
        }
    
    def decrypt_user_query(self, encrypted_query: Dict[str, str]) -> Dict[str, Any]:
        """Decrypt user query"""
        return self.decrypt_data(encrypted_query["encrypted_data"])
    
    def encrypt_analysis_result(self, result: Dict[str, Any], user_id: str) -> Dict[str, str]:
        """Encrypt analysis result with metadata"""
        result_data = {
            "result": result,
            "user_id": user_id,
            "timestamp": str(datetime.utcnow()),
            "type": "analysis_result"
        }
        return {
            "encrypted_data": self.encrypt_data(result_data),
            "encryption_version": "1.0"
        }
    
    def decrypt_analysis_result(self, encrypted_result: Dict[str, str]) -> Dict[str, Any]:
        """Decrypt analysis result"""
        return self.decrypt_data(encrypted_result["encrypted_data"])
    
    def encrypt_pdf_content(self, pdf_content: bytes, filename: str, user_id: str) -> Dict[str, str]:
        """Encrypt PDF content"""
        pdf_data = {
            "content": base64.b64encode(pdf_content).decode(),
            "filename": filename,
            "user_id": user_id,
            "timestamp": str(datetime.utcnow()),
            "type": "pdf_content"
        }
        return {
            "encrypted_data": self.encrypt_data(pdf_data),
            "encryption_version": "1.0"
        }
    
    def decrypt_pdf_content(self, encrypted_pdf: Dict[str, str]) -> Dict[str, Any]:
        """Decrypt PDF content"""
        return self.decrypt_data(encrypted_pdf["encrypted_data"])

class SecureDataStorage:
    """Secure data storage with encryption"""
    
    def __init__(self):
        self.encryption_manager = EncryptionManager()
    
    def store_user_query(self, user_id: str, query: str) -> Dict[str, str]:
        """Store encrypted user query"""
        encrypted_query = self.encryption_manager.encrypt_user_query(query, user_id)
        return encrypted_query
    
    def retrieve_user_query(self, encrypted_query: Dict[str, str]) -> Dict[str, Any]:
        """Retrieve and decrypt user query"""
        return self.encryption_manager.decrypt_user_query(encrypted_query)
    
    def store_analysis_result(self, user_id: str, result: Dict[str, Any]) -> Dict[str, str]:
        """Store encrypted analysis result"""
        encrypted_result = self.encryption_manager.encrypt_analysis_result(result, user_id)
        return encrypted_result
    
    def retrieve_analysis_result(self, encrypted_result: Dict[str, str]) -> Dict[str, Any]:
        """Retrieve and decrypt analysis result"""
        return self.encryption_manager.decrypt_analysis_result(encrypted_result)
    
    def store_pdf_data(self, user_id: str, pdf_content: bytes, filename: str) -> Dict[str, str]:
        """Store encrypted PDF data"""
        encrypted_pdf = self.encryption_manager.encrypt_pdf_content(pdf_content, filename, user_id)
        return encrypted_pdf
    
    def retrieve_pdf_data(self, encrypted_pdf: Dict[str, str]) -> Dict[str, Any]:
        """Retrieve and decrypt PDF data"""
        return self.encryption_manager.decrypt_pdf_content(encrypted_pdf)

# Global instances
encryption_manager = EncryptionManager()
secure_storage = SecureDataStorage()

# Utility functions for easy integration
def encrypt_sensitive_data(data: Union[str, Dict[str, Any]]) -> str:
    """Encrypt sensitive data"""
    return encryption_manager.encrypt_data(data)

def decrypt_sensitive_data(encrypted_data: str) -> Union[str, Dict[str, Any]]:
    """Decrypt sensitive data"""
    return encryption_manager.decrypt_data(encrypted_data)

def encrypt_user_data(data: Dict[str, Any], user_id: str, data_type: str) -> Dict[str, str]:
    """Encrypt user data with metadata"""
    data_with_metadata = {
        **data,
        "user_id": user_id,
        "timestamp": str(datetime.utcnow()),
        "type": data_type
    }
    return {
        "encrypted_data": encryption_manager.encrypt_data(data_with_metadata),
        "encryption_version": "1.0"
    }

def decrypt_user_data(encrypted_data: Dict[str, str]) -> Dict[str, Any]:
    """Decrypt user data"""
    return encryption_manager.decrypt_data(encrypted_data["encrypted_data"])
