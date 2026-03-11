output "platform_admin_role_arn" {
  value = aws_iam_role.platform_admin.arn
}

output "team_developer_role_arn" {
  value = aws_iam_role.team_developer.arn
}

output "github_actions_role_arn" {
  value = var.create_github_oidc ? aws_iam_role.github_actions[0].arn : ""
}
