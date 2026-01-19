
import os
import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# Load env vars
load_dotenv()

key_id = os.getenv('AWS_ACCESS_KEY_ID')
secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')
endpoint_url = os.getenv('AWS_S3_ENDPOINT_URL')

print(f"Testing connection with:")
print(f"Key ID: {key_id}")
print(f"Bucket: {bucket_name}")
print(f"Endpoint: {endpoint_url}")

if not all([key_id, secret_key, bucket_name, endpoint_url]):
    print("ERROR: Missing one or more required environment variables.")
    exit(1)

try:
    s3 = boto3.resource(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=key_id,
        aws_secret_access_key=secret_key
    )
    
    # Try to list objects to verify permissions
    bucket = s3.Bucket(bucket_name)
    print(f"\nAttempting to access bucket '{bucket_name}'...")
    
    count = 0
    for obj in bucket.objects.limit(1):
        print(f"Found object: {obj.key}")
        count += 1
    
    print("\nSUCCESS: Connection confirmed! Credentials are valid.")
    
    # Try to upload a test file
    print("\nAttempting to upload test file...")
    s3.Object(bucket_name, 'test_connection.txt').put(Body='Hello from the verification script!')
    print("SUCCESS: Upload confirmed!")

except ClientError as e:
    print(f"\nERROR: AWS ClientError: {e}")
except Exception as e:
    print(f"\nERROR: An unexpected error occurred: {e}")
