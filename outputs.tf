output "alb_dns_name" {
  description = "The public DNS URL of the Application Load Balancer"
  value       = "http://${aws_lb.alb.dns_name}"
}

output "s3_bucket_name" {
  description = "The name of the S3 bucket created for cloud vault"
  value       = aws_s3_bucket.vault.id
}

output "rds_endpoint" {
  description = "The connection endpoint for the MySQL RDS instance"
  value       = aws_db_instance.rds.endpoint
}
