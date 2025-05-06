from flask import Flask, render_template_string, send_from_directory
import os
from datetime import datetime

app = Flask(__name__)

# Logging setup
import logging
logging.basicConfig(filename='server.log', level=logging.INFO)

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
    app.logger.info("Accessed file list")
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
    app.logger.info(f"Serving file: {filename}")
    return send_from_directory(OUTPUT_DIR, filename)

@app.template_filter('datetimeformat')
def datetimeformat(value):
    return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')


# Icon routes for favicon and Apple touch icons
from flask import send_file
import io

@app.route('/favicon.ico')
@app.route('/apple-touch-icon.png')
@app.route('/apple-touch-icon-precomposed.png')
def empty_icon():
    # Return a 1x1 transparent PNG
    icon_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\xdacd\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x03\xd2\x00\x00\x00\x00IEND\xaeB`\x82'
    return send_file(io.BytesIO(icon_bytes), mimetype='image/png')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)