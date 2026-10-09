"""Build a usable, deterministic DevOps artifact bundle for local projects.

The LLM is an optional enhancement. These templates keep the core workflow
usable when no model key is configured and provide a safe baseline to validate.
"""
import json
import re
import shlex
from typing import Any

import yaml


def _slug(value: Any) -> str:
    text = re.sub(r"[^a-z0-9-]+", "-", str(value or "sample-app").lower()).strip("-")
    return (text or "sample-app")[:50].rstrip("-") or "sample-app"


def _yaml(value: dict) -> str:
    return yaml.safe_dump(value, sort_keys=False, allow_unicode=False)


def _dockerfile(spec: dict) -> str:
    app = spec.get("application", {})
    container = spec.get("container", {})
    language = (app.get("language") or "").lower()
    port = int(container.get("port") or 8080)

    if language == "node.js":
        command = ["npm", "start"] if app.get("start_command") != "npm run dev" else ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
        install = "COPY package*.json ./\nRUN npm install"
        base = container.get("base_image") or "node:20-alpine"
        setup = "RUN addgroup -S app && adduser -S app -G app"
    elif language == "python":
        base = container.get("base_image") or "python:3.12-slim"
        has_requirements = any(str(path).endswith("requirements.txt") for path in app.get("files", []))
        install = "COPY requirements.txt ./\nRUN pip install --no-cache-dir -r requirements.txt" if has_requirements else "RUN pip install --no-cache-dir fastapi uvicorn"
        command = shlex.split(app.get("start_command") or "python main.py")
        setup = "RUN useradd --create-home --uid 10001 app"
    elif language == "java":
        base = container.get("base_image") or "eclipse-temurin:21-jre-alpine"
        install = "COPY target/*.jar /app/app.jar"
        command = ["java", "-jar", "/app/app.jar"]
        setup = "RUN addgroup -S app && adduser -S app -G app"
    else:
        base = container.get("base_image") or "alpine:3.20"
        install = "COPY . ."
        command = shlex.split(app.get("start_command") or "sh")
        setup = "RUN addgroup -S app && adduser -S app -G app"

    if language == "java":
        return (
            "FROM maven:3.9-eclipse-temurin-21 AS build\n"
            "WORKDIR /build\nCOPY pom.xml ./\nRUN mvn -B dependency:go-offline\n"
            "COPY src ./src\nRUN mvn -B package -DskipTests\n\n"
            f"FROM {base}\nWORKDIR /app\nCOPY --from=build /build/target/*.jar /app/app.jar\n"
            f"{setup}\nUSER app\nEXPOSE {port}\nCMD {json.dumps(command)}\n"
        )

    return (
        f"FROM {base}\nWORKDIR /app\n{install}\nCOPY . .\n"
        f"{setup}\nUSER app\nEXPOSE {port}\nCMD {json.dumps(command)}\n"
    )


def _kubernetes_manifests(spec: dict) -> dict[str, str]:
    app = spec.get("application", {})
    container = spec.get("container", {})
    platform = spec.get("platform", {})
    name = _slug(app.get("name"))
    image = f"devops-assistant/{name}:1.0.0"
    port = int(container.get("port") or 8080)
    replicas = max(1, int(platform.get("replicas") or 1))
    cpu = platform.get("cpu_limit") or "500m"
    memory = platform.get("memory_limit") or "512Mi"

    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": name, "labels": {"app.kubernetes.io/name": name}},
        "spec": {
            "replicas": replicas,
            "selector": {"matchLabels": {"app.kubernetes.io/name": name}},
            "template": {
                "metadata": {"labels": {"app.kubernetes.io/name": name}},
                "spec": {
                    "securityContext": {"runAsNonRoot": True, "runAsUser": 10001, "fsGroup": 10001},
                    "containers": [{
                        "name": name,
                        "image": image,
                        "imagePullPolicy": "IfNotPresent",
                        "ports": [{"name": "http", "containerPort": port, "protocol": "TCP"}],
                        "resources": {"requests": {"cpu": cpu, "memory": memory}, "limits": {"cpu": cpu, "memory": memory}},
                        "securityContext": {"allowPrivilegeEscalation": False, "readOnlyRootFilesystem": False, "capabilities": {"drop": ["ALL"]}},
                        "readinessProbe": {"tcpSocket": {"port": port}, "initialDelaySeconds": 5, "periodSeconds": 10},
                        "livenessProbe": {"tcpSocket": {"port": port}, "initialDelaySeconds": 15, "periodSeconds": 20},
                    }],
                },
            },
        },
    }
    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": name},
        "spec": {"type": "ClusterIP", "selector": {"app.kubernetes.io/name": name}, "ports": [{"name": "http", "port": 80, "targetPort": port}]},
    }
    outputs = {
        "kubernetes/deployment.yaml": _yaml(deployment),
        "kubernetes/service.yaml": _yaml(service),
    }

    if platform.get("is_public"):
        ingress = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {"name": name},
            "spec": {"rules": [{"host": f"{name}.local", "http": {"paths": [{"path": "/", "pathType": "Prefix", "backend": {"service": {"name": name, "port": {"number": 80}}}}]}}]},
        }
        outputs["kubernetes/ingress.yaml"] = _yaml(ingress)

    if platform.get("autoscaling"):
        hpa = {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {"name": name},
            "spec": {"scaleTargetRef": {"apiVersion": "apps/v1", "kind": "Deployment", "name": name}, "minReplicas": replicas, "maxReplicas": max(replicas * 3, 3), "metrics": [{"type": "Resource", "resource": {"name": "cpu", "target": {"type": "Utilization", "averageUtilization": 75}}}]},
        }
        outputs["kubernetes/hpa.yaml"] = _yaml(hpa)

    return outputs


def _helm_chart(spec: dict) -> dict[str, str]:
    app = spec.get("application", {})
    container = spec.get("container", {})
    platform = spec.get("platform", {})
    name = _slug(app.get("name"))
    port = int(container.get("port") or 8080)
    cpu = platform.get("cpu_limit") or "500m"
    memory = platform.get("memory_limit") or "512Mi"
    values = {
        "replicaCount": max(1, int(platform.get("replicas") or 1)),
        "image": {"repository": f"devops-assistant/{name}", "tag": "1.0.0", "pullPolicy": "IfNotPresent"},
        "service": {"type": "ClusterIP", "port": 80, "targetPort": port},
        "ingress": {"enabled": bool(platform.get("is_public")), "className": "nginx", "host": f"{name}.local"},
        "autoscaling": {"enabled": bool(platform.get("autoscaling")), "minReplicas": max(1, int(platform.get("replicas") or 1)), "maxReplicas": max(max(1, int(platform.get("replicas") or 1)) * 3, 3), "targetCPUUtilizationPercentage": 75},
        "resources": {"requests": {"cpu": cpu, "memory": memory}, "limits": {"cpu": cpu, "memory": memory}},
    }
    templates = {
        "helm/templates/deployment.yaml": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include \"app.fullname\" . }}
  labels:
    app.kubernetes.io/name: {{ include \"app.name\" . }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include \"app.name\" . }}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {{ include \"app.name\" . }}
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
      containers:
        - name: {{ include \"app.name\" . }}
          image: \"{{ .Values.image.repository }}:{{ .Values.image.tag }}\"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.service.targetPort }}
          resources:
{{ toYaml .Values.resources | indent 12 }}
          readinessProbe:
            tcpSocket:
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            tcpSocket:
              port: http
            initialDelaySeconds: 15
            periodSeconds: 20
""",
        "helm/templates/service.yaml": """apiVersion: v1
kind: Service
metadata:
  name: {{ include \"app.fullname\" . }}
spec:
  type: {{ .Values.service.type }}
  selector:
    app.kubernetes.io/name: {{ include \"app.name\" . }}
  ports:
    - name: http
      port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort }}
""",
    }
    if platform.get("is_public"):
        templates["helm/templates/ingress.yaml"] = """{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include \"app.fullname\" . }}
spec:
  ingressClassName: {{ .Values.ingress.className }}
  rules:
    - host: {{ .Values.ingress.host | quote }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ include \"app.fullname\" . }}
                port:
                  number: {{ .Values.service.port }}
{{- end }}
"""
    if platform.get("autoscaling"):
        templates["helm/templates/hpa.yaml"] = """{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include \"app.fullname\" . }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include \"app.fullname\" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
"""
    helpers = f"""{{{{/* Expand the chart name. */}}}}
{{{{- define \"app.name\" -}}}}
{name}
{{{{- end }}}}

{{{{/* Create a release-qualified resource name. */}}}}
{{{{- define \"app.fullname\" -}}}}
{{{{ .Release.Name }}}}
{{{{- end }}}}
"""
    return {
        "helm/Chart.yaml": f"apiVersion: v2\nname: {name}\ndescription: Deployment chart for {name}\ntype: application\nversion: 0.1.0\nappVersion: \"1.0.0\"\n",
        "helm/values.yaml": _yaml(values),
        "helm/templates/_helpers.tpl": helpers,
        **templates,
    }


def generate_artifacts_deterministically(spec: dict) -> dict[str, str]:
    """Generate a complete local artifact bundle from the deployment spec."""
    app = spec.get("application", {})
    platform = spec.get("platform", {})
    name = _slug(app.get("name"))
    artifacts = {"Dockerfile": _dockerfile(spec)}

    if (platform.get("platform") or "Kubernetes").lower() == "kubernetes":
        artifacts.update(_kubernetes_manifests(spec))
        artifacts.update(_helm_chart(spec))
        helm_check = "      - name: Check Helm chart\n        run: helm lint ./helm\n".rstrip()
    else:
        artifacts["docker-compose.yml"] = _yaml({
            "services": {
                name: {"build": {"context": "."}, "image": f"devops-assistant/{name}:1.0.0", "ports": [f"${{HOST_PORT:-8080}}:{int(spec.get('container', {}).get('port') or 8080)}"], "restart": "unless-stopped"}
            }
        })
        helm_check = "      - name: Validate Compose file\n        run: docker compose config --quiet\n".rstrip()

    artifacts[".dockerignore"] = """.git
.env
.venv
venv
node_modules
dist
build
__pycache__
*.pyc
"""

    artifacts[".github/workflows/devops-ci.yml"] = f"""name: DevOps quality gate
on:
  push:
  pull_request:
permissions:
  contents: read
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Check out source
        uses: actions/checkout@v4
      - name: Build container
        run: docker build -t {name}:ci .
{helm_check}
"""
    artifacts["DEPLOYMENT.md"] = f"""# {name} deployment notes

## Container image

Build the generated image with `docker build -t devops-assistant/{name}:1.0.0 .`.
For a remote Kubernetes cluster, publish that image to a registry your cluster can reach and update the image repository in the manifest/chart first.

## Kubernetes

Apply the generated manifests with `kubectl apply -f kubernetes/`, or install the Helm chart with `helm upgrade --install {name} ./helm --namespace {name} --create-namespace`.
The ingress host defaults to `{name}.local`; point DNS or your local ingress controller at it before use.

Configuration values are names only. Add environment values and secrets through your deployment environment; no repository secret values are copied into the generated artifacts.

The included GitHub Actions workflow builds the container and checks the deployment package. Configure a registry and deployment credentials separately to add automated publishing or cluster deployment.
"""
    return artifacts
