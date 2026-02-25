"""S3 uploader for publishing static content to AWS S3."""

import mimetypes
from typing import Optional

import boto3
import config
from botocore.exceptions import ClientError


class S3Uploader:
    """Handles uploading static files to AWS S3."""

    def __init__(self, bucket_name: str = None, region: str = None):
        """Initialize the S3 uploader.

        Args:
            bucket_name: S3 bucket name
            region: AWS region
        """
        self.bucket_name = bucket_name or config.S3_BUCKET_NAME
        self.region = region or config.S3_REGION

        # Initialize S3 client
        try:
            self.s3_client = boto3.client("s3", region_name=self.region)
        except Exception as e:
            print(f"Warning: Could not initialize S3 client: {e}")
            self.s3_client = None

    def upload_html(
        self, html_content: str, s3_key: str, cache_control: str = "max-age=3600"
    ) -> bool:
        """Upload HTML content to S3.

        Args:
            html_content: HTML content string
            s3_key: S3 key (path) for the file
            cache_control: Cache-Control header value

        Returns:
            True if successful, False otherwise
        """
        if not self.s3_client:
            print(
                f"S3 client not initialized. Would upload to: s3://{self.bucket_name}/{s3_key}"
            )
            return False

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=html_content.encode("utf-8"),
                ContentType="text/html",
                CacheControl=cache_control,
                ACL="public-read",  # Make publicly accessible
            )
            print(f"Uploaded: s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            print(f"Error uploading to S3: {e}")
            return False

    def upload_file(
        self, file_path: str, s3_key: str = None, content_type: str = None
    ) -> bool:
        """Upload a file to S3.

        Args:
            file_path: Local file path
            s3_key: S3 key (path) for the file. If None, uses file_path
            content_type: MIME type. If None, will be guessed from file extension

        Returns:
            True if successful, False otherwise
        """
        if not self.s3_client:
            print(f"S3 client not initialized. Would upload: {file_path}")
            return False

        if s3_key is None:
            s3_key = file_path

        if content_type is None:
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=f,
                    ContentType=content_type,
                    ACL="public-read",
                )
            print(f"Uploaded file: s3://{self.bucket_name}/{s3_key}")
            return True
        except (ClientError, IOError) as e:
            print(f"Error uploading file to S3: {e}")
            return False

    def delete_file(self, s3_key: str) -> bool:
        """Delete a file from S3.

        Args:
            s3_key: S3 key of the file to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.s3_client:
            print(f"S3 client not initialized. Would delete: {s3_key}")
            return False

        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            print(f"Deleted: s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            print(f"Error deleting from S3: {e}")
            return False

    def file_exists(self, s3_key: str) -> bool:
        """Check if a file exists in S3.

        Args:
            s3_key: S3 key to check

        Returns:
            True if file exists, False otherwise
        """
        if not self.s3_client:
            return False

        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

    def get_public_url(self, s3_key: str) -> str:
        """Get the public URL for an S3 object.

        Args:
            s3_key: S3 key

        Returns:
            Public URL string
        """
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
