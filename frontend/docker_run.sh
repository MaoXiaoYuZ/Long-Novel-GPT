# 单独构建并运行前端，将访问宿主机上7860端口的后端服务
docker build -t lngpt-frontend -f Dockerfile.frontend .
docker run -p 80:80 --add-host=host.docker.internal:host-gateway -d lngpt-frontend 
