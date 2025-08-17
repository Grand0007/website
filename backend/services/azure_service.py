import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import json

logger = logging.getLogger(__name__)

class AzureService:
    def __init__(self):
        # Azure Storage
        self.storage_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.storage_container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "resumes")
        
        # Azure Cosmos DB
        self.cosmos_endpoint = os.getenv("AZURE_COSMOS_ENDPOINT")
        self.cosmos_key = os.getenv("AZURE_COSMOS_KEY")
        self.cosmos_database_name = os.getenv("AZURE_COSMOS_DATABASE_NAME", "ai_resume_db")
        
        # Azure Key Vault
        self.key_vault_url = os.getenv("AZURE_KEY_VAULT_URL")
        
        # Initialize clients
        self.blob_service_client = None
        self.cosmos_client = None
        self.key_vault_client = None
        
        self.initialized = False

    async def initialize(self):
        """Initialize Azure services"""
        try:
            # Initialize Blob Storage
            if self.storage_connection_string:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    self.storage_connection_string
                )
                await self._ensure_container_exists(self.storage_container_name)
                logger.info("Azure Blob Storage initialized")
            
            # Initialize Cosmos DB
            if self.cosmos_endpoint and self.cosmos_key:
                self.cosmos_client = CosmosClient(
                    url=self.cosmos_endpoint,
                    credential=self.cosmos_key
                )
                await self._ensure_cosmos_database_exists()
                logger.info("Azure Cosmos DB initialized")
            
            # Initialize Key Vault
            if self.key_vault_url:
                credential = DefaultAzureCredential()
                self.key_vault_client = SecretClient(
                    vault_url=self.key_vault_url,
                    credential=credential
                )
                logger.info("Azure Key Vault initialized")
            
            self.initialized = True
            logger.info("Azure services initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Azure services: {str(e)}")
            # Don't raise exception to allow app to run without Azure services
            self.initialized = False

    async def _ensure_container_exists(self, container_name: str):
        """Ensure blob container exists"""
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            
            # Try to get container properties
            try:
                await asyncio.to_thread(container_client.get_container_properties)
            except Exception:
                # Container doesn't exist, create it
                await asyncio.to_thread(
                    self.blob_service_client.create_container,
                    container_name,
                    public_access=None
                )
                logger.info(f"Created blob container: {container_name}")
                
        except Exception as e:
            logger.error(f"Error ensuring container exists: {str(e)}")

    async def _ensure_cosmos_database_exists(self):
        """Ensure Cosmos database and containers exist"""
        try:
            # Create database if it doesn't exist
            database = self.cosmos_client.create_database_if_not_exists(
                id=self.cosmos_database_name
            )
            
            # Create containers if they don't exist
            containers = [
                {"id": "users", "partition_key": "/id"},
                {"id": "resumes", "partition_key": "/user_id"},
                {"id": "processing_logs", "partition_key": "/resume_id"}
            ]
            
            for container_config in containers:
                database.create_container_if_not_exists(
                    id=container_config["id"],
                    partition_key=PartitionKey(path=container_config["partition_key"])
                )
            
            logger.info("Cosmos DB database and containers ensured")
            
        except Exception as e:
            logger.error(f"Error ensuring Cosmos database exists: {str(e)}")

    async def upload_file(self, file_content: bytes, filename: str, container_name: str = None) -> str:
        """Upload file to Azure Blob Storage"""
        if not self.blob_service_client:
            raise Exception("Azure Blob Storage not initialized")
        
        try:
            container_name = container_name or self.storage_container_name
            blob_name = f"{datetime.utcnow().strftime('%Y/%m/%d')}/{filename}"
            
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            # Upload file
            await asyncio.to_thread(
                blob_client.upload_blob,
                file_content,
                overwrite=True
            )
            
            logger.info(f"File uploaded to Azure Storage: {blob_name}")
            return blob_name
            
        except Exception as e:
            logger.error(f"Error uploading file to Azure Storage: {str(e)}")
            raise

    async def download_file(self, blob_name: str, container_name: str = None) -> bytes:
        """Download file from Azure Blob Storage"""
        if not self.blob_service_client:
            raise Exception("Azure Blob Storage not initialized")
        
        try:
            container_name = container_name or self.storage_container_name
            
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            # Download file
            download_stream = await asyncio.to_thread(blob_client.download_blob)
            file_content = await asyncio.to_thread(download_stream.readall)
            
            return file_content
            
        except Exception as e:
            logger.error(f"Error downloading file from Azure Storage: {str(e)}")
            raise

    async def delete_file(self, blob_name: str, container_name: str = None) -> bool:
        """Delete file from Azure Blob Storage"""
        if not self.blob_service_client:
            logger.warning("Azure Blob Storage not initialized")
            return False
        
        try:
            container_name = container_name or self.storage_container_name
            
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            # Delete file
            await asyncio.to_thread(blob_client.delete_blob)
            
            logger.info(f"File deleted from Azure Storage: {blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file from Azure Storage: {str(e)}")
            return False

    async def get_file_url(self, blob_name: str, container_name: str = None, expires_in_hours: int = 24) -> str:
        """Generate a signed URL for file access"""
        if not self.blob_service_client:
            raise Exception("Azure Blob Storage not initialized")
        
        try:
            container_name = container_name or self.storage_container_name
            
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            # Generate SAS token
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions
            
            sas_token = generate_blob_sas(
                account_name=blob_client.account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=blob_client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expires_in_hours)
            )
            
            # Construct URL
            url = f"{blob_client.url}?{sas_token}"
            return url
            
        except Exception as e:
            logger.error(f"Error generating file URL: {str(e)}")
            raise

    async def store_document(self, container_name: str, document: Dict[str, Any]) -> str:
        """Store document in Cosmos DB"""
        if not self.cosmos_client:
            logger.warning("Azure Cosmos DB not initialized")
            return ""
        
        try:
            database = self.cosmos_client.get_database_client(self.cosmos_database_name)
            container = database.get_container_client(container_name)
            
            # Add timestamp
            document["created_at"] = datetime.utcnow().isoformat()
            document["updated_at"] = datetime.utcnow().isoformat()
            
            # Create document
            response = container.create_item(body=document)
            
            logger.info(f"Document stored in Cosmos DB: {container_name}")
            return response["id"]
            
        except Exception as e:
            logger.error(f"Error storing document in Cosmos DB: {str(e)}")
            return ""

    async def get_document(self, container_name: str, document_id: str, partition_key: str) -> Optional[Dict[str, Any]]:
        """Get document from Cosmos DB"""
        if not self.cosmos_client:
            return None
        
        try:
            database = self.cosmos_client.get_database_client(self.cosmos_database_name)
            container = database.get_container_client(container_name)
            
            # Read document
            response = container.read_item(
                item=document_id,
                partition_key=partition_key
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting document from Cosmos DB: {str(e)}")
            return None

    async def query_documents(self, container_name: str, query: str, parameters: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Query documents from Cosmos DB"""
        if not self.cosmos_client:
            return []
        
        try:
            database = self.cosmos_client.get_database_client(self.cosmos_database_name)
            container = database.get_container_client(container_name)
            
            # Execute query
            items = list(container.query_items(
                query=query,
                parameters=parameters or [],
                enable_cross_partition_query=True
            ))
            
            return items
            
        except Exception as e:
            logger.error(f"Error querying documents from Cosmos DB: {str(e)}")
            return []

    async def update_document(self, container_name: str, document_id: str, updates: Dict[str, Any], partition_key: str) -> bool:
        """Update document in Cosmos DB"""
        if not self.cosmos_client:
            return False
        
        try:
            database = self.cosmos_client.get_database_client(self.cosmos_database_name)
            container = database.get_container_client(container_name)
            
            # Get existing document
            existing_doc = container.read_item(
                item=document_id,
                partition_key=partition_key
            )
            
            # Apply updates
            for key, value in updates.items():
                existing_doc[key] = value
            
            existing_doc["updated_at"] = datetime.utcnow().isoformat()
            
            # Replace document
            container.replace_item(
                item=document_id,
                body=existing_doc
            )
            
            logger.info(f"Document updated in Cosmos DB: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating document in Cosmos DB: {str(e)}")
            return False

    async def delete_document(self, container_name: str, document_id: str, partition_key: str) -> bool:
        """Delete document from Cosmos DB"""
        if not self.cosmos_client:
            return False
        
        try:
            database = self.cosmos_client.get_database_client(self.cosmos_database_name)
            container = database.get_container_client(container_name)
            
            # Delete document
            container.delete_item(
                item=document_id,
                partition_key=partition_key
            )
            
            logger.info(f"Document deleted from Cosmos DB: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document from Cosmos DB: {str(e)}")
            return False

    async def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from Azure Key Vault"""
        if not self.key_vault_client:
            return None
        
        try:
            secret = await asyncio.to_thread(
                self.key_vault_client.get_secret,
                secret_name
            )
            return secret.value
            
        except Exception as e:
            logger.error(f"Error getting secret from Key Vault: {str(e)}")
            return None

    async def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set secret in Azure Key Vault"""
        if not self.key_vault_client:
            return False
        
        try:
            await asyncio.to_thread(
                self.key_vault_client.set_secret,
                secret_name,
                secret_value
            )
            
            logger.info(f"Secret set in Key Vault: {secret_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting secret in Key Vault: {str(e)}")
            return False

    async def log_processing_activity(self, resume_id: str, activity_type: str, details: Dict[str, Any]) -> str:
        """Log AI processing activity to Cosmos DB"""
        log_entry = {
            "id": f"{resume_id}_{activity_type}_{datetime.utcnow().timestamp()}",
            "resume_id": resume_id,
            "activity_type": activity_type,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.store_document("processing_logs", log_entry)

    async def get_processing_logs(self, resume_id: str) -> List[Dict[str, Any]]:
        """Get processing logs for a resume"""
        query = "SELECT * FROM c WHERE c.resume_id = @resume_id ORDER BY c.timestamp DESC"
        parameters = [{"name": "@resume_id", "value": resume_id}]
        
        return await self.query_documents("processing_logs", query, parameters)

    def is_available(self) -> bool:
        """Check if Azure services are available"""
        return self.initialized

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Azure services"""
        health_status = {
            "blob_storage": False,
            "cosmos_db": False,
            "key_vault": False,
            "overall": False
        }
        
        try:
            # Check Blob Storage
            if self.blob_service_client:
                try:
                    containers = await asyncio.to_thread(
                        list,
                        self.blob_service_client.list_containers(max_results=1)
                    )
                    health_status["blob_storage"] = True
                except:
                    pass
            
            # Check Cosmos DB
            if self.cosmos_client:
                try:
                    databases = list(self.cosmos_client.list_databases())
                    health_status["cosmos_db"] = True
                except:
                    pass
            
            # Check Key Vault
            if self.key_vault_client:
                try:
                    # Try to list secrets (this will fail if no permissions, but connection works)
                    await asyncio.to_thread(
                        list,
                        self.key_vault_client.list_properties_of_secrets()
                    )
                    health_status["key_vault"] = True
                except:
                    # Key Vault might be accessible but no list permissions
                    health_status["key_vault"] = True
            
            # Overall health
            health_status["overall"] = any([
                health_status["blob_storage"],
                health_status["cosmos_db"],
                health_status["key_vault"]
            ])
            
        except Exception as e:
            logger.error(f"Error during Azure health check: {str(e)}")
        
        return health_status

# Initialize Azure service
azure_service = AzureService()