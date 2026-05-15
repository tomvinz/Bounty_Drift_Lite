terraform {
  required_version = ">= 1.5.0"
}

resource "null_resource" "k3d_cluster" {
  provisioner "local-exec" {
    command = <<EOT
k3d cluster create ${var.cluster_name} \
  --agents 1 \
  --servers 1 \
  --port "8081:80@loadbalancer" || true
EOT
  }
}

resource "null_resource" "install_argocd" {
  depends_on = [null_resource.k3d_cluster]

  provisioner "local-exec" {
    command = <<EOT
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

kubectl wait --for=condition=available deployment/argocd-server \
  -n argocd \
  --timeout=300s
EOT
  }
}

resource "null_resource" "prepare_argocd_application" {
  depends_on = [null_resource.install_argocd]

  provisioner "local-exec" {
    command = <<EOT
sed "s/YOUR_GITHUB_USERNAME/${var.github_username}/g" ../argocd/application.yaml > /tmp/driftbounty-argocd-app.yaml
kubectl apply -f /tmp/driftbounty-argocd-app.yaml
EOT
  }
}
