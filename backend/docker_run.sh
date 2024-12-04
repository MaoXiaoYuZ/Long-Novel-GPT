# 单独构建并运行后端
cd ..
docker build -t lngpt-backend -f backend/Dockerfile.backend .
docker run -p 7860:7860 --add-host=host.docker.internal:host-gateway lngpt-backend

# 添加host.docker.internal是为了访问mongodb服务
