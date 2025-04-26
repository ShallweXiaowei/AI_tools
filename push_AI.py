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

# ====== 配置区域 ======
questions = {
    "女优":"推荐最近比较火的日本AV女优，详细列出她们的信息"
}

# 指定使用的 LLM 模型
MODEL_NAME = "deepseek-r1:14b-qwen-distill-q8_0"

# 自定义 AI 角色描述
AI_ROLE = '''
    用户喜欢详细的信息,作为一个助手,会让回答尽量详细, 提供尽可能多的信息
    你会尽量用中文回答问题.
    你会尽量在重要的地方加上数据源链接
    你的回答不用严格局限这个问题,可以揣测用户目的,提供更多信息。
'''

# 是否开启推送
ENABLE_PUSH = True

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


def custom_summarize_with_role(text_blocks, user_question):
    messages = [
        {"role": "system", "content": AI_ROLE},
        {"role": "user", "content": f"请回答这个问题：{user_question}\n你的回答可以基于以下网页内容：\n\n{text_blocks}"}
    ]
    return ask_deepseek(messages, include_datetime=True, model=MODEL_NAME)

def auto_process_question(user_question,title = "AI分析完成",ENABLE_PUSH = True):
    if determine_search_need(user_question):
        print(f"🔍 [{user_question}] 判断需要搜索...")
        keywords = generate_search_keywords(user_question)
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
                summary = summarize_each_page(content, url, user_question)
                summaries.append(f"[{url}]\n{summary}")
        
        combined_summary = "\n\n".join(summaries)
        final_answer = custom_summarize_with_role(combined_summary, user_question)

        if urls:
            save_session(user_question, urls, combined_summary, final_answer)

    else:
        print(f"ℹ️ [{user_question}] 判断不需要搜索，直接回答...")
        final_answer = custom_summarize_with_role("", user_question)

    # 推送到 Bark
    if ENABLE_PUSH:
        try:
            trimmed_answer = remove_think(final_answer)
            print(f"推送内容（统一生成网页）：{trimmed_answer}")

            # 统一保存成html网页
            safe_name = safe_filename(user_question)
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"{date_str}_{safe_name}.html"
            #filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
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
    for title, q in questions.items():
        auto_process_question(q,title,ENABLE_PUSH=ENABLE_PUSH)
