# 构建并启动docker

docker build -t maoxiaoyuz/long-novel-gpt:2.0.0 .
docker run -p 80:80 --env-file .env --add-host=host.docker.internal:host-gateway maoxiaoyuz/long-novel-gpt:2.0.0