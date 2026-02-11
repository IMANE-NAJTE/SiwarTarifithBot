# config.py

import os

BOT_TOKEN = os.getenv("BOT_TOKEN")  # récupérer depuis Render secrets
FOLDER_ID = os.getenv("FOLDER_ID")  # ID du dossier Google Drive
SERVICE_ACCOUNT_FILE = "credentialsjson"
