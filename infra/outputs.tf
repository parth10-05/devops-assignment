output "frontend_url" {
  description = "Public HTTPS URL to submit after the first GitHub Actions deployment."
  value       = "https://${aws_cloudfront_distribution.site.domain_name}"
}

output "frontend_bucket" {
  description = "Private S3 bucket used by CI for frontend files and release bundles."
  value       = aws_s3_bucket.frontend.bucket
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.site.id
}

output "ec2_instance_id" {
  value = aws_instance.app.id
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}

output "parameter_prefix" {
  value = local.parameter_prefix
}
