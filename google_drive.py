from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io
from config import SERVICE_ACCOUNT_FILE, FOLDER_ID

SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Authentification
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=credentials)

def upload_audio_to_drive(audio_bytes, file_name):
    file_metadata = {
        'name': file_name,
        'parents': [FOLDER_ID]
    }
    media = MediaIoBaseUpload(io.BytesIO(audio_bytes), mimetype='audio/ogg')
    file = drive_service.files().create(
        body=file_metadata, media_body=media, fields='id'
    ).execute()
    return file.get('id')
