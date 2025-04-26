from googleapiclient.discovery import build
import requests

# Google API 密钥和搜索引擎 ID
API_KEY = "AIzaSyDmfPU0aEM3-WgFQRBWUCtvvhIt2NWNvEs"
CSE_ID = "548acf14d5a484725"

# DeepSeek API 配置
OLLAMA_URL = "http://192.168.0.50:11434/api/chat"
MODEL_NAME = "deepseek-r1:32b"
HEADERS = {"Content-Type": "application/json"}

# 设置 Google 搜索 API
def google_search(query, num_results=10):
    service = build("customsearch", "v1", developerKey=API_KEY)
    res = service.cse().list(q=query, cx=CSE_ID, num=num_results).execute()
    return [item['link'] for item in res['items']]  # 返回每条结果的 URL

# 将搜索结果发送给 AI
def ask_deepseek_about(text, user_question):
    messages = [
        {"role": "system", "content": "你是一个根据网络内容回答问题的 AI 助手"},
        {"role": "user", "content": f"请回答这个问题：{user_question}"},
        {"role": "user", "content": f"以下是相关内容：\n{text}"}
    ]
    data = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False
    }
    res = requests.post(OLLAMA_URL, json=data, headers=HEADERS)
    return res.json()["message"]["content"]

# 运行示例
if __name__ == "__main__":
    from bs4 import BeautifulSoup

    def fetch_webpage_text(url):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            }
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text(separator='\n')
            return '\n'.join(line.strip() for line in text.splitlines() if line.strip())[:2000]
        except Exception as e:
            print(f"❌ 无法抓取 {url}：{e}")
            return ""

    query = input("请输入搜索内容：")
    search_urls = google_search(query)

    print("\nGoogle 搜索结果：")
    contents = []
    for idx, url in enumerate(search_urls, 1):
        print(f"{idx}. {url}")
        content = fetch_webpage_text(url)
        if content:
            contents.append(content)

    combined_results = "\n\n".join(contents)

    user_question = input("\n你想问这篇文章什么？\n")
    reply = ask_deepseek_about(combined_results, user_question)

    print("\n🤖 AI 回复：\n")
    print(reply)