# 单独构建并运行后端
docker rm -f $(docker ps -a | grep lngpt-backend | awk '{print $1}') 2>/dev/null || true
cd ..
docker build -t lngpt-backend -f backend/Dockerfile.backend .
docker run -p 7869:7869 --add-host=host.docker.internal:host-gateway -d lngpt-backend

# 添加host.docker.internal是为了访问mongodb服务
