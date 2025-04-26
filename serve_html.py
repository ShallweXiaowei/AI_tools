from flask import Flask, render_template_string, send_from_directory
import os
from datetime import datetime

app = Flask(__name__)

OUTPUT_DIR = 'html_outputs'

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>分析记录</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif;
            padding: 2em;
            background-color: #f9f9f9;
            color: #333;
        }
        h1 {
            text-align: center;
            margin-bottom: 1em;
        }
        ul {
            list-style-type: none;
            padding: 0;
        }
        li {
            margin: 0.5em 0;
        }
        a {
            color: #007aff;
            text-decoration: none;
            font-size: 18px;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <h1>分析记录</h1>
    <ul>
        {% for file, mtime in files %}
        <li><a href="/outputs/{{ file }}">{{ file }}</a> — <small>{{ mtime | datetimeformat }}</small></li>
        {% endfor %}
    </ul>
</body>
</html>
"""

@app.route('/')
def list_files():
    files = []
    try:
        for f in os.listdir(OUTPUT_DIR):
            full_path = os.path.join(OUTPUT_DIR, f)
            if os.path.isfile(full_path):
                modified_time = os.path.getmtime(full_path)
                files.append((f, modified_time))
        files = sorted(files, key=lambda x: x[1], reverse=True)
    except FileNotFoundError:
        pass
    return render_template_string(INDEX_TEMPLATE, files=files)

@app.route('/outputs/<path:filename>')
def serve_file(filename):
    return send_from_directory(OUTPUT_DIR, filename)

@app.template_filter('datetimeformat')
def datetimeformat(value):
    return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)