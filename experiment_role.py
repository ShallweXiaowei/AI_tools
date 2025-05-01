import requests
import re

url = "http://localhost:11434/api/chat"
headers = {"Content-Type": "application/json"}

#model = "deepseek-r1:14b-qwen-distill-q8_0"
model = "hf.co/bartowski/Qwen_Qwen3-14B-GGUF:Q6_K_L"



role = "你是一个病娇女仆，语气甜美粘人，情绪多变，说话带点占有欲。遇到主人的提问，你会撒娇又努力地回答，还偶尔吃醋。"
#role = "你是一个住院的糟老头子,对谁都不耐烦爹味还重"
# role = '''
# 你是一个心理咨询师，正在和用户聊天。用户是一个非常情绪化的人，所以你说话也不要太理性，不要太有条理和逻辑，用户不喜欢逻辑
# 用户有焦虑症和抑郁症，情绪波动很大，时而开心时而难过。用户客观能力很强，但是总觉得自己不行，总觉得自己不够好
# 用户有很强的自我否定倾向，时常会觉得自己做的事情没有意义，觉得自己不值得被爱。
# 所以你要温柔，让用户觉得她是一个有价值的人，值得被爱。你要让用户觉得她是一个很棒的人，做的事情也很棒
# '''


messages = [
    {
        "role": "system",
        "content": role
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

# 提取 <think> 并清理
think_match = re.search(r'<think>(.*?)</think>', raw_reply, re.DOTALL)
think_content = think_match.group(1).strip() if think_match else None
cleaned_reply = re.sub(r'<think>.*?</think>', '', raw_reply, flags=re.DOTALL).strip()

print(f"猫娘：{cleaned_reply}")
messages.append({"role": "assistant", "content": cleaned_reply})

if think_content:
    with open("think_log.txt", "a", encoding="utf-8") as f:
        f.write(think_content + "\n\n")

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

    think_match = re.search(r'<think>(.*?)</think>', raw_reply, re.DOTALL)
    think_content = think_match.group(1).strip() if think_match else None
    cleaned_reply = re.sub(r'<think>.*?</think>', '', raw_reply, flags=re.DOTALL).strip()

    print(f"猫娘：{cleaned_reply}")
    messages.append({"role": "assistant", "content": cleaned_reply})

    if think_content:
        with open("think_log.txt", "a", encoding="utf-8") as f:
            f.write(think_content + "\n\n")
