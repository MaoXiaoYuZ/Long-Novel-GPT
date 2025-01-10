# 构建并启动docker
# docker build -t maoxiaoyuz/long-novel-gpt .
docker build --network host --build-arg HTTP_PROXY=http://127.0.0.1:7890 --build-arg HTTPS_PROXY=http://127.0.0.1:7890 -t maoxiaoyuz/long-novel-gpt .
docker tag maoxiaoyuz/long-novel-gpt maoxiaoyuz/long-novel-gpt:2.2
docker tag maoxiaoyuz/long-novel-gpt maoxiaoyuz/long-novel-gpt:latest
docker run -p 80:80 --env-file .env --add-host=host.docker.internal:host-gateway -d maoxiaoyuz/long-novel-gpt:latest