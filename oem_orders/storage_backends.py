"""
Google Drive storage backend for Django
"""
import os
import io
from django.core.files.base import File
from django.core.files.storage import Storage
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import json


class GoogleDriveStorage(Storage):
    """Custom storage class for Google Drive"""

    def __init__(self):
        self._drive = None
        self.base_url = 'https://drive.google.com/uc?export=view&id='

    def _get_drive(self):
        """Initialize and return GoogleDrive instance"""
        if self._drive is None:
            gauth = GoogleAuth()

            # Load credentials
            gauth.LoadCredentialsFile("credentials.json")

            if gauth.credentials is None:
                raise Exception("No credentials found")
            elif gauth.access_token_expired:
                gauth.Refresh()
            else:
                gauth.Authorize()

            gauth.SaveCredentialsFile("credentials.json")
            self._drive = GoogleDrive(gauth)

        return self._drive

    def _save(self, name, content):
        """Save a file to Google Drive"""
        drive = self._get_drive()
        folder_id = os.environ.get('GDRIVE_FOLDER_ID', 'root')

        # Create folder structure if needed
        folder_path = os.path.dirname(name)
        if folder_path:
            folder_id = self._create_folder_structure(folder_path, folder_id)

        # Create file
        gdrive_file = drive.CreateFile({
            'title': os.path.basename(name),
            'parents': [{'id': folder_id}]
        })

        # Set content
        if hasattr(content, 'read'):
            gdrive_file.content = io.BytesIO(content.read())
        else:
            gdrive_file.SetContentString(content)

        gdrive_file.Upload()

        # Store file mapping
        self._save_file_mapping(name, gdrive_file['id'])

        return name

    def _create_folder_structure(self, path, parent_id='root'):
        """Create nested folders in Google Drive"""
        drive = self._get_drive()
        folders = path.split('/')
        current_parent = parent_id

        for folder_name in folders:
            query = f"title='{folder_name}' and '{current_parent}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            file_list = drive.ListFile({'q': query}).GetList()

            if file_list:
                current_parent = file_list[0]['id']
            else:
                folder = drive.CreateFile({
                    'title': folder_name,
                    'parents': [{'id': current_parent}],
                    'mimeType': 'application/vnd.google-apps.folder'
                })
                folder.Upload()
                current_parent = folder['id']

        return current_parent

    def _save_file_mapping(self, path, file_id):
        """Save mapping of file path to Google Drive file ID"""
        from django.conf import settings
        mapping_file = os.path.join(settings.BASE_DIR, 'gdrive_mapping.json')

        if os.path.exists(mapping_file):
            with open(mapping_file, 'r') as f:
                mapping = json.load(f)
        else:
            mapping = {}

        mapping[path] = file_id

        with open(mapping_file, 'w') as f:
            json.dump(mapping, f, indent=2)

    def _get_file_id(self, name):
        """Get Google Drive file ID from path"""
        from django.conf import settings
        mapping_file = os.path.join(settings.BASE_DIR, 'gdrive_mapping.json')

        if os.path.exists(mapping_file):
            with open(mapping_file, 'r') as f:
                mapping = json.load(f)
                return mapping.get(name)

        return None

    def exists(self, name):
        """Check if a file exists"""
        return self._get_file_id(name) is not None

    def url(self, name):
        """Return the URL to access a file"""
        file_id = self._get_file_id(name)
        if file_id:
            return f"{self.base_url}{file_id}"
        return ""

    def delete(self, name):
        """Delete a file"""
        drive = self._get_drive()
        file_id = self._get_file_id(name)

        if file_id:
            gdrive_file = drive.CreateFile({'id': file_id})
            gdrive_file.Trash()

    def size(self, name):
        """Return file size"""
        drive = self._get_drive()
        file_id = self._get_file_id(name)

        if file_id:
            gdrive_file = drive.CreateFile({'id': file_id})
            return int(gdrive_file.get('fileSize', 0))

        return 0
