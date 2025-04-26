import requests
from bs4 import BeautifulSoup
# from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import re
# === 配置 ===
OLLAMA_URL = "http://192.168.0.50:11434/api/chat"
MODEL_NAME = "deepseek-r1:32b"
HEADERS = {"Content-Type": "application/json"}

# GOOGLE_API_KEY = "AIzaSyDmfPU0aEM3-WgFQRBWUCtvvhIt2NWNvEs"  # 请替换
# GOOGLE_CSE_ID = "548acf14d5a484725"  # 请替换

def ask_deepseek(messages, include_datetime=False):
    if include_datetime:
        from datetime import datetime
        now = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
        messages.insert(0, {
            "role": "system",
            "content": f"当前日期和时间是：{now}"
        })
    data = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "temperature": 0.2      
    }
    res = requests.post(OLLAMA_URL, json=data, headers=HEADERS)
    res.raise_for_status()
    return res.json()["message"]["content"]

def generate_search_keywords(question):
    messages = [
        {"role": "system", "content": '''
        你是一个信息检索助手，根据用户的问题生成合适的 Google 搜索关键词
        默认情况下Market 指的是美国市场.
        作为一个严谨的助手,你会尽量在每一个观点后面附上最关键的数据来源.
         '''},
        {"role": "user", "content": f"请根据这个问题生成几个有用的 Google 搜索关键词,搜索尽量用英文获取：\n\n{question},输出结果只包含关键词,一个其他多余的字都不要有"}
    ]
    result = ask_deepseek(messages, include_datetime=True)
    ### clearn think
    think_match = re.search(r'<think>(.*?)</think>', result, re.DOTALL)
    think_content = think_match.group(1).strip() if think_match else None
    cleaned_reply = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL).strip()

    # 过滤掉包含 think 标签的内容，确保只返回关键词
    keywords = [re.sub(r'^\d+[\.\)]\s*', '', kw).translate(str.maketrans('', '', '*"\'')) for kw in cleaned_reply.splitlines() if kw.strip()]
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

def bing_search(query, max_results=3):
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
        return '\n'.join(line.strip() for line in text.splitlines() if line.strip())[:2000]
    except Exception as e:
        print(f"❌ 无法抓取 {url}：{e}")
        return ""

def summarize_with_deepseek(text_blocks, original_question):
    messages = [
        {"role": "system", "content": '''
         你是一个严谨的信息分析助手。你只能基于提供的文本和公开事实作答，不允许假设或猜测.
         你有良好的习惯,会在重要的观点后面附上最主要的数据来源的链接,供用户交叉验证.
         '''},
        {"role": "user", "content": f"以下是一些网页内容，请基于这些信息来回答这个问题：{original_question}\n\n{text_blocks}"}
    ]
    return ask_deepseek(messages, include_datetime=True)

if __name__ == "__main__":
    user_question = input("请输入你的问题：\n")
    if determine_search_need(user_question):
        keywords = generate_search_keywords(user_question)
        print("\n🔍 AI 建议搜索关键词：")
        for kw in keywords:
            print(f"- {kw}")
    else:
        print("\nℹ️ AI 判断此问题不需要搜索，直接回答ß...")
        keywords = []

    urls = []
    if keywords:
        for kw in keywords:
            urls += bing_search(kw)

    print("\n📄 搜索到的网页：%d"%len(urls))
    for url in urls:
        print(url)

    contents = []
    for i, url in enumerate(urls, 1):
        print(f"🕸️ 正在抓取第 {i}/{len(urls)} 个网页：{url}")
        content = fetch_webpage_text(url)
        if content:
            contents.append(content)
    combined_text = "\n\n".join(contents)

    print("\n🤖 正在总结信息，请稍候...\n")
    summary = summarize_with_deepseek(combined_text, user_question)
    print("✅ 总结结果：\n")
    print(summary)
    #print(bing_search("python"))
