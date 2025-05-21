import os
import csv
import email
from email.utils import parsedate_to_datetime
from datetime import datetime

MAILDIR_PATH = os.path.expanduser('~/Mail/gmail/[Gmail].Important/')

OUTPUT_CSV = 'mail_file_date_map.csv'

def parse_date(date_str):
    try:
        dt = parsedate_to_datetime(date_str)
        if dt is not None and dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.utcnow().astimezone().tzinfo)
        return dt.isoformat()
    except Exception:
        return ""

def collect_mail_dates(maildir_path):
    results = []
    for root, _, files in os.walk(maildir_path):
        for fname in files:
            if fname.startswith("."):
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, 'rb') as f:
                    msg = email.message_from_binary_file(f)
                    date_str = msg.get('Date', '')
                    date = parse_date(date_str)
                    results.append((path, date))
            except Exception as e:
                print(f"跳过: {path} 错误: {e}")
    return results

def save_to_csv(records, output_file):
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['file_path', 'date'])
        writer.writerows(records)
    print(f"✅ 已保存 CSV：{output_file}")

if __name__ == '__main__':
    data = collect_mail_dates(MAILDIR_PATH)
    save_to_csv(data, OUTPUT_CSV)