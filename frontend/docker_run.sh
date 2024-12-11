# 单独构建并运行前端，将访问宿主机上7869端口的后端服务
docker rm -f $(docker ps -a | grep lngpt-frontend | awk '{print $1}') 2>/dev/null || true
docker build -t lngpt-frontend -f Dockerfile.frontend .
docker run -p 9999:9999 --add-host=host.docker.internal:host-gateway -d lngpt-frontend