# Imagem do Exchange em 3 estágios:
#   base  -> Python + dependências do serviço
#   test  -> roda pytest e pip-audit DURANTE o build (o Jenkins chama --target test); se um
#            teste falhar ou alguma dependência tiver vulnerabilidade conhecida, o build para
#   final -> só o código do serviço, usuário sem root (é o estágio padrão, o que vai pro Docker Hub)
FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# Achado do Trivy (18/11/2026): a imagem base trazia 2 vulnerabilidades HIGH com correção
# (zlib1g CVE-2026-85091 do Debian e setuptools CVE-2025-47273). O upgrade aplica os patches
# de segurança do Debian que saíram depois da imagem base; o setuptools vai para a versão
# corrigida e o pacote antigo que vem junto do Python (ensurepip) é removido.
RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/*
WORKDIR /app
# requirements antes do código: mudar main.py não reinstala as dependências (cache de camada)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip "setuptools>=78.1.1" \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /usr/local/lib/python3.13/ensurepip/_bundled

FROM base AS test
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
RUN pytest -q && pip-audit --strict -r requirements.txt

FROM base AS final
COPY main.py ptax.py ./
RUN useradd --uid 10001 --no-create-home app
USER 10001
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
