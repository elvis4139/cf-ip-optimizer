#!/bin/sh
# 阶段 3.4：在 NAS 项目目录落地 3 个骨架文件，并只做文件检查
# 不执行 docker compose up，不启动任何容器/定时任务，不改动现有容器与网络
set -e

if [ ! -d /share/Container/cf-ip-optimizer ]; then
  echo "ERROR: /share/Container/cf-ip-optimizer 不存在；按要求不擅自创建目录，请先确认路径"
  exit 1
fi
cd /share/Container/cf-ip-optimizer || exit 1

cat > Dockerfile <<'DOCKERFILE_EOF'
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
PYTHONUNBUFFERED=1
WORKDIR /opt/cf-ip-optimizer
CMD ["python", "--version"]
DOCKERFILE_EOF

cat > compose.yaml <<'COMPOSE_EOF'
services:
  cf-ip-optimizer:
    container_name: cf-ip-optimizer
    image: cf-ip-optimizer:stage3
    build:
      context: .
      dockerfile: Dockerfile
    user: "1000:0"
    init: true
    restart: "no"
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=64m,uid=1000,gid=0
    environment:
      TZ: Asia/Shanghai
      PYTHONDONTWRITEBYTECODE: "1"
      PYTHONUNBUFFERED: "1"
      HTTP_PROXY: ""
      HTTPS_PROXY: ""
      ALL_PROXY: ""
      http_proxy: ""
      https_proxy: ""
      all_proxy: ""
      NO_PROXY: "*"
      no_proxy: "*"
    volumes:
      - ./bin:/opt/cf-ip-optimizer/bin:ro
      - ./config:/opt/cf-ip-optimizer/config:ro
      - ./data:/opt/cf-ip-optimizer/data
      - ./samples:/opt/cf-ip-optimizer/samples
      - ./logs:/opt/cf-ip-optimizer/logs
    command: ["python", "--version"]
    networks:
      - cf_optimizer_net
networks:
  cf_optimizer_net:
    name: cf-ip-optimizer-net
    driver: bridge
COMPOSE_EOF

cat > .dockerignore <<'DOCKERIGNORE_EOF'
.git
.env
*.tar.gz
data/
samples/
logs/
__pycache__/
*.pyc
DOCKERIGNORE_EOF

echo "========== 3.4-1 文件检查 =========="
ls -lah Dockerfile compose.yaml .dockerignore
echo "========== 3.4-2 Dockerfile =========="
cat Dockerfile
echo "========== 3.4-3 Compose配置 =========="
cat compose.yaml
echo "========== 3.4-4 Docker忽略文件 =========="
cat .dockerignore
echo "========== 3.4-5 Compose配置语法检查 =========="
/usr/local/lib/docker/cli-plugins/docker-compose config -q
echo "Compose配置语法检查通过"
