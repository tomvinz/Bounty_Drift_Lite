import os
import time
import yaml

from kubernetes import client, config
from github_client import GitHubClient


WATCH_NAMESPACE = os.getenv("WATCH_NAMESPACE", "demo")
EXPECTED_CONFIGMAP = os.getenv("EXPECTED_CONFIGMAP", "expected-state")
EXPECTED_CONFIGMAP_KEY = os.getenv("EXPECTED_CONFIGMAP_KEY", "demo-nginx.yaml")
SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "30"))


class DriftDetector:
    def __init__(self):
        print("Initializing DriftDetector...", flush=True)

        self.load_kubernetes_config()

        print("Creating Kubernetes API clients...", flush=True)
        self.apps_api = client.AppsV1Api()
        self.core_api = client.CoreV1Api()

        print("Creating GitHub client...", flush=True)
        self.github = GitHubClient()

        print("DriftDetector initialized successfully", flush=True)

    def load_kubernetes_config(self):
        print("Trying to load in-cluster Kubernetes config...", flush=True)

        try:
            config.load_incluster_config()
            print("Loaded in-cluster Kubernetes config", flush=True)
        except Exception as error:
            print(f"In-cluster config failed: {error}", flush=True)
            print("Trying local kubeconfig...", flush=True)

            config.load_kube_config()
            print("Loaded local kubeconfig", flush=True)

    def get_expected_manifest(self):
        print(
            f"Reading expected ConfigMap {EXPECTED_CONFIGMAP} "
            f"in namespace {WATCH_NAMESPACE}...",
            flush=True,
        )

        configmap = self.core_api.read_namespaced_config_map(
            name=EXPECTED_CONFIGMAP,
            namespace=WATCH_NAMESPACE,
        )

        manifest_text = configmap.data.get(EXPECTED_CONFIGMAP_KEY)

        if not manifest_text:
            raise ValueError(
                f"Key {EXPECTED_CONFIGMAP_KEY} not found in ConfigMap {EXPECTED_CONFIGMAP}"
            )

        return yaml.safe_load(manifest_text)

    def get_actual_deployment(self, name: str):
        print(
            f"Reading live Deployment {name} in namespace {WATCH_NAMESPACE}...",
            flush=True,
        )

        return self.apps_api.read_namespaced_deployment(
            name=name,
            namespace=WATCH_NAMESPACE,
        )

    def check_replica_drift(self):
        expected = self.get_expected_manifest()

        expected_name = expected["metadata"]["name"]
        expected_replicas = expected["spec"].get("replicas", 1)

        actual = self.get_actual_deployment(expected_name)
        actual_replicas = actual.spec.replicas

        print(
            f"Replica check: deployment={expected_name}, "
            f"expected={expected_replicas}, actual={actual_replicas}",
            flush=True,
        )

        if expected_replicas != actual_replicas:
            title = f"[DRIFT] {expected_name} replicas mismatch"

            body = f"""
## Kubernetes Drift Detected

DriftBounty detected a replica mismatch.

| Field | Value |
|---|---|
| Namespace | `{WATCH_NAMESPACE}` |
| Deployment | `{expected_name}` |
| Expected replicas from GitOps state | `{expected_replicas}` |
| Actual live replicas | `{actual_replicas}` |

## Risk

Someone changed the live Kubernetes deployment manually, bypassing GitOps.

## Suggested Fix

Run:

```bash
kubectl scale deployment {expected_name} -n {WATCH_NAMESPACE} --replicas={expected_replicas}