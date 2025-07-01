#!/bin/bash
# 用法: ./discourse_build.sh <workspace> <discourse_base_image> <maxmind_key> <postgre_user> <postgre_pass> 
#                            <github_user> <github_pass> <developer_emails>


# 参数校验
if [ $# -ne 8 ]; then
  echo "错误: 需要8个参数"
  echo "用法: $0 <workspace> <discourse_base_image> <maxmind_key> <postgre_user> <postgre_pass> <github_user> <github_pass>  <developer_emails>"
  exit 1
fi

# 分配参数
WORKSPACE="$1"
DISCOURSE_BASE_IMAGE="$2"
MAXMIND_LICENSE_KEY="$3"
POSTGRE_USER="$4"
POSTGRE_PASSWORD="$5"
DISCOURSE_GITHUB_USER="${6}"
DISCOURSE_GITHUB_PASS="${7}"
DEVELOPER_EMAILS="${8}"

# 进入工作目录
cd "$WORKSPACE" || exit 1

# 更新基础镜像版本
IMAGE_VERSION="image=\"$DISCOURSE_BASE_IMAGE\""
sed -i "s|image=\"discourse/base:2.0.20250226-0128\"|$IMAGE_VERSION|" ./launcher

# 调试输出
base_image=$(awk 'NR==94{print $1}' ./launcher)
echo "######### 基础镜像: $base_image #########"

#############################################################
######## 构建前配置 web_only.yml ##############
cd containers || exit 1

# 使用参数更新配置
sed -i "s|DISCOURSE_MAXMIND_LICENSE_KEY:.*|DISCOURSE_MAXMIND_LICENSE_KEY: $MAXMIND_LICENSE_KEY|" ./web_only.yml
sed -i "s|DISCOURSE_DEVELOPER_EMAILS:.*|DISCOURSE_DEVELOPER_EMAILS: $DEVELOPER_EMAILS|" ./web_only.yml
sed -i "s|DISCOURSE_DB_USERNAME:.*|DISCOURSE_DB_USERNAME: $POSTGRE_USER|" ./web_only.yml
sed -i "s|DISCOURSE_DB_PASSWORD:.*|DISCOURSE_DB_PASSWORD: $POSTGRE_PASSWORD|" ./web_only.yml
sed -i "s|DISCOURSE_DB_HOST:.*|DISCOURSE_DB_HOST: 192.168.1.38|" ./web_only.yml
sed -i "s|DISCOURSE_REDIS_HOST:.*|DISCOURSE_REDIS_HOST: 192.168.1.166|" ./web_only.yml
sed -i "s|GIT_USERNAME|$DISCOURSE_GITHUB_USER|" ./web_only.yml
sed -i "s|GIT_PASSWORD|$DISCOURSE_GITHUB_PASS|" ./web_only.yml

# 检查并启动Redis
if ! docker ps --format '{{.Names}}' | grep -q discourse-redis; then
  echo "启动Redis实例..."
  docker pull swr.cn-north-4.myhuaweicloud.com/opensourceway/discourse/redis:7.0.5
  docker run -d --restart=always -p 6379:6379 \
    --name discourse-redis \
    swr.cn-north-4.myhuaweicloud.com/opensourceway/discourse/redis:7.0.5 \
    redis-server --protected-mode no
else
  echo "Redis容器已存在"
fi

# 启动构建
cd .. || exit 1
./launcher bootstrap web_only
