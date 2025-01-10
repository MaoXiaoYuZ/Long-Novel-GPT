#!/bin/bash

# 设置默认值
FRONTEND_PORT=${FRONTEND_PORT:-80}
BACKEND_PORT=${BACKEND_PORT:-7869}
BACKEND_HOST=${BACKEND_HOST:-0.0.0.0}
WORKERS=${WORKERS:-4}
THREADS=${THREADS:-2}
TIMEOUT=${TIMEOUT:-120}

# 在Linux环境下添加host.docker.internal解析
# if ! grep -q "host.docker.internal" /etc/hosts; then
#     DOCKER_INTERNAL_HOST="$(ip route | grep default | awk '{print $3}')"
#     echo "$DOCKER_INTERNAL_HOST host.docker.internal" >> /etc/hosts
# fi

# 替换nginx配置中的端口
sed -i "s/listen 9999/listen $FRONTEND_PORT/g" /etc/nginx/conf.d/default.conf
sed -i "s/host.docker.internal:7869/localhost:$BACKEND_PORT/g" /etc/nginx/conf.d/default.conf

# 启动nginx
nginx

# 启动gunicorn
gunicorn --bind $BACKEND_HOST:$BACKEND_PORT \
    --workers $WORKERS \
    --threads $THREADS \
    --worker-class gthread \
    --timeout $TIMEOUT \
    --access-logfile - \
    --error-logfile - \
    app:app