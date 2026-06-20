import os
import json
import csv
from datetime import datetime

class S3Client:
    def __init__(self):
        # We will store files in a simulated directory inside the backend folder
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 's3_storage_mock'))
        os.makedirs(self.base_dir, exist_ok=True)
        # Create directories for default bucket
        self.bucket_name = 'graphshield-storage-bucket'
        self.bucket_dir = os.path.join(self.base_dir, self.bucket_name)
        os.makedirs(self.bucket_dir, exist_ok=True)

    def _resolve_path(self, bucket, key):
        # Cleans up key and resolves absolute path
        clean_key = key.lstrip('/')
        full_path = os.path.abspath(os.path.join(self.base_dir, bucket, clean_key))
        # Ensure we stay within s3_storage_mock
        if not full_path.startswith(self.base_dir):
            raise ValueError("Path traversal attack detected")
        return full_path

    def upload_file(self, bucket, key, content):
        """
        Upload content to simulated S3.
        content can be string, bytes, dictionary (for JSON), or list of dicts (for CSV).
        """
        path = self._resolve_path(bucket, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if isinstance(content, bytes):
            with open(path, 'wb') as f:
                f.write(content)
        elif isinstance(content, dict):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=4)
        elif isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict):
            # Save list of dicts as CSV
            keys = content[0].keys()
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(content)
        else:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(str(content))
        
        print(f"[S3 MOCK UPLOAD] s3://{bucket}/{key} -> Saved to {path}")
        return f"s3://{bucket}/{key}"

    def download_file(self, bucket, key, as_json=False):
        """
        Download content from simulated S3.
        """
        path = self._resolve_path(bucket, key)
        if not os.path.exists(path):
            return None
            
        if as_json:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()

    def log_orchestrator(self, message):
        """
        Appends runtime log to administrative_logs/orchestrator_runtime.log
        """
        log_key = "administrative_logs/orchestrator_runtime.log"
        path = self._resolve_path(self.bucket_name, log_key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        timestamp = datetime.utcnow().isoformat()
        log_line = f"[{timestamp}] {message}\n"
        
        with open(path, 'a', encoding='utf-8') as f:
            f.write(log_line)
        print(f"[S3 ORCHESTRATOR LOG] {message}")

# Singleton instance
s3_client_instance = S3Client()

def get_s3_client():
    return s3_client_instance
