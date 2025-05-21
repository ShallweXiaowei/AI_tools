import os
import email
from datetime import datetime, timedelta
import requests
from tqdm import tqdm

# 配置参数
MAILDIR_PATH = os.path.expanduser("~/Mail/gmail/[Gmail].All Mail/")  # 根据你的实际路径调整
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "hf.co/bartowski/Qwen_Qwen3-14B-GGUF:Q6_K_L"
HOURS = 8  # 修改这里控制“最近几小时”

# 解析邮件日期
def parse_email_date(date_str):
    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        if dt is not None and dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.utcnow().astimezone().tzinfo)
        return dt
    except Exception:
        return None

# 遍历 Maildir 提取最近邮件
def get_recent_emails(maildir_path, limit=20):
    all_emails = []

    for root, _, files in os.walk(maildir_path):
        for fname in tqdm(files, desc=f"📨 扫描 {root}", unit="封"):
            if fname.startswith("."):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'rb') as f:
                    msg = email.message_from_binary_file(f)
                    subject = msg.get("Subject", "")
                    date_str = msg.get("Date", "")
                    dt = parse_email_date(date_str)
                    if dt is None:
                        continue
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                charset = part.get_content_charset() or 'utf-8'
                                body += part.get_payload(decode=True).decode(charset, errors="ignore")
                    else:
                        charset = msg.get_content_charset() or 'utf-8'
                        body = msg.get_payload(decode=True).decode(charset, errors="ignore")
                    all_emails.append((
                        dt,
                        {
                            "from": msg.get("From", ""),
                            "subject": subject,
                            "date": date_str,
                            "body": body.strip(),
                            "path": fpath
                        }
                    ))
            except Exception as e:
                print(f"跳过邮件: {fpath} 错误: {e}")

    all_emails.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in all_emails[:limit]]

# 调用 Ollama 发送邮件内容请求 AI 判断
def ask_ai(emails):
    if not emails:
        print("✅ 最近无新邮件")
        return
    summary = "\n\n".join(
        f"发件人: {m['from']}\n主题: {m['subject']}\n时间: {m['date']}\n内容: {m['body'][:1000]}" for m in emails
    )
    print(summary)
    prompt = "请判断以下邮件哪些重要，并简要说明理由,用中文回答：\n\n" + summary
    res = requests.post(OLLAMA_URL, json={
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    })
    res.raise_for_status()
    print("\n📌 AI 分析结果：\n")
    print(res.json()["message"]["content"])

if __name__ == "__main__":
    emails = get_recent_emails(MAILDIR_PATH, limit=20)
    ask_ai(emails)