import os
import mailbox
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path
from bs4 import BeautifulSoup

from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
from tqdm import tqdm

MAILDIR = os.path.expanduser("~/Mail/gmail/[Gmail].All Mail")

def decode_mime_header(value):
    if value is None:
        return ''
    parts = decode_header(value)
    decoded = []
    for text, encoding in parts:
        try:
            if isinstance(text, bytes):
                decoded.append(text.decode(encoding or 'utf-8', errors='replace'))
            else:
                decoded.append(text)
        except LookupError:
            decoded.append(text.decode('utf-8', errors='replace') if isinstance(text, bytes) else text)
    return ''.join(decoded)

def clean_email_body(raw_body):
    soup = BeautifulSoup(raw_body, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator='\n')
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    return cleaned

def extract_plain_text(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get('Content-Disposition', '').startswith('attachment'):
                return clean_email_body(part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace'))
    else:
        return clean_email_body(msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='replace'))
    return ''

def get_all_mails(maildir_path):
    # 收集所有邮件文件
    mail_files = list(Path(maildir_path, "cur").glob("*")) + list(Path(maildir_path, "new").glob("*"))
    mail_files = sorted(mail_files, key=os.path.getmtime, reverse=True)

    results = []
    for path in tqdm(mail_files, desc="Processing emails"):
        with open(path, 'rb') as f:
            msg = email.message_from_binary_file(f)

        subject = decode_mime_header(msg['subject'])
        sender = decode_mime_header(msg['from'])
        date = decode_mime_header(msg['date'])
        body = extract_plain_text(msg)

        results.append({
            "from": sender,
            "subject": subject,
            "date": date,
            "body": body.strip()
        })
    return results

def clean_surrogates(obj):
    if isinstance(obj, str):
        return obj.encode('utf-8', 'surrogatepass').decode('utf-8', 'ignore')
    elif isinstance(obj, list):
        return [clean_surrogates(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: clean_surrogates(v) for k, v in obj.items()}
    else:
        return obj
    
# 主程序调用
if __name__ == "__main__":
    mails = get_all_mails(MAILDIR)
    for i, mail in enumerate(mails):
        print(f"📧 Mail {i+1}")
        print(f"From: {mail['from']}")
        print(f"Date: {mail['date']}")
        print(f"Subject: {mail['subject']}")
        print(f"Body:\n{mail['body'].encode('utf-8', 'ignore').decode('utf-8')}")  # 可调 body 长度
        print("="*60)
    import json

    # 将邮件写入 JSON 文件（使用临时文件再原子替换）
    with open("my_text/recent_emails.json.tmp", "w", encoding="utf-8") as f:
        json.dump(clean_surrogates(mails), f, ensure_ascii=False, indent=2)
    os.replace("my_text/recent_emails.json.tmp", "my_text/recent_emails.json")
    print("✅ 已保存 my_text/recent_emails.json")

    # 向量化邮件内容
    model = SentenceTransformer("all-MiniLM-L6-v2")
    def sanitize_text(text):
        if not isinstance(text, str):
            return ""
        return text.encode("utf-8", "ignore").decode("utf-8")

    contents = [
        sanitize_text(mail.get("subject", "")) + "\n" + sanitize_text(mail.get("body", ""))
        for mail in mails
        if isinstance(mail, dict)
    ]
    embeddings = model.encode(contents, convert_to_numpy=True)

    # 构建 FAISS 索引
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # 保存向量和索引
    np.save("my_text/email_vectors.npy", embeddings)
    faiss.write_index(index, "my_text/email_index.faiss")
    print("✅ 向量化完成，已保存至 my_text/email_vectors.npy 和 email_index.faiss")