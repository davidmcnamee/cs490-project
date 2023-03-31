allow_k8s_contexts('kube-hetzner')

k8s_yaml(["k8s/deployment.yaml", "k8s/service.yaml", "k8s/ingress.yaml"])

watch_file('app.py')
docker_build('davidmc1/cs490-project', './src', platform='linux/amd64')

k8s_resource('api', port_forwards=5000)
