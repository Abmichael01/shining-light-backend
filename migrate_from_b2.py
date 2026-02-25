import os
import boto3
from pathlib import Path
from botocore.config import Config

def migrate():
    # Configuration - manually set as fallback if not in environment
    # (Since we just commented them out, we'll hardcode them for this migration script)
    access_key = os.getenv('AWS_ACCESS_KEY_ID') or "005c609398fa9760000000003"
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY') or "K005Zaya1S03tDRZcfdityCvGVT7ZMM"
    bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME') or "Shining-lIght"
    endpoint_url = os.getenv('AWS_S3_ENDPOINT_URL') or "https://s3.us-east-005.backblazeb2.com"
    
    # Local media root
    base_dir = Path(__file__).resolve().parent
    local_media_root = base_dir / "media"
    
    if not local_media_root.exists():
        print(f"Creating local media directory at {local_media_root}")
        local_media_root.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to Backblaze B2 at {endpoint_url}...")
    s3 = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version='s3v4')
    )

    print(f"Fetching file list from bucket '{bucket_name}'...")
    paginator = s3.get_paginator('list_objects_v2')
    # Filter for objects starting with 'media/'
    pages = paginator.paginate(Bucket=bucket_name, Prefix='media/')

    count = 0
    skipped = 0
    errors = 0

    for page in pages:
        if 'Contents' not in page:
            continue
            
        for obj in page['Contents']:
            key = obj['Key']
            # Remove the 'media/' prefix for local path relative to our media folder
            # If the files in B2 are inside a 'media/' folder, we want to strip it
            # because our local_media_root already represents that folder.
            relative_path = key.replace('media/', '', 1) if key.startswith('media/') else key
            
            if not relative_path: # Skip the directory object itself if it exists
                continue
                
            local_file_path = local_media_root / relative_path
            
            # Ensure local subdirectories exist
            local_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                # Check if file exists and has same size
                if local_file_path.exists() and local_file_path.stat().st_size == obj['Size']:
                    # print(f"Skipping {key} (already exists)")
                    skipped += 1
                    continue
                
                print(f"Downloading: {key} -> {local_file_path}")
                s3.download_file(bucket_name, key, str(local_file_path))
                count += 1
            except Exception as e:
                print(f"Error downloading {key}: {e}")
                errors += 1

    print("\nMigration Summary:")
    print(f"------------------")
    print(f"Successfully downloaded: {count} files")
    print(f"Skipped (already exist): {skipped} files")
    print(f"Failed: {errors} files")
    print(f"------------------")
    print(f"All files are now in {local_media_root}")

if __name__ == "__main__":
    migrate()
