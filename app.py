from flask import Flask, request, render_template
from AI_search import (determine_search_need, generate_search_keywords, bing_search,
                        fetch_webpage_text, summarize_each_page, summarize_with_deepseek,
                        save_session, list_sessions, load_session)
import os

app = Flask(__name__)  # 一定要先创建 Flask 应用对象！

@app.route("/", methods=["GET", "POST"])
def index():
    answer = ""
    if request.method == "POST":
        user_input = request.form["command"].strip()

        if user_input == "/exit":
            answer = "✅ 已退出（浏览器模式无实际退出操作）。"
        elif user_input == "/list":
            sessions = list_sessions()
            answer = "\n".join(sessions) if sessions else "⚠️ 没有保存的记录。"
        elif user_input.startswith("/load"):
            parts = user_input.split()
            if len(parts) < 2:
                answer = "❗ 用法：/load 编号 [编号2 编号3...]"
            else:
                indices = [int(x)-1 for x in parts[1:]]
                files = list_sessions()
                combined_text = ""
                for idx in indices:
                    if 0 <= idx < len(files):
                        session = load_session(os.path.join("saved_sessions", files[idx]))
                        combined_text += session['combined_summary'] + "\n\n"
                if combined_text:
                    answer = "✅ 已加载所选记录，现在请输入新的提问。"
                    # 保存到一个临时文件
                    with open("temp_combined_summary.txt", "w", encoding="utf-8") as f:
                        f.write(combined_text)
                else:
                    answer = "⚠️ 没有成功加载任何记录。"
        elif user_input.startswith("/search"):
            keyword = user_input[len("/search"):].strip()
            if not keyword:
                answer = "❗ 用法：/search 关键词"
            else:
                matches = []
                files = list_sessions()
                for i, f in enumerate(files):
                    path = os.path.join("saved_sessions", f)
                    session = load_session(path)
                    if keyword in session.get("user_question", "") or keyword in session.get("final_summary", ""):
                        matches.append(f"{i+1}: {f}")
                answer = "\n".join(matches) if matches else f"未找到关键词 '{keyword}' 的相关记录。"
        else:
            # 普通提问
            if os.path.exists("temp_combined_summary.txt"):
                # 如果之前 load 过，用历史内容回答
                with open("temp_combined_summary.txt", "r", encoding="utf-8") as f:
                    combined_text = f.read()
                answer = summarize_with_deepseek(combined_text, user_input)
                os.remove("temp_combined_summary.txt")
            else:
                if determine_search_need(user_input):
                    keywords = generate_search_keywords(user_input)
                    urls = []
                    for kw in keywords:
                        urls += bing_search(kw)
                    urls = list(dict.fromkeys(urls))
                    summaries = []
                    for url in urls:
                        content = fetch_webpage_text(url)
                        if content:
                            summary = summarize_each_page(content, url, user_input)
                            summaries.append(f"[{url}]\n{summary}")
                    combined_summary = "\n\n".join(summaries)
                    answer = summarize_with_deepseek(combined_summary, user_input)
                    save_session(user_input, urls, combined_summary, answer)
                else:
                    answer = summarize_with_deepseek("", user_input)

    return render_template("index.html", answer=answer)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)