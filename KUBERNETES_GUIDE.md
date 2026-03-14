# ☸️ Student Guide — Local Kubernetes with Minikube
## Assignment — Setting Up a Local Kubernetes Cluster

> **What you will do:** Install Minikube, spin up a local Kubernetes cluster on your laptop,
> and deploy the **full AI Chat application** — the same FastAPI + TinyLlama + PostgreSQL + Nginx
> stack from the previous Docker assignments — but now managed by Kubernetes.

---

## 📋 Table of Contents

1. [What is Kubernetes? (Quick Intro)](#1-what-is-kubernetes-quick-intro)
2. [Prerequisites & Installation](#2-prerequisites--installation)
3. [Step 1 — Start Your Cluster](#step-1--start-your-cluster)
4. [Step 2 — Understand the App Stack](#step-2--understand-the-app-stack)
5. [Step 3 — Build Images into Minikube](#step-3--build-images-into-minikube)
6. [Step 4 — Deploy the Full Stack](#step-4--deploy-the-full-stack)
7. [Step 5 — Open the App](#step-5--open-the-app)
8. [Step 6 — Monitor the Model Download](#step-6--monitor-the-model-download)
9. [Step 7 — Explore with kubectl](#step-7--explore-with-kubectl)
10. [Step 8 — Auto-Scaling with HPA](#step-8--auto-scaling-with-hpa)
11. [Step 9 — Monitor with kubectl top](#step-9--monitor-with-kubectl-top)
12. [Step 10 — Clean Up](#step-10--clean-up)
13. [Troubleshooting](#troubleshooting)

---

## 1. What is Kubernetes? (Quick Intro)

You already know **Docker** — it runs a single container on a single machine.

**Kubernetes (K8s)** is the next step: it manages **many containers across many machines**, handling restarts, scaling, networking, and more — automatically.

| Concept | Simple explanation |
|---|---|
| **Cluster** | A group of machines (nodes) that Kubernetes manages together |
| **Node** | A single machine (real or virtual) inside the cluster |
| **Pod** | The smallest deployable unit — wraps one (or more) containers |
| **Deployment** | Tells Kubernetes: "keep N copies of this Pod running at all times" |
| **Service** | A stable network address to reach your Pods |
| **Job** | A Pod that runs once to completion (e.g. downloading a model) |
| **PVC** | Persistent Volume Claim — asks Kubernetes for disk storage |
| **ConfigMap** | Stores config or files (like SQL scripts) that Pods can read |
| **HPA** | Horizontal Pod Autoscaler — automatically scales replicas up/down based on CPU usage |
| **metrics-server** | Kubernetes addon that collects CPU/memory stats from every Pod |

> 💡 **Minikube** gives you a single-node Kubernetes cluster that runs entirely on your laptop — perfect for learning.

---

## 2. Prerequisites & Installation

You need **Minikube** and **kubectl** installed. Docker Desktop must already be running (you installed it in the previous assignments).

---

### 🍎 macOS

Open Terminal and run:

```bash
# Install Minikube
brew install minikube

# Install kubectl (the command-line tool to talk to Kubernetes)
brew install kubectl
```

Verify both installed:
```bash
minikube version
kubectl version --client
```

**Expected output:**
```
minikube version: v1.x.x
Client Version: v1.x.x
```

---

### 🪟 Windows

Open **PowerShell as Administrator** and run:

**1. Install Minikube:**
```powershell
winget install Kubernetes.minikube
```

**2. Install kubectl:**
```powershell
winget install Kubernetes.kubectl
```

Close and reopen PowerShell, then verify:
```powershell
minikube version
kubectl version --client
```

> 💡 If `winget` is not available, download the installers manually:
> - Minikube: [https://minikube.sigs.k8s.io/docs/start/](https://minikube.sigs.k8s.io/docs/start/)
> - kubectl: [https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/)

---

## Step 1 — Start Your Cluster

```bash
minikube start
```

This downloads a small virtual machine and starts a single-node Kubernetes cluster inside it. **First run takes 2–5 minutes.**

**Expected output (last few lines):**
```
✅  Done! kubectl is now configured to use "minikube" cluster and "default" namespace by default
```

Check the cluster is running:
```bash
kubectl get nodes
```

**Expected output:**
```
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   1m    v1.x.x
```

> `STATUS: Ready` means your cluster is up. You have 1 node — your laptop.

---

## Step 2 — Understand the App Stack

The `kubernetes/` folder contains one manifest file per service:

```
kubernetes/
  ollama.yaml        → Ollama LLM runtime  (PVC + Deployment + Service)
  model-puller.yaml  → Job: downloads TinyLlama into Ollama (runs once)
  postgres.yaml      → PostgreSQL database (ConfigMap + PVC + Deployment + Service)
  ai-model.yaml      → FastAPI chat API    (Deployment + Service)
  frontend.yaml      → Nginx chat UI       (Deployment + Service)
```

The services talk to each other **by name** inside the cluster — no IP addresses needed:

```
Browser
  │
  ▼ localhost:3000 (port-forward)
 Frontend (Nginx)
  │
  ▼ http://localhost:8000 (port-forward)
 AI Model (FastAPI)
  │            │
  ▼            ▼
Ollama      PostgreSQL
(TinyLlama)  (chat history)
```

> 💡 A **manifest** is just a YAML file that describes what you want — Kubernetes figures out how to make it happen.

---

## Step 3 — Build Images into Minikube

Minikube runs its own internal Docker daemon — **separate** from Docker Desktop. You must build your custom images directly inside Minikube, otherwise Kubernetes won't find them.

### Point your Docker CLI at Minikube's daemon

```bash
eval $(minikube docker-env)
```

> After running this, every `docker` command targets Minikube's internal registry, not Docker Desktop.
> This only applies to your **current terminal session**.

### Pre-pull the large Ollama image

Ollama's image is ~1.5 GB. Pull it now so Kubernetes doesn't time out waiting for it:

```bash
docker pull ollama/ollama:latest
```

This takes 2–5 minutes depending on your internet. You will see progress bars.

### Build the two custom app images

```bash
# Build the FastAPI AI model image
docker build -t ai-chat/ai-model:latest ./ai-model

# Build the Nginx frontend image
docker build -t ai-chat/frontend:latest ./frontend
```

**Expected output (last line of each build):**
```
=> naming to docker.io/ai-chat/ai-model:latest
=> naming to docker.io/ai-chat/frontend:latest
```

Verify all three images are inside Minikube:
```bash
docker images | grep -E "ollama|ai-chat"
```

> 💡 All manifests use `imagePullPolicy: Never` — this tells Kubernetes to use the locally built image
> and never try to download it from Docker Hub.

---

## Step 4 — Deploy the Full Stack

Apply all manifests in dependency order:

```bash
kubectl apply -f kubernetes/postgres.yaml
kubectl apply -f kubernetes/ollama.yaml
kubectl apply -f kubernetes/model-puller.yaml
kubectl apply -f kubernetes/ai-model.yaml
kubectl apply -f kubernetes/frontend.yaml
```

**Expected output:**
```
configmap/postgres-init-sql created
persistentvolumeclaim/postgres-pvc created
deployment.apps/postgres created
service/postgres created
persistentvolumeclaim/ollama-pvc created
deployment.apps/ollama created
service/ollama created
job.batch/model-puller created
deployment.apps/ai-model created
service/ai-model created
deployment.apps/frontend created
service/frontend created
```

### Watch everything start up

```bash
kubectl get pods
```

Wait until all pods show `1/1 Running`. The first time takes a few minutes:

```
NAME                        READY   STATUS    RESTARTS   AGE
ai-model-bd8785684-btkhc    1/1     Running   0          3m
frontend-565c768fbd-fv728   1/1     Running   0          3m
model-puller-lrpmq          1/1     Running   0          3m
ollama-6496b8b749-lq556     1/1     Running   0          3m
postgres-6fdddcdc7-fbg5j    1/1     Running   0          3m
```

> `model-puller` will show `Completed` after it finishes downloading TinyLlama — that's normal.

---

## Step 5 — Open the App

On macOS, Minikube runs inside Docker's network so `minikube service` creates a fragile tunnel.
`kubectl port-forward` is stable and works every time. You need **two** port-forwards — one for the
frontend and one for the API (the frontend JavaScript calls `http://localhost:8000` directly).

Run these two commands in **separate terminal tabs** (or as background processes):

**Terminal tab 1 — Frontend:**
```bash
kubectl port-forward deployment/frontend 3000:80
```

**Terminal tab 2 — AI API:**
```bash
kubectl port-forward deployment/ai-model 8000:8000
```

**Expected output for each:**
```
Forwarding from 127.0.0.1:3000 -> 80
Forwarding from [::1]:3000 -> 80
```

Now open your browser: **http://localhost:3000** 🎉

> ⚠️ Keep both terminal tabs open — the port-forwards stop if you close them.

#### 🪟 Windows — use `minikube service`

```powershell
minikube service frontend
```
Minikube opens the browser for you automatically. The API is accessible at `http://localhost:8000`
via the port-forward in the second tab.

---

## Step 6 — Monitor the Model Download

The `model-puller` Job downloads TinyLlama (~637 MB) into Ollama in the background.
The chat UI will show **Offline** until this finishes.

Watch the download progress:
```bash
kubectl logs -f job/model-puller
```

**Expected output:**
```
⏳ Waiting for Ollama to be ready...
✅ Ollama is ready. Pulling tinyllama (this takes a few minutes)...
✅ Model pulled successfully!
```

Once you see `Model pulled successfully!`, check the full health of the stack:
```bash
curl http://localhost:8000/health
```

**Expected output (all healthy):**
```json
{
  "status": "healthy",
  "model": "tinyllama",
  "ollama": "healthy",
  "database": "healthy"
}
```

The status indicator in the chat UI will turn green. You can now send messages! 🤖

---

## Step 7 — Explore with kubectl

These are the commands you will use every day as a developer or DevOps engineer.

### List everything running

```bash
# List all Pods
kubectl get pods

# List all Services (internal addresses)
kubectl get services

# List all Jobs (like model-puller)
kubectl get jobs

# List everything at once
kubectl get all
```

### Inspect a resource (the most useful debugging command)

```bash
# Replace <pod-name> with the actual name from kubectl get pods
kubectl describe pod <pod-name>
```

Look for the **Events** section at the bottom — it shows exactly what Kubernetes did to start your Pod, including any errors.

### View container logs

```bash
# Logs from a specific service
kubectl logs deployment/ai-model
kubectl logs deployment/ollama
kubectl logs deployment/postgres

# Follow logs live (like docker logs -f)
kubectl logs -f deployment/ai-model

# Logs from the model download job
kubectl logs job/model-puller
```

### Get a shell inside a container

```bash
kubectl exec -it deployment/frontend -- sh
```

You are now inside the running container! Try:
```sh
ls /usr/share/nginx/html
exit
```

### Restart a deployment

```bash
# Useful when a service started before its dependency was ready
kubectl rollout restart deployment/ai-model
```

---

## Step 8 — Auto-Scaling with HPA

So far you manually scaled with `kubectl scale`. Now let Kubernetes do it **automatically** based on CPU load — this is called a **Horizontal Pod Autoscaler (HPA)**.

### How HPA works

```
metrics-server watches CPU of every Pod
         │
         ▼
  HPA checks every 15 seconds:
  "Is frontend CPU > 50%?"
         │
    Yes ─▶ add more replicas (up to 5)
    No  ─▶ remove replicas (down to 1)
```

### Step 8.1 — Enable metrics-server

HPA requires the `metrics-server` addon. Enable it once:

```bash
minikube addons enable metrics-server
```

**Expected output:**
```
🌟  The 'metrics-server' addon is enabled
```

> ⚠️ On macOS with the Docker driver, metrics-server needs a small patch to work.
> Run this once after enabling:
> ```bash
> kubectl patch deployment metrics-server -n kube-system \
>   --type='json' \
>   -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
> ```

Wait ~30 seconds, then verify it is collecting data:
```bash
kubectl top pods
```

**Expected output:**
```
NAME                        CPU(cores)   MEMORY(bytes)
ai-model-85d8b94d97-k4xqp   4m           74Mi
frontend-565c768fbd-fv728   1m           8Mi
ollama-6496b8b749-lq556     2m           1310Mi
postgres-6fdddcdc7-fbg5j    2m           55Mi
```

> `m` = millicores. `1000m` = 1 full CPU core. At idle, pods use very little.

### Step 8.2 — Deploy the HPAs

The `kubernetes/hpa.yaml` file defines two autoscalers:
- **frontend-hpa** — scales `frontend` between 1–5 replicas when CPU > 50%
- **ai-model-hpa** — scales `ai-model` between 1–3 replicas when CPU > 70%

```bash
kubectl apply -f kubernetes/hpa.yaml
```

**Expected output:**
```
horizontalpodautoscaler.autoscaling/frontend-hpa created
horizontalpodautoscaler.autoscaling/ai-model-hpa created
```

### Step 8.3 — Observe the HPA

```bash
kubectl get hpa
```

**Expected output:**
```
NAME           REFERENCE             TARGETS       MINPODS   MAXPODS   REPLICAS
ai-model-hpa   Deployment/ai-model   cpu: 4%/70%   1         3         1
frontend-hpa   Deployment/frontend   cpu: 2%/50%   1         5         1
```

| Column | What it means |
|---|---|
| `TARGETS` | Current CPU% / threshold to trigger scaling |
| `MINPODS` | Minimum replicas — Kubernetes will never go below this |
| `MAXPODS` | Maximum replicas — Kubernetes will never exceed this |
| `REPLICAS` | How many Pods are running right now |

> At idle the CPU is low so only 1 replica runs. Under real traffic the HPA would automatically
> add more. This is one of the most powerful features of Kubernetes.

### Step 8.4 — Simulate load and watch it scale (optional)

Open a second terminal and send a burst of requests to the frontend:

```bash
# Send 10000 requests with 50 concurrent connections
kubectl run load-test --image=busybox --restart=Never -- \
  sh -c 'for i in $(seq 1 10000); do wget -q -O- http://frontend > /dev/null; done'
```

In another tab, watch the HPA react:
```bash
kubectl get hpa -w
```

Clean up the load test pod:
```bash
kubectl delete pod load-test
```

---

## Step 9 — Monitor with kubectl top

`kubectl top` gives you a live view of CPU and memory for every Pod and Node.
It uses the same `metrics-server` you just enabled.

### Pod metrics

```bash
# Current CPU and memory for all Pods
kubectl top pods

# Watch it update every 2 seconds
watch kubectl top pods
```

**Example output while chatting with TinyLlama:**
```
NAME                        CPU(cores)   MEMORY(bytes)
ai-model-85d8b94d97-k4xqp   220m         128Mi
frontend-565c768fbd-fv728   3m           8Mi
ollama-6496b8b749-lq556     1850m        2100Mi    ← spikes during inference
postgres-6fdddcdc7-fbg5j    4m           58Mi
```

> You can see Ollama spiking to ~1.85 CPU cores while generating a response. That's normal —
> running a language model is CPU-intensive.

### Node metrics

```bash
# CPU and memory of the entire Minikube node
kubectl top node
```

**Example output:**
```
NAME       CPU(cores)   CPU%   MEMORY(bytes)   MEMORY%
minikube   2100m        52%    3500Mi          45%
```

### Describe an HPA for full detail

```bash
kubectl describe hpa frontend-hpa
```

Look for the **Events** section — it shows every scale-up and scale-down decision Kubernetes made
and exactly why.

---

## Step 10 — Clean Up

When you're done, clean up to free resources on your laptop.

### Delete everything you deployed

```bash
kubectl delete -f kubernetes/
```

Verify everything is gone:
```bash
kubectl get all
```

### Stop the Minikube cluster

```bash
# Stop the cluster (keeps your config — fast to restart next time)
minikube stop

# OR delete the cluster completely (removes everything, fresh start next time)
minikube delete
```

---

## Troubleshooting

### ❓ `minikube start` fails or hangs

Make sure **Docker Desktop is running** before starting Minikube.

```bash
docker info
```

If Docker is not running, open Docker Desktop and wait for the whale icon to turn solid, then retry.

### ❓ Pod stuck in `ContainerCreating` for more than 2 minutes

Kubernetes is still pulling the image from Docker Hub inside Minikube. This is slow because
Minikube has its own separate Docker daemon with an empty cache on first run.

**Fix:** Pre-pull images into Minikube's daemon before deploying:

```bash
# Point Docker CLI at Minikube's daemon
eval $(minikube docker-env)

# Pull the large image directly (shows a progress bar)
docker pull ollama/ollama:latest
```

Then delete the stuck pod — Kubernetes will recreate it and find the image already cached:
```bash
kubectl delete pod -l app=ollama
```

### ❓ Chat shows "AI service unavailable"

This happens when the `ai-model` pod started before Postgres or Ollama was fully ready.
It falls back to a degraded mode and won't recover on its own.

**Step 1** — Check the health endpoint:
```bash
curl http://localhost:8000/health
```

**Step 2** — Wait for all pods to be `1/1 Running`, then restart the ai-model:
```bash
kubectl get pods                              # confirm all Running
kubectl rollout restart deployment/ai-model   # restart cleanly
```

**Step 3** — Restart the port-forward for port 8000 (the old pod is gone):
```bash
kubectl port-forward deployment/ai-model 8000:8000
```

**Step 4** — Verify everything is green:
```bash
curl http://localhost:8000/health
# Should return: "status": "healthy", "ollama": "healthy", "database": "healthy"
```

### ❓ Chat shows "Offline" / status indicator is red

TinyLlama is still being downloaded by the `model-puller` Job. Watch the progress:
```bash
kubectl logs -f job/model-puller
```
Wait for `✅ Model pulled successfully!` then the UI will turn green automatically.

### ❓ `port-forward` stopped working

The terminal running `kubectl port-forward` was closed or interrupted. Restart both:
```bash
kubectl port-forward deployment/frontend 3000:80 &
kubectl port-forward deployment/ai-model 8000:8000 &
```

### ❓ `error: image can't be pulled` or `ErrImagePull`

You forgot to build images inside Minikube's Docker daemon. Run this first in your terminal:
```bash
eval $(minikube docker-env)
docker build -t ai-chat/ai-model:latest ./ai-model
docker build -t ai-chat/frontend:latest ./frontend
```

### ❓ `kubectl: command not found`

kubectl was not added to your PATH. On macOS, run:
```bash
export PATH="$PATH:/usr/local/bin"
```
On Windows, restart PowerShell after installing with winget.

### ❓ Want to completely start over

```bash
kubectl delete -f kubernetes/
minikube delete
minikube start
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────────┐
│  SETUP (run once per terminal session on macOS)                      │
│  Point Docker at Minikube:  eval $(minikube docker-env)              │
│  Pre-pull large image:      docker pull ollama/ollama:latest         │
│  Build custom images:       docker build -t ai-chat/ai-model ./ai-model  │
│                             docker build -t ai-chat/frontend ./frontend  │
├─────────────────────────────────────────────────────────────────────┤
│  MINIKUBE                                                            │
│  Start cluster:    minikube start                                    │
│  Stop cluster:     minikube stop                                     │
│  Delete cluster:   minikube delete                                   │
├─────────────────────────────────────────────────────────────────────┤
│  DEPLOY                                                              │
│  Apply all:        kubectl apply -f kubernetes/                      │
│  Delete all:       kubectl delete -f kubernetes/                     │
├─────────────────────────────────────────────────────────────────────┤
│  ACCESS (macOS — keep these running in terminal tabs)               │
│  Frontend:         kubectl port-forward deployment/frontend 3000:80  │
│  AI API:           kubectl port-forward deployment/ai-model 8000:8000│
│  Open app:         http://localhost:3000                             │
│  Health check:     curl http://localhost:8000/health                 │
├─────────────────────────────────────────────────────────────────────┤
│  AUTO-SCALING & MONITORING                                           │
│  Enable metrics:  minikube addons enable metrics-server              │
│  Pod CPU/mem:     kubectl top pods                                   │
│  Node CPU/mem:    kubectl top node                                   │
│  Deploy HPA:      kubectl apply -f kubernetes/hpa.yaml               │
│  Watch HPA:       kubectl get hpa                                    │
│  HPA detail:      kubectl describe hpa frontend-hpa                  │
├─────────────────────────────────────────────────────────────────────┤
│  KUBECTL — ESSENTIALS                                                │
│  List pods:        kubectl get pods                                  │
│  List all:         kubectl get all                                   │
│  Inspect:          kubectl describe pod <pod-name>                   │
│  Logs:             kubectl logs deployment/<name>                    │
│  Follow logs:      kubectl logs -f deployment/<name>                 │
│  Job logs:         kubectl logs job/model-puller                     │
│  Restart deploy:   kubectl rollout restart deployment/<name>         │
│  Shell in pod:     kubectl exec -it deployment/<name> -- sh          │
│  Scale:            kubectl scale deployment <name> --replicas=N      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Summary — What You Learned

| Concept | What it does in this project |
|---------|------------------------------|
| `minikube docker-env` | Points your Docker CLI at Minikube's internal daemon so builds are available to Kubernetes |
| `imagePullPolicy: Never` | Tells Kubernetes to use a locally built image instead of pulling from Docker Hub |
| Deployment | Keeps your service Pod running — restarts it automatically if it crashes |
| Service | Gives a stable internal DNS name so Pods find each other by name (e.g. `http://ollama:11434`) |
| PVC | Gives Ollama and Postgres their own persistent disk inside the cluster |
| ConfigMap | Injects the `init.sql` schema file into the Postgres container at startup |
| Job | Runs the model-puller once to download TinyLlama — then stops cleanly |
| `kubectl port-forward` | Bridges `localhost` on your Mac to a Pod inside Minikube's isolated network |
| `kubectl rollout restart` | Restarts a deployment cleanly — useful when a service started before its dependency was ready |
| `metrics-server` | Minikube addon that collects live CPU/memory stats from every Pod |
| `kubectl top pods` | Shows real-time CPU and memory usage per Pod — the first monitoring command to learn |
| HPA | Automatically scales replicas up when CPU is high, and back down when it drops |

---

*Assignment — Local Kubernetes with Minikube | Stack: Minikube · kubectl · Ollama · TinyLlama · FastAPI · PostgreSQL · Nginx · Docker*
