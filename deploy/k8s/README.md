# Minimal Kubernetes evidence

The AWS deployment intentionally uses Docker Compose on one EC2 instance. This
directory is the small, reproducible Kubernetes portion of the assignment: it
proves a Deployment, ClusterIP Service, Secret injection, non-root runtime,
read-only filesystem, resource limits, and health probes without paying for
Amazon EKS.

It deploys the existing gateway image only. Its `/healthz` endpoint is fully
testable without pretending that a small local cluster is the production stack.

```powershell
# Build the image from the repository root.
docker compose build gateway

# With k3d installed, create a local cluster and load the image.
k3d cluster create triageiq-demo
k3d image import triageiq-gateway:dev -c triageiq-demo

# Create the real secret outside Git, then apply the manifests.
kubectl -n triageiq-demo create secret generic triageiq-gateway-credentials `
  --from-literal=GATEWAY_HTPASSWD='replace-with-a-real-htpasswd-hash'
kubectl apply -k deploy/k8s
kubectl -n triageiq-demo rollout status deployment/gateway
kubectl -n triageiq-demo port-forward service/gateway 8080:80
```

In another terminal, verify `http://127.0.0.1:8080/healthz`, then retain the
output of `kubectl get pods,service -n triageiq-demo` as assignment evidence.
