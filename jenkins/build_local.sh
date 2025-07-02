#!/bin/bash
# 用法: ./build_local.sh
# 本地构建discourse镜像

# 将discourse_config 的配置文件拷贝至containers中
cp ../containers/web_only.yml ../../containers/web_only.yml

# 定义需要修改的文件
FILE="../../containers/web_only.yml"

# 检查文件是否存在
if [ ! -f "$FILE" ]; then
  echo "错误：文件 '$FILE' 不存在。"
  exit 1
fi

# 查找现有行的缩进级别
indent=2  # 默认缩进为2个空格
# 创建缩进字符串
indent_str=$(printf "%${indent}s" "")
sed -i -E "
/redis\.template\.yml/ {
    s/^[[:space:]]*#[[:space:]]*(-[[:space:]]*\"templates\/redis\.template\.yml\")[[:space:]]*$/${indent_str}\1/
    t
    s/^[[:space:]]*#[[:space:]]*(\"templates\/redis\.template\.yml\")[[:space:]]*$/${indent_str}-\1/
}
/postgres\.template\.yml/ {
    s/^[[:space:]]*#[[:space:]]*(-[[:space:]]*\"templates\/postgres\.template\.yml\")[[:space:]]*$/${indent_str}\1/
    t
    s/^[[:space:]]*#[[:space:]]*(\"templates\/postgres\.template\.yml\")[[:space:]]*$/${indent_str}-\1/
}
" "$FILE"

# 使用 sed 注释包含 discourse-easecheck 的 git clone 行
sed -i '/git clone.*discourse-easecheck/s/^\([[:space:]]*-\)/# \1/' "$FILE"

echo "文件 '$FILE' 已成功修改。"
echo "请检查内容是否正确："
# cat "$FILE"

# 启动构建
cd ../../ || exit 1
./launcher bootstrap web_only
