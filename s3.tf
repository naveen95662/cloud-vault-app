resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Private S3 Bucket for Uploaded Files
resource "aws_s3_bucket" "vault" {
  bucket        = "cloud-vault-storage-${var.environment}-${random_id.bucket_suffix.hex}"
  force_destroy = true

  tags = {
    Name = "${var.environment}-cloud-vault-bucket"
  }
}

# Block all public access to S3 (Enforce IAM-only access)
resource "aws_s3_bucket_public_access_block" "vault_access" {
  bucket = aws_s3_bucket.vault.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
