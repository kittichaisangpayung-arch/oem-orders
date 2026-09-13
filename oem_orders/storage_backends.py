"""
Google Drive storage backend for Django
"""
import os
import io
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.decoding import force_str
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import tempfile
import json


class GoogleDriveStorage(Storage):
    """
    Custom storage class for Google Drive
    """

    def __init__(self):
        self._drive = None
        self.base_url = 'https://drive.google.com/uc?export=view&id='

    def _get_drive(self):
        """Initialize and return GoogleDrive instance"""
        if self._drive is None:
            gauth = GoogleAuth()

            # Try to load credentials from environment variable
            credentials_json = os.environ.get('GDRIVE_CREDENTIALS_JSON', '')

            if credentials_json:
                # Create temporary settings file
                settings = {
                    "client_config_backend": "settings",
                    "client_config": json.loads(credentials_json),
                    "save_credentials": True,
                    "save_credentials_backend": "file",
                    "save_credentials_file": "credentials.json",
                    "get_refresh_token": True,
                    "oauth_scope": ["https://www.googleapis.com/auth/drive"]
                }

                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
                    import yaml
                    yaml.dump(settings, f)
                    settings_file = f.name

                gauth.settings_file = settings_file

            # Load credentials or authenticate
            gauth.LoadCredentialsFile("credentials.json")

            if gauth.credentials is None:
                gauth.LocalWebserverAuth()
            elif gauth.access_token_expired:
                gauth.Refresh()
            else:
                gauth.Authorize()

            gauth.SaveCredentialsFile("credentials.json")
            self._drive = GoogleDrive(gauth)

        return self._drive

    def _open(self, name, mode='rb'):
        """Open a file from Google Drive"""
        drive = self._get_drive()
        file_id = self._get_file_id(name)

        if file_id:
            gdrive_file = drive.CreateFile({'id': file_id})
            content = gdrive_file.GetContentString()
            return File(io.BytesIO(content.encode()), name=name)

        raise FileNotFoundError(f"File {name} not found in Google Drive")

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

        # Store file mapping (file path -> file ID)
        self._save_file_mapping(name, gdrive_file['id'])

        return name

    def _create_folder_structure(self, path, parent_id='root'):
        """Create nested folders in Google Drive"""
        drive = self._get_drive()
        folders = path.split('/')
        current_parent = parent_id

        for folder_name in folders:
            # Check if folder exists
            query = f"title='{folder_name}' and '{current_parent}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            file_list = drive.ListFile({'q': query}).GetList()

            if file_list:
                current_parent = file_list[0]['id']
            else:
                # Create folder
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
        mapping_file = 'gdrive_mapping.json'

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
        mapping_file = 'gdrive_mapping.json'

        if os.path.exists(mapping_file):
            with open(mapping_file, 'r') as f:
                mapping = json.load(f)
                return mapping.get(name)

        return None

    def delete(self, name):
        """Delete a file from Google Drive"""
        drive = self._get_drive()
        file_id = self._get_file_id(name)

        if file_id:
            gdrive_file = drive.CreateFile({'id': file_id})
            gdrive_file.Trash()

    def exists(self, name):
        """Check if a file exists in Google Drive"""
        return self._get_file_id(name) is not None

    def listdir(self, path):
        """List contents of a directory"""
        drive = self._get_drive()
        folder_id = os.environ.get('GDRIVE_FOLDER_ID', 'root')

        if path:
            folder_id = self._get_folder_id(path, folder_id)

        if not folder_id:
            return [], []

        query = f"'{folder_id}' in parents and trashed=false"
        file_list = drive.ListFile({'q': query}).GetList()

        directories = []
        files = []

        for item in file_list:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                directories.append(item['title'])
            else:
                files.append(item['title'])

        return directories, files

    def size(self, name):
        """Return the size of a file"""
        drive = self._get_drive()
        file_id = self._get_file_id(name)

        if file_id:
            gdrive_file = drive.CreateFile({'id': file_id})
            return int(gdrive_file.get('fileSize', 0))

        return 0

    def url(self, name):
        """Return the URL to access a file"""
        file_id = self._get_file_id(name)

        if file_id:
            return f"{self.base_url}{file_id}"

        return ""

    def _get_folder_id(self, path, parent_id='root'):
        """Get folder ID from path"""
        drive = self._get_drive()
        folders = path.split('/')
        current_parent = parent_id

        for folder_name in folders:
            query = f"title='{folder_name}' and '{current_parent}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            file_list = drive.ListFile({'q': query}).GetList()

            if file_list:
                current_parent = file_list[0]['id']
            else:
                return None

        return current_parent

    def get_accessed_time(self, name):
        """Return the last accessed time"""
        return self.get_modified_time(name)

    def get_created_time(self, name):
        """Return the creation time"""
        drive = self._get_drive()
        file_id = self._get_file_id(name)

        if file_id:
            gdrive_file = drive.CreateFile({'id': file_id})
            from datetime import datetime
            return datetime.strptime(gdrive_file['createdDate'], '%Y-%m-%dT%H:%M:%S.%fZ')

        return None

    def get_modified_time(self, name):
        """Return the last modified time"""
        drive = self._get_drive()
        file_id = self._get_file_id(name)

        if file_id:
            gdrive_file = drive.CreateFile({'id': file_id})
            from datetime import datetime
            return datetime.strptime(gdrive_file['modifiedDate'], '%Y-%m-%dT%H:%M:%S.%fZ')

        return None
