import json
import os
import re
from datetime import datetime

# 文件路径
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "src", "content", "posts"
)


# 将时间戳转换为日期字符串
def timestamp_to_date(timestamp):
    # 将时间戳转换为datetime对象
    dt = datetime.fromtimestamp(timestamp)
    # 格式化为YYYY-MM-DD格式
    return dt.strftime("%Y-%m-%d")


def parse_second_to_time(duration):
    # 将秒数转换为时间字符串
    hours = duration // 3600
    minutes = (duration % 3600) // 60
    seconds = duration % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    elif minutes > 0:
        return f"{minutes:02d}:{seconds:02d}"
    elif seconds > 0:
        return f"{seconds:02d}"
    return ""


# 生成完整的Markdown文件
def generate_full_md(videos_data):
    # 获取第一个视频的发布时间作为文件名和发布日期
    if not videos_data:
        return None, None

    if videos_data["subtitle"] == "":
        return None, None
    file_name = f"{videos_data['bvid']}.md"

    # 创建Markdown头部信息
    header = f"---\n"
    header += f"title: {videos_data['title']}\n"
    header += f"published: {videos_data['pub_time']}\n"
    header += f"tags: [王者荣耀]\n"
    header += f"category: 磊哥视频\n"
    header += f"draft: false\n"
    header += f"---\n\n"

    # 创建新的Markdown内容
    new_content = header

    # 添加视频的信息
    # body = f"\n![封面]({videos_data['cover']})\n"
    body = f"\n> 作者：[磊哥游戏](https://space.bilibili.com/268941858?spm_id_from=333.788.upinfo.head.click)\n"
    body += f"\n视频字幕：\n"
    body += f"\n{videos_data['subtitle']}\n"
    body += f"\n---\n"
    body += f"\n链接：{videos_data['link']}\n"
    body += f"\n时长：{parse_second_to_time(videos_data['duration'])}\n"
    body += f"\n发布时间：{videos_data['pub_time']}\n"

    new_content += body
    return new_content, file_name


# 保存Markdown文件
def save_md_file(content, file_name):
    if not os.path.exists(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)
    file_path = os.path.join(OUTPUT_DIR, file_name)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"已成功生成Markdown文件: {file_path}")
