# 构建并启动docker

docker build -t maoxiaoyuz/long-novel-gpt .
docker tag maoxiaoyuz/long-novel-gpt maoxiaoyuz/long-novel-gpt:2.1
docker tag maoxiaoyuz/long-novel-gpt maoxiaoyuz/long-novel-gpt:latest
docker run -p 80:80 --env-file .env --add-host=host.docker.internal:host-gateway -d maoxiaoyuz/long-novel-gpt:latest