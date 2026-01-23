"""
Google Drive Service - OAuth2 Version
Uploads files to your personal Google Drive
"""

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import os
import pickle
import logging

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """Service for uploading files to Google Drive using OAuth2"""
    
    # Scopes required
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self):
        """Initialize Google Drive service with OAuth2 credentials"""
        
        # Paths
        self.credentials_file = 'credentials.json'  # OAuth2 credentials
        self.token_file = 'token.pickle'  # Saved token
        
        # Your Google Drive folder ID (optional - leave empty for root)
        self.folder_id = os.getenv('DRIVE_FOLDER_ID', '1fE8WGtnBlDVlnaJMUNGgk1W37rgjppSX')
        
        # Get authenticated service
        self.service = self._get_service()
        logger.info("Google Drive service initialized successfully")
    
    def _get_service(self):
        """Get authenticated Google Drive service"""
        
        creds = None
        
        # Check if token already exists
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Refresh expired token
                creds.refresh(Request())
            else:
                # First time authentication
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file '{self.credentials_file}' not found. "
                        "Please download OAuth2 credentials from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, 
                    self.SCOPES
                )
                
                # Run local server for authentication
                # This will open a browser window for you to authorize
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for next time
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        # Build and return service
        return build('drive', 'v3', credentials=creds)
    
    def upload_file(
        self, 
        file_path: str, 
        filename: str, 
        mime_type: str = None,
        folder_id: str = None
    ) -> dict:
        """
        Upload file to Google Drive
        
        Args:
            file_path: Path to the file to upload
            filename: Name for the file in Drive
            mime_type: MIME type of the file
            folder_id: Optional folder ID (uses default if not provided)
            
        Returns:
            dict: File info including ID and URLs
        """
        
        try:
            # Auto-detect mime type if not provided
            if mime_type is None:
                mime_type = self._get_mime_type(filename)
            
            # Use provided folder_id or default
            target_folder = folder_id or self.folder_id
            
            # File metadata
            file_metadata = {'name': filename}
            
            # Add folder if specified
            if target_folder:
                file_metadata['parents'] = [target_folder]
            
            # Upload file
            media = MediaFileUpload(
                file_path,
                mimetype=mime_type,
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, webContentLink, mimeType, size'
            ).execute()
            
            # Make file publicly readable (optional)
            self._make_public(file['id'])
            
            logger.info(f"File uploaded successfully: {file['name']} (ID: {file['id']})")
            
            return {
                'file_id': file['id'],
                'name': file['name'],
                'view_link': file.get('webViewLink'),
                'download_link': file.get('webContentLink'),
                'mime_type': file.get('mimeType'),
                'size': file.get('size')
            }
            
        except HttpError as e:
            logger.error(f"Google Drive API error: {e}")
            raise Exception(f"Failed to upload file to Google Drive: {e}")
        
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file from Google Drive"""
        
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"File deleted successfully: {file_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            return False
    
    def get_file_info(self, file_id: str) -> dict:
        """Get information about a file"""
        
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='id, name, webViewLink, webContentLink, mimeType, size'
            ).execute()
            
            return {
                'file_id': file['id'],
                'name': file['name'],
                'view_link': file.get('webViewLink'),
                'download_link': file.get('webContentLink'),
                'mime_type': file.get('mimeType'),
                'size': file.get('size')
            }
            
        except HttpError as e:
            logger.error(f"Error getting file info {file_id}: {e}")
            raise
    
    def create_folder(self, folder_name: str, parent_folder_id: str = None) -> str:
        """Create a folder in Google Drive and return its ID"""
        
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            logger.info(f"Folder created: {folder_name} (ID: {folder['id']})")
            return folder['id']
            
        except HttpError as e:
            logger.error(f"Error creating folder: {e}")
            raise
    
    def _make_public(self, file_id: str):
        """Make file publicly accessible (anyone with link can view)"""
        
        try:
            self.service.permissions().create(
                fileId=file_id,
                body={
                    'type': 'anyone',
                    'role': 'reader'
                }
            ).execute()
            
        except HttpError as e:
            logger.warning(f"Could not make file public: {e}")
    
    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type based on file extension"""
        
        extension = filename.lower().split('.')[-1]
        
        mime_types = {
            'pdf': 'application/pdf',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'ppt': 'application/vnd.ms-powerpoint',
            'txt': 'text/plain',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }
        
        return mime_types.get(extension, 'application/octet-stream')


# Singleton instance - will be created when first imported
_drive_service_instance = None

def get_drive_service():
    """Get or create the Drive service singleton"""
    global _drive_service_instance
    
    if _drive_service_instance is None:
        _drive_service_instance = GoogleDriveService()
    
    return _drive_service_instance


# For backward compatibility
drive_service = get_drive_service()