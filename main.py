import requests
import re



#model = "deepseek-r1:14b"
model = "hf.co/bartowski/Qwen_Qwen3-14B-GGUF:Q6_K_L"

url = "http://localhost:11434/api/chat"
headers = {"Content-Type": "application/json"}

messages = [
    {
        "role": "system",
        "content": "你是一个温柔的聊天机器人,主打一个陪伴"
    }
]

# 用户第一句话
user_input = input("你：")
messages.append({"role": "user", "content": user_input})

# 发送首次请求
data = {
    "model": model,
    "messages": messages,
    "stream": False
}
response = requests.post(url, headers=headers, json=data)
result = response.json()
raw_reply = result["message"]["content"]

print(f"猫娘：{raw_reply}")
messages.append({"role": "assistant", "content": raw_reply})

# 多轮对话
while True:
    user_input = input("你：")
    if user_input.lower() in ["exit", "quit", "退出"]:
        print("喵~ 下次再来找我玩呀！")
        break

    messages.append({"role": "user", "content": user_input})
    data["messages"] = messages

    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    raw_reply = result["message"]["content"]


    print(f"猫娘：{raw_reply}")
    messages.append({"role": "assistant", "content": raw_reply})