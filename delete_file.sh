#!/bin/bash

# 输入关键词
read -p "请输入要查找的关键字（keyword）: " keyword

# 查找符合条件的文件，保存到数组
mapfile -t files < <(find . -type f -iname "*$keyword*")

# 如果没有找到文件
if [ ${#files[@]} -eq 0 ]; then
    echo "没有找到匹配的文件。"
    exit 0
fi

# 显示找到的文件列表
echo "找到以下文件："
for file in "${files[@]}"; do
    echo "$file"
done

# 统一询问是否删除
read -p "是否要删除以上所有文件？(y/n): " confirm
if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
    for file in "${files[@]}"; do
        rm "$file"
        echo "已删除: $file"
    done
    echo "✅ 所有文件已删除。"
else
    echo "❌ 未删除任何文件。"
fi
