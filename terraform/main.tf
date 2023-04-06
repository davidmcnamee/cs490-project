
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

resource "kubectl_manifest" "docker_credentials" {
  yaml_body = <<-YAML
    apiVersion: v1
    kind: Secret
    metadata:
      name: docker-credentials
      namespace: cs490-project
    data:
      config.json: ${base64encode(file("~/.docker/config.json"))}
  YAML
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

resource "helm_release" "argocd_chart" {
  name             = "argo-cd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = "5.27.5"
  namespace        = "argo-cd"
  create_namespace = true
  values           = [
  ]
}

resource "helm_release" "redis_chart" {
  name             = "redis"
  repository       = "https://charts.bitnami.com/bitnami"
  chart            = "redis-cluster"
  version          = "8.4.3"
  namespace        = "redis"
  create_namespace = true
  values           = [
    <<-YAML
    usePassword: false
    YAML
  ]
}


resource "kubectl_manifest" "argocd_ingress" {
  yaml_body = <<-YAML
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: argocd-ingress
      namespace: argo-cd
      annotations:
        kubernetes.io/ingress.class: nginx
        nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
        cert-manager.io/cluster-issuer: letsencrypt-production
        nginx.ingress.kubernetes.io/ssl-passthrough: "true"
        nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
    spec:
      ingressClassName: nginx
      tls: 
      - secretName: argocd-ssl
        hosts:
          - 'argocd.mcnamee.io'
      rules:
      - host: 'argocd.mcnamee.io'
        http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: argo-cd-argocd-server
                port:
                  name: https
  YAML
  depends_on = [kubectl_manifest.argocd_ssl]
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

variable "github_ci_token" {
  type = string
  sensitive = true
}

resource "kubectl_manifest" "github_ci_token" {
  yaml_body = <<-YAML
    apiVersion: v1
    kind: Secret
    metadata:
      name: github-ci-token
      namespace: cs490-project
    stringData:
      token: ${var.github_ci_token}
      secret: random-string-data
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
variable "price_api_token" {
  type = string
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
      PRICE_API_TOKEN: ${base64encode(var.price_api_token)}
  YAML
  depends_on = [kubectl_manifest.cs490_ns]
}

# only want this to apply once (thus keeping this in terraform)
resource "kubectl_manifest" "argocd_ssl" {
  yaml_body = <<-YAML
  apiVersion: v1
  kind: Secret
  metadata:
    name: argocd-ssl
    namespace: argo-cd
  type: kubernetes.io/tls
  stringData:
    tls.key: "" # populated by Issuer/letsencrypt-production
    tls.crt: ""
  YAML
  lifecycle {
    ignore_changes = [yaml_body]
  }
  depends_on = [helm_release.argocd_chart]
}

# only want this to apply once (thus keeping this in terraform)
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
