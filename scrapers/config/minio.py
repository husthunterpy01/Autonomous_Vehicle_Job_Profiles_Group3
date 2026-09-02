import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# Import Minio config for parquet archives of scraped jobs
@dataclass(frozen=True)
class MinioConfig:
    endpoint: str = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
    access_key: str = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    secret_key: str = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
    secure: bool = os.environ.get("MINIO_SECURE", "false").lower() == "true"
    bucket: str = os.environ.get("MINIO_JOBS_BUCKET", "scraped-jobs")
    region: str = os.environ.get("MINIO_REGION", "")
