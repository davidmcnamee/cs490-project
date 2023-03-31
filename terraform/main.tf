
terraform {
  required_version = ">= 0.13"
  required_providers {
    kubectl = {
      source  = "gavinbunney/kubectl"
      version = ">= 1.7.0"
    }
  }
}

provider "kubectl" {
  config_path = "~/.kube/config"
}

provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}

resource "helm_release" "mysql_chart" {
  name             = "mysql"
  repository       = "https://charts.bitnami.com/bitnami"
  chart            = "mysql"
  version          = "9.7.0"
  namespace        = "mysql"
  create_namespace = true
  values           = [
  <<-YAML
    auth:
      username: cs490user
      database: cs490db
      existingSecret: mysql-secret
  YAML
  ]
  depends_on = [kubectl_manifest.mysql_secret]
}

resource "random_password" "mysql_passwords" {
  length  = 16
  special = false
  for_each = toset(["root", "user", "replication"])
}

resource "kubectl_manifest" "mysql_secret" {
  yaml_body = <<-YAML
    apiVersion: v1
    kind: Secret
    metadata:
      name: mysql-secret
      namespace: mysql
    type: Opaque
    data:
      mysql-root-password: ${base64encode(random_password.mysql_passwords["root"].result)}
      mysql-password: ${base64encode(random_password.mysql_passwords["user"].result)}
      mysql-replication-password: ${base64encode(random_password.mysql_passwords["replication"].result)}
  YAML
}

locals {
  mysql_host = "mysql.mysql.svc.cluster.local"
  database_url = "mysql://cs490user:${random_password.mysql_passwords["user"].result}@${local.mysql_host}:3306/cs490db"
}

output "database_url" {
  value = local.database_url
  sensitive = true
}

resource "kubectl_manifest" "cs490_ns" {
  yaml_body = <<-YAML
    apiVersion: v1
    kind: Namespace
    metadata:
      name: cs490-project
  YAML
}

resource "kubectl_manifest" "api_secret" {
  yaml_body = <<-YAML
    apiVersion: v1
    kind: Secret
    metadata:
      name: api-secret
      namespace: cs490-project
    type: Opaque
    data:
      DATABASE_URL: ${base64encode(local.database_url)}
  YAML
  depends_on = [kubectl_manifest.cs490_ns]
}

# only want this to apply once
resource "kubectl_manifest" "cs490_ssl" {
  yaml_body = <<-YAML
  apiVersion: v1
  kind: Secret
  metadata:
    name: cs490-ssl
  type: kubernetes.io/tls
  stringData:
    tls.key: "" # populated by Issuer/letsencrypt-production
    tls.crt: ""
  YAML
  lifecycle {
    ignore_changes = [yaml_body]
  }
}
