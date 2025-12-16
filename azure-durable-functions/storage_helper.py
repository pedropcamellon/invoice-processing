"""
Storage helper module for Azure Blob Storage operations with Azurite.
Provides utility functions for uploading PDFs, page images, and retrieving blob URLs.
"""

import os
import logging
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError

# Configure logging
logger = logging.getLogger(__name__)

# Azurite default connection string (full format)
AZURITE_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
    "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
)

# Container names
PDF_CONTAINER = "pdfs"
IMAGE_CONTAINER = "images"


def get_blob_service_client() -> BlobServiceClient:
    """
    Get a BlobServiceClient connected to Azurite local storage emulator.
    
    Returns:
        BlobServiceClient: Client for interacting with blob storage
    """
    # First check environment variable, then fall back to default
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", AZURITE_CONNECTION_STRING)
    logger.info("[STORAGE] Connecting to blob storage...")
    return BlobServiceClient.from_connection_string(connection_string)


def ensure_container_exists(container_name: str = PDF_CONTAINER) -> None:
    """
    Ensure the specified container exists in blob storage.
    Creates it if it doesn't exist.
    
    Args:
        container_name: Name of the container to ensure exists
    """
    try:
        blob_service_client = get_blob_service_client()
        container_client = blob_service_client.get_container_client(container_name)
        
        # Try to get container properties (will fail if doesn't exist)
        try:
            container_client.get_container_properties()
            logger.info(f"[STORAGE] Container '{container_name}' already exists")
        except Exception:
            # Container doesn't exist, create it
            container_client.create_container()
            logger.info(f"[STORAGE] Created container '{container_name}'")
            
    except ResourceExistsError:
        logger.info(f"[STORAGE] Container '{container_name}' already exists (race condition)")
    except Exception as e:
        logger.error(f"[STORAGE] Error ensuring container exists: {str(e)}")
        raise


def upload_pdf_to_storage(pdf_data: bytes, pdf_id: str) -> str:
    """
    Upload a PDF file to blob storage.
    
    Args:
        pdf_data: Raw PDF file bytes
        pdf_id: Unique identifier for the PDF (typically filename without extension)
        
    Returns:
        str: Blob URL where the PDF was uploaded
    """
    try:
        blob_service_client = get_blob_service_client()
        
        # Construct blob path: pdfs/{pdf_id}.pdf
        blob_name = f"{pdf_id}.pdf"
        blob_client = blob_service_client.get_blob_client(
            container=PDF_CONTAINER,
            blob=blob_name
        )
        
        # Upload PDF
        logger.info(f"[STORAGE] Uploading PDF to {blob_name} ({len(pdf_data)} bytes)")
        blob_client.upload_blob(pdf_data, overwrite=True)
        
        # Return the blob URL
        blob_url = get_azurite_url(blob_name)
        logger.info(f"[STORAGE] PDF uploaded successfully: {blob_url}")
        return blob_url
        
    except Exception as e:
        logger.error(f"[STORAGE] Error uploading PDF: {str(e)}")
        raise


def upload_page_image(image_data: bytes, pdf_id: str, page_num: int) -> str:
    """
    Upload a page image to blob storage.
    
    Args:
        image_data: Raw PNG image bytes
        pdf_id: PDF identifier (parent document)
        page_num: Page number (0-indexed)
        
    Returns:
        str: Blob URL where the image was uploaded
    """
    try:
        blob_service_client = get_blob_service_client()
        
        # Construct blob path: images/{pdf_id}/page_{num}.png
        blob_name = f"{pdf_id}/page_{page_num}.png"
        blob_client = blob_service_client.get_blob_client(
            container=IMAGE_CONTAINER,
            blob=blob_name
        )
        
        # Upload image
        logger.info(f"[STORAGE] Uploading page image to {blob_name} ({len(image_data)} bytes)")
        blob_client.upload_blob(image_data, overwrite=True)
        
        # Return the blob URL
        blob_url = get_azurite_url(blob_name, container_name=IMAGE_CONTAINER)
        logger.info(f"[STORAGE] Page image uploaded successfully: {blob_url}")
        return blob_url
        
    except Exception as e:
        logger.error(f"[STORAGE] Error uploading page image: {str(e)}")
        raise


def download_blob(blob_url: str) -> bytes:
    """
    Download blob data from storage.
    
    Args:
        blob_url: Full blob URL (Azurite URL format)
        
    Returns:
        bytes: Raw blob data
    """
    try:
        # Extract container and blob name from URL
        # Format: http://127.0.0.1:10000/devstoreaccount1/{container}/{blob_name}
        # Try pdfs container first
        if f"/{PDF_CONTAINER}/" in blob_url:
            parts = blob_url.split(f"/{PDF_CONTAINER}/")
            container_name = PDF_CONTAINER
        elif f"/{IMAGE_CONTAINER}/" in blob_url:
            parts = blob_url.split(f"/{IMAGE_CONTAINER}/")
            container_name = IMAGE_CONTAINER
        else:
            raise ValueError(f"Invalid blob URL format (no recognized container): {blob_url}")
        
        if len(parts) != 2:
            raise ValueError(f"Invalid blob URL format: {blob_url}")
        
        blob_name = parts[1]
        
        blob_service_client = get_blob_service_client()
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        logger.info(f"[STORAGE] Downloading blob: {container_name}/{blob_name}")
        blob_data = blob_client.download_blob().readall()
        logger.info(f"[STORAGE] Downloaded {len(blob_data)} bytes from {blob_name}")
        
        return blob_data
        
    except Exception as e:
        logger.error(f"[STORAGE] Error downloading blob: {str(e)}")
        raise


def get_azurite_url(blob_name: str, container_name: str = PDF_CONTAINER) -> str:
    """
    Construct an Azurite blob URL.
    
    Args:
        blob_name: Name/path of the blob
        container_name: Container name (default: pdfs)
        
    Returns:
        str: Full Azurite blob URL
    """
    # Azurite default blob endpoint
    # Format: http://127.0.0.1:10000/devstoreaccount1/{container}/{blob}
    return f"http://127.0.0.1:10000/devstoreaccount1/{container_name}/{blob_name}"


def list_blobs_in_folder(folder_prefix: str) -> list[str]:
    """
    List all blobs with a given prefix (folder path).
    
    Args:
        folder_prefix: Folder path prefix (e.g., "invoice_123/")
        
    Returns:
        list[str]: List of blob URLs matching the prefix
    """
    try:
        blob_service_client = get_blob_service_client()
        container_client = blob_service_client.get_container_client(PDF_CONTAINER)
        
        logger.info(f"[STORAGE] Listing blobs with prefix: {folder_prefix}")
        
        blob_urls = []
        blob_list = container_client.list_blobs(name_starts_with=folder_prefix)
        
        for blob in blob_list:
            blob_url = get_azurite_url(blob.name)
            blob_urls.append(blob_url)
        
        logger.info(f"[STORAGE] Found {len(blob_urls)} blobs")
        return blob_urls
        
    except Exception as e:
        logger.error(f"[STORAGE] Error listing blobs: {str(e)}")
        raise
