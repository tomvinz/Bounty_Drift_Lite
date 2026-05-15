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

        self.apps_api = client.AppsV1Api()
        self.core_api = client.CoreV1Api()

        self.github = GitHubClient()

        print("DriftDetector initialized successfully", flush=True)

    def load_kubernetes_config(self):
        print("Trying in-cluster Kubernetes config...", flush=True)

        try:
            config.load_incluster_config()
            print("Loaded in-cluster Kubernetes config", flush=True)

        except Exception as error:
            print(f"In-cluster config failed: {error}", flush=True)

            config.load_kube_config()
            print("Loaded local kubeconfig", flush=True)

    def get_expected_manifest(self):
        configmap = self.core_api.read_namespaced_config_map(
            name=EXPECTED_CONFIGMAP,
            namespace=WATCH_NAMESPACE,
        )

        manifest_text = configmap.data.get(EXPECTED_CONFIGMAP_KEY)

        if not manifest_text:
            raise ValueError(
                f"Missing key {EXPECTED_CONFIGMAP_KEY} "
                f"in ConfigMap {EXPECTED_CONFIGMAP}"
            )

        return yaml.safe_load(manifest_text)

    def get_actual_deployment(self, deployment_name):
        return self.apps_api.read_namespaced_deployment(
            name=deployment_name,
            namespace=WATCH_NAMESPACE,
        )

    def check_replica_drift(self):
        expected = self.get_expected_manifest()

        deployment_name = expected["metadata"]["name"]
        expected_replicas = expected["spec"].get("replicas", 1)

        actual = self.get_actual_deployment(deployment_name)
        actual_replicas = actual.spec.replicas

        print(
            f"Replica check: expected={expected_replicas}, "
            f"actual={actual_replicas}",
            flush=True,
        )

        if expected_replicas != actual_replicas:
            title = f"[DRIFT] {deployment_name} replicas mismatch"

            body = (
                "Kubernetes drift detected.\n\n"
                f"Deployment: {deployment_name}\n"
                f"Namespace: {WATCH_NAMESPACE}\n"
                f"Expected replicas: {expected_replicas}\n"
                f"Actual replicas: {actual_replicas}\n"
            )

            print(title, flush=True)

            try:
                self.github.create_issue(title, body)
                print("GitHub issue created", flush=True)

            except Exception as error:
                print(f"GitHub issue creation failed: {error}", flush=True)

        else:
            print(
                f"No drift detected for {deployment_name}. "
                f"Expected={expected_replicas}, Actual={actual_replicas}",
                flush=True,
            )

    def run_forever(self):
        print("Starting drift detection loop...", flush=True)

        while True:
            try:
                self.check_replica_drift()

            except Exception as error:
                print(f"Drift scan failed: {error}", flush=True)

            time.sleep(SCAN_INTERVAL_SECONDS)