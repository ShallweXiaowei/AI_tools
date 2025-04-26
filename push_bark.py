import requests

bark_key = "272nuNgyaZGhjSFUS6vAyL"

def push_bark(title, body, url=None):
    """
    发送推送到 iPhone Bark App（新版标准）
    :param title: 通知标题
    :param body: 通知正文
    :param url: 可选，点击通知跳转的链接
    """
    base_url = f"https://api.day.app/{bark_key}"

    params = {
        "title": title,
        "body": body
    }
    if url:
        params["url"] = url

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        print("✅ 推送成功！")
    except Exception as e:
        print(f"❌ 推送失败：{e}")

if __name__ == "__main__":
    # 测试推送
    push_bark(
        title="AI分析完成",
        body="你今天的数据总结已经生成啦！哈哈哈哈哈哈哈哈哈哈哈"
    )