from AI_search import (
    determine_search_need, generate_search_keywords, bing_search,
    fetch_webpage_text, summarize_each_page, summarize_with_deepseek,
    save_session, ask_deepseek, remove_think,safe_filename
)
from push_bark import push_bark
from tqdm import tqdm  # Add tqdm for progress bar
import os
import time
from datetime import datetime
import subprocess
import argparse
import json
import urllib.parse

# ====== 主程序 ======
# 获取 ZeroTier 分配的本地 IP
def get_zerotier_ip():
    try:
        output = subprocess.check_output(["sudo","/usr/sbin/zerotier-cli", "listnetworks"], encoding="utf-8")
        for line in output.splitlines():
            if "OK PRIVATE" in line:
                parts = line.split()
                ip_info = parts[-1]  # Last field
                ips = ip_info.split(",")
                # Find IPv4 address (not fd开头的IPv6地址)
                for ip in ips:
                    if "." in ip:
                        return ip.split("/")[0]
    except Exception as e:
        print(f"⚠️ 获取 ZeroTier IP 失败: {e}")
    return "127.0.0.1"  # fallback

def safe_filename(name):
    name = name.replace(" ", "_")
    return "".join(c for c in name if c.isalnum() or c in "._-")[:100]

def save_html(content, filename):
    output_dir = "html_outputs"
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>{filename}</title>
        </head>
        <body style="font-family:sans-serif;line-height:1.6;padding:2em;">
            <h2>{filename}</h2>
            <p>{content.replace('\n', '<br>')}</p>
        </body>
        </html>
        """)
    return filepath


def custom_summarize_with_role(text_blocks, user_question, ai_role, model_name):
    messages = [
        {"role": "system", "content": ai_role},
        {"role": "user", "content": f"请回答这个问题：{user_question}\n你的回答可以基于以下网页内容：\n\n{text_blocks}"}
    ]
    return ask_deepseek(messages, include_datetime=True, model=model_name)

def auto_process_question(user_question, title, ENABLE_PUSH, ai_role, model_name):
    if determine_search_need(user_question, model=model_name):
        print(f"🔍 [{user_question}] 判断需要搜索...")
        keywords = generate_search_keywords(user_question, model=model_name)
        urls = []
        for kw in keywords:
            urls += bing_search(kw)
        urls = list(dict.fromkeys(urls))
        print(f"🕸️ 搜索到 {len(urls)} 个网页")

        summaries = []
        # Add progress bar for URL fetching
        for url in tqdm(urls, desc="Fetching URLs"):
            content = fetch_webpage_text(url)
            print(f"📝 正在分析网页：{url}")
            if content:
                summary = summarize_each_page(content, url, user_question, model=model_name)
                summaries.append(f"[{url}]\n{summary}")
        
        combined_summary = "\n\n".join(summaries)
        print(f"📝 汇总网页内容：\n{combined_summary}")
        final_answer = custom_summarize_with_role(combined_summary, user_question, ai_role, model_name)

        if urls:
            save_session(user_question, urls, combined_summary, final_answer)

    else:
        print(f"ℹ️ [{user_question}] 判断不需要搜索，直接回答...")
        final_answer = custom_summarize_with_role("", user_question, ai_role, model_name)

    # 推送到 Bark
    if ENABLE_PUSH:
        try:
            trimmed_answer = remove_think(final_answer)
            #print(f"推送内容（统一生成网页）：{trimmed_answer}")

            # 统一保存成html网页，限制文件名长度
            safe_name = safe_filename(user_question)[:50]  # 限制 base 名长度
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"{date_str}_{safe_name}.html"
            if len(filename) > 80:
                filename = filename[:80] + '.html'
            save_html(trimmed_answer, filename)

            # 获取 ZeroTier 分配的本机 IP
            local_ip = get_zerotier_ip()
            link = f"http://{local_ip}:5000/outputs/{filename}"
            body = f"点击链接查看完整回答：\n{link}"

            short_title = title.strip()[:15]
            push_bark(title=f"回答完成 - {short_title}", body=body)
        except Exception as e:
            print(f"❌ 推送失败：{e}")

    print("✅ 完成处理！")
    print("-" * 50)
    print(final_answer)
    return final_answer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto process AI questions")
    parser.add_argument('config', help='Path to configuration JSON file')
    args = parser.parse_args()

    config_path = os.path.join("config_file", args.config)
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    questions = config.get("questions", {})
    MODEL_NAME = config.get("model_name")
    AI_ROLE = config.get("ai_role")
    ENABLE_PUSH = config.get("enable_push", True)

    for title, q in questions.items():
        print(q,title,ENABLE_PUSH,AI_ROLE,MODEL_NAME)
        auto_process_question(q, title, ENABLE_PUSH, AI_ROLE, MODEL_NAME)
