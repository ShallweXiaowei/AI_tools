import requests
from bs4 import BeautifulSoup
# from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import re
from push_bark import push_bark
import json
import os



def remove_think(res):
    # 清理 think 标签
    think_match = re.search(r'<think>(.*?)</think>', res, re.DOTALL)
    think_content = think_match.group(1).strip() if think_match else None
    cleaned_reply = re.sub(r'<think>.*?</think>', '', res, flags=re.DOTALL).strip()
    return cleaned_reply
    #print("befoire clearn think:", res)
# === 配置 ===
OLLAMA_URL = "http://localhost:11434/api/chat"
#MODEL_NAME = "deepseek-r1:14b"
#MODEL_NAME = "gemma3:27b"
#MODEL_NAME = "deepseek-r1:14b"
MODEL_NAME = "deepseek-r1:14b-qwen-distill-q8_0"

HEADERS = {"Content-Type": "application/json"}

# GOOGLE_API_KEY = "AIzaSyDmfPU0aEM3-WgFQRBWUCtvvhIt2NWNvEs"  # 请替换
# GOOGLE_CSE_ID = "548acf14d5a484725"  # 请替换

def ask_deepseek(messages, include_datetime=True):
    if include_datetime:
        from datetime import datetime
        now = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
        messages.insert(0, {
            "role": "system",
            "content": f"当前日期和时间是：{now}"
        })
    print(f"当前日期和时间是：{now}")
    data = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "temperature": 0.4,
        #"options": {"num_gpu":1}
    }
    res = requests.post(OLLAMA_URL, json=data, headers=HEADERS)
    res.raise_for_status()
    return res.json()["message"]["content"]

def generate_search_keywords(question):
    messages = [
        {"role": "system", "content": '''
        你是一个信息检索助手，根据用户的问题生成合适的 Google 搜索关键词
        涉及到美国的公司,新闻,财报,股市等问题,用英文关键词搜索
        如果问题包含'最近',就需要用搜索引擎了
         '''},
        {"role": "user", "content": f"请根据这个问题生成几个有用的 Google 搜索关键词：\n\n{question},输出结果只包含关键词.关键词尽量简短以保证涵盖到流量大的网站,最好不要超过10个.当问题涉及到股市,公司财报等信息,用英文关键词搜索"}
    ]
    result = ask_deepseek(messages, include_datetime=True)
    print("############Generating key words:", result)
    ### clearn think
    think_match = re.search(r'<think>(.*?)</think>', result, re.DOTALL)
    think_content = think_match.group(1).strip() if think_match else None
    cleaned_reply = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL).strip()

    # 过滤掉包含 think 标签的内容，确保只返回关键词
    lines = cleaned_reply.replace("\n", ",").split(",")
    keywords = [kw.strip().translate(str.maketrans('', '', '*"\'')) for kw in lines if kw.strip()]
    return keywords

def determine_search_need(question):
    messages = [
        {"role": "system", "content": "你是一个判断专家，负责判断一个问题是否需要搜索引擎获取答案。如果用户问题需要实时信息、数据更新或特定网页信息，请回答 YES，否则回答 NO。只输出 YES 或 NO。"},
        {"role": "user", "content": f"{question}"}
    ]
    result = ask_deepseek(messages, include_datetime=True).strip()
    # 清理 think 标签
    think_match = re.search(r'<think>(.*?)</think>', result, re.DOTALL)
    think_content = think_match.group(1).strip() if think_match else None
    cleaned_reply = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL).strip()


    print("befoire clearn think:", result)
    print( "determine_search_need:", cleaned_reply)
    return cleaned_reply == "YES"

def bing_search(query, max_results=2):
    options = Options()
    options.add_argument("--headless")  # 留空以显示窗口
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)

    driver.get(f"https://www.bing.com/search?q={query}")
    time.sleep(3)  # 等待页面加载完成

    results = driver.find_elements(By.CSS_SELECTOR, 'li.b_algo h2 a')  # 修改 CSS 选择器
    urls = []
    for result in results:
        href = result.get_attribute("href")
        if href and href.startswith("http"):
            urls.append(href)
        if len(urls) >= max_results:
            break

    driver.quit()
    return urls

def fetch_webpage_text(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator='\n')
        #return '\n'.join(line.strip() for line in text.splitlines() if line.strip())[:3000]
        return '\n'.join(line.strip() for line in text.splitlines() if line.strip())
    except Exception as e:
        print(f"❌ 无法抓取 {url}：{e}")
        return ""

def summarize_each_page(text, url, original_question):
    messages = [
        {"role": "system", "content": '''
        你是一个网页摘要助手，会对单一网页内容进行总结, 目标是为了总结信息来回答用户的问题
        如有重要信息，请保留，并附上该网页来源链接。
        '''},
        {"role": "user", "content": f"网页内容来自：{url}\n\n{text}"},
        {"role": "user", "content": f"请总结这篇网页的主要内容,以便回答用户的问题：\n问题是：{original_question}"}
    ]

    result = ask_deepseek(messages, include_datetime=True)
    think_match = re.search(r'<think>(.*?)</think>', result, re.DOTALL)
    think_content = think_match.group(1).strip() if think_match else None
    cleaned_reply = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL).strip()
    print("summarize_each_page:", cleaned_reply)
    return cleaned_reply

def summarize_with_deepseek(text_blocks, original_question):
    messages = [
        {"role": "system", "content": '''
         用户喜欢详细的信息,作为一个助手,会让回答尽量详细, 提供尽可能多的信息
         你会尽量用中文回答问题.
         你会尽量在重要的地方加上数据源链接
         '''},
        {"role": "user", "content": f"请回答这个问题：{original_question}\n你的回答不用严格局限这个问题,可以揣测用户目的,提供更多信息"},
        {"role": "user", "content": f"以下是一些网页内容以供参考 \n\n{text_blocks}"}
    ]
    return ask_deepseek(messages, include_datetime=True)

def safe_filename(name):
    return "".join(c for c in name if c.isalnum() or c in "._- ")[:50]

def save_session(user_question, urls, combined_summary_text, final_summary, save_dir="saved_sessions"):
    from datetime import datetime
    os.makedirs(save_dir, exist_ok=True)
    timestamp = int(time.time())
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_name = safe_filename(user_question)
    filename = os.path.join(save_dir, f"{timestamp}_{date_str}_{safe_name}.json")
    session = {
        "user_question": user_question,
        "urls": urls,
        "combined_summary": combined_summary_text,
        "final_summary": final_summary
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False, indent=2)
    print(f"✅ 本次搜索记录已保存到 {filename}")

def load_session(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        session = json.load(f)
    return session

def list_sessions(save_dir="saved_sessions"):
    if not os.path.exists(save_dir):
        print("⚠️ 暂无保存记录")
        return []
    files = sorted(os.listdir(save_dir), key=lambda x: os.path.getmtime(os.path.join(save_dir, x)), reverse=True)
    for i, f in enumerate(files):
        print(f"{i+1}: {f}")
    return files

def search_sessions(keyword, save_dir="saved_sessions"):
    if not os.path.exists(save_dir):
        print("⚠️ 暂无保存记录")
        return []
    files = sorted(os.listdir(save_dir), key=lambda x: os.path.getmtime(os.path.join(save_dir, x)), reverse=True)
    matched = []
    for i, f in enumerate(files):
        path = os.path.join(save_dir, f)
        with open(path, "r", encoding="utf-8") as fp:
            session = json.load(fp)
            if keyword in session.get("user_question", "") or keyword in session.get("final_summary", ""):
                matched.append((i+1, f))
    if matched:
        for idx, name in matched:
            print(f"{idx}: {name}")
    else:
        print(f"未找到包含关键词 '{keyword}' 的历史记录。")
    return matched

if __name__ == "__main__":
    while True:
        user_input = input("请输入你的问题（或输入 /list /load n /search 关键词 /exit）：\n").strip()
        
        if user_input == "/exit":
            break
        elif user_input == "/list":
            list_sessions()
        elif user_input.startswith("/load"):
            parts = user_input.split()
            if len(parts) < 2:
                print("❗ 用法：/load 编号 [编号2 编号3...]")
                continue
            indices = [int(x) - 1 for x in parts[1:]]
            files = list_sessions()

            combined_text = ""
            for idx in indices:
                if 0 <= idx < len(files):
                    chosen_file = os.path.join("saved_sessions", files[idx])
                    session = load_session(chosen_file)
                    combined_text += session['combined_summary'] + "\n\n"
                else:
                    print(f"⚠️ 忽略无效编号 {idx+1}")

            if not combined_text:
                print("⚠️ 没有成功加载任何内容。")
                continue

            print(f"\n📄 已加载 {len(indices)} 个历史总结。")
            new_question = input("请输入想在这些资料基础上继续提问的问题：\n")

            followup = summarize_with_deepseek(combined_text, new_question)
            print(f"\n✅ AI回答：\n{followup}")
            #push_bark(title="AI分析完成", body=remove_think(followup))
        elif user_input.startswith("/search"):
            keyword = user_input[len("/search"):].strip()
            if not keyword:
                print("❗ 用法：/search 关键词")
            else:
                search_sessions(keyword)
        else:
            user_question = user_input
            if determine_search_need(user_question):
                keywords = generate_search_keywords(user_question)
                print("\n🔍 AI 建议搜索关键词：")
                for kw in keywords:
                    print(f"- {kw}")
            else:
                print("\nℹ️ AI 判断此问题不需要搜索，直接回答...")
                keywords = []

            urls = []
            if keywords:
                for kw in keywords:
                    urls += bing_search(kw)
            urls = list(dict.fromkeys(urls))

            print("\n📄 搜索到的网页：%d" % len(urls))
            for url in urls:
                print(url)

            summaries = []
            for i, url in enumerate(urls, 1):
                print(f"🕸️ 正在抓取第 {i}/{len(urls)} 个网页：{url}")
                content = fetch_webpage_text(url)
                if content:
                    summary = summarize_each_page(content, url, user_question)
                    summaries.append(f"[{url}]\n{summary}")

            combined_summary_text = "\n\n".join(summaries)

            print("\n🤖 正在总结信息，请稍候...\n")
            summary = summarize_with_deepseek(combined_summary_text, user_question)
            print("✅ 总结结果：\n")
            print(summary)

            #push_bark(title="AI分析完成", body=remove_think(summary))
            save_session(user_question, urls, combined_summary_text, summary)
