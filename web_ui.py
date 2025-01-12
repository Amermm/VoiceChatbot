import os
import logging
from google.cloud import secretmanager

class VoiceChatBot:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Load variables
        self.config = {
            "DATABASE_EXCEL_PATH": os.getenv("DATABASE_EXCEL_PATH", "default.xlsx"),
            "ROBOTNAME": os.getenv("ROBOTNAME", "DefaultRobot"),
            "GOOGLE_CREDENTIALS": None,
            "OPENAI_API_KEY": None,
        }

        # Load secrets from GCP Secret Manager
        self.load_secrets()

    def load_secrets(self):
        """Load secrets from GCP Secret Manager."""
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

        self.config["GOOGLE_CREDENTIALS"] = self.get_secret(client, project_id, "GOOGLE_CREDENTIALS")
        self.config["OPENAI_API_KEY"] = self.get_secret(client, project_id, "OPENAI_API_KEY")

        # Save Google credentials to a temporary file
        credentials_path = "/tmp/google_credentials.json"
        with open(credentials_path, "w") as file:
            file.write(self.config["GOOGLE_CREDENTIALS"])
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        self.logger.info("Google credentials loaded successfully.")

    def get_secret(self, client, project_id, secret_name):
        """Fetch a secret from GCP Secret Manager."""
        secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": secret_path})
        return response.payload.data.decode("UTF-8")
