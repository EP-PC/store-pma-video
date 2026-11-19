# Como rodar

```bash
git clone --recurse-submodules https://github.com/EP-PC/store-pma.git
cd store-pma
```

## Local (Docker Compose)

Pré-requisitos: Java 25, Maven 3.9+ e Docker.

```bash
cd api
cp .env.example .env      # preencher JWT_SECRET_KEY e ACCOUNT_ADMIN_* (o arquivo explica como gerar)
./build.sh                # Windows: .\build.ps1 (mvn install nos contratos, mvn package nos services)
docker compose up --build -d
docker compose ps
```

- A API fica em `http://localhost:8080`; só o gateway publica porta.
- O Exchange é buildado só pelo Docker (Python, fora do `build.sh`).
- Para derrubar: `docker compose down`, **sem `-v`** (o volume guarda as contas e os pedidos).
- Prometheus e Grafana do Order: `docker compose --profile observability up --build -d`
  (Grafana em `http://localhost:3000`).

Teste rápido pelo gateway:

| Chamada | Esperado |
|---|---|
| `GET /products` | 200 (vitrine aberta) |
| `POST /auth/register`, `POST /auth/login` | 201, 200 + cookie |
| `GET /exchange/health-check` sem login | 200 |
| `GET /exchange/USD/BRL` sem login | 401 (o gateway barra) |
| `GET /exchange/USD/BRL` logado | 200 com o `id-account` do usuário |
| `POST /orders` e `GET /orders/{id}?currency=BRL` | itens e total em reais |
| `GET /orders/{id}?currency=XYZ` | 422 |

## Minikube

```bash
minikube start --driver=docker --memory=3072 --cpus=4
kubectl apply -f api/postgres/configmap.yaml -f api/postgres/secrets.yaml \
              -f api/postgres/deployment.yaml -f api/postgres/service.yaml
kubectl create secret generic account-secrets \
  --from-literal=ACCOUNT_ADMIN_EMAIL="..." --from-literal=ACCOUNT_ADMIN_HASH="..."
kubectl create secret generic auth-secrets --from-literal=JWT_SECRET_KEY="..."
for s in account-service auth-service product-service order-service exchange-service gateway-service; do
  kubectl apply -f api/$s/k8s/k8s.yaml
done
minikube tunnel           # em outro terminal: gateway em http://localhost:8080
```

As imagens vêm do Docker Hub: cada `k8s/k8s.yaml` aponta para a imagem do serviço com a tag
do commit.

## AWS (EKS)

Pré-requisitos: AWS CLI v2 com o profile SSO do grupo, `kubectl`, PowerShell e o `api/.env`
preenchido.

```powershell
aws sso login --profile grupo05
powershell -NoProfile -ExecutionPolicy Bypass -File .\aws\up.ps1     # ~30 min
# ... no fim imprime http://<load-balancer>:8080
powershell -NoProfile -ExecutionPolicy Bypass -File .\aws\down.ps1   # ~20 min: SEMPRE derrubar
```

O `up.ps1` faz, em ordem:

1. stacks `eks-store-vpc`, `eks-store-iam`, `eks-store-cluster` (com o metrics-server),
   `eks-store-rds` e `eks-store-jenkins-access` (CloudFormation);
2. kubeconfig, ConfigMap e Secrets do banco a partir do RDS e do `aws/.env`;
3. Secrets `account-secrets` e `auth-secrets` a partir do `api/.env`;
4. `kubectl apply` de cada serviço (inclusive o `exchange-service`) e `rollout status`;
5. espera o Load Balancer do gateway e imprime a URL pública.

O `down.ps1` apaga tudo, menos a stack `eks-store-jenkins-iam` (usuário do Jenkins, permanente).
Custo com tudo no ar: cerca de **US$ 0,34/hora** (ver [Custos](custos.md)).
