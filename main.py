import os
import platform
import subprocess
import threading
import argparse
from flask import Flask, send_file, request, render_template_string

app = Flask(__name__)

# 解析命令行参数
parser = argparse.ArgumentParser(description='HTTP File Server')
parser.add_argument('--root', type=str, default=os.getcwd(),
                    help='Root directory for the file server (default: current directory)')
parser.add_argument('--port', type=int, default=8080,
                    help='Port to run the server on (default: 8080)')
parser.add_argument('--no-browser', action='store_true',
                    help='Do not automatically open browser')
args = parser.parse_args()

# 设置根目录并确保路径有效
ROOT_DIR = os.path.abspath(args.root)
if not os.path.exists(ROOT_DIR):
    print(f"Error: Specified root directory does not exist: {ROOT_DIR}")
    exit(1)
if not os.path.isdir(ROOT_DIR):
    print(f"Error: Specified root path is not a directory: {ROOT_DIR}")
    exit(1)

PORT = args.port

def open_in_file_browser(path):
    """Open a file/folder using system default file explorer"""
    abs_path = os.path.abspath(path)

    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            if os.path.isdir(abs_path):
                subprocess.Popen(["open", abs_path])
            else:
                # Open parent directory and select file
                subprocess.Popen(["open", "-R", abs_path])
        elif system == "Windows":
            if os.path.isfile(abs_path):
                # Open folder and select file
                subprocess.Popen(f'explorer /select,"{abs_path}"', shell=True)
            else:
                subprocess.Popen(f'explorer "{abs_path}"', shell=True)
        else:  # Linux variants
            if os.path.isfile(abs_path):
                abs_path = os.path.dirname(abs_path)
            subprocess.Popen(["xdg-open", abs_path])
    except Exception as e:
        print(f"Error opening file browser: {e}")

@app.route('/')
@app.route('/<path:subpath>')
def list_dir(subpath=''):
    """List directory contents with folders first and include parent directory link"""
    current_path = os.path.join(ROOT_DIR, subpath)

    # 检查是否超出根目录范围
    if not os.path.commonpath([ROOT_DIR, os.path.abspath(current_path)]).startswith(ROOT_DIR):
        return "Access denied: Path is outside root directory", 403

    # Serve files directly
    if os.path.isfile(current_path):
        return send_file(current_path)

    # List directory contents
    if not os.path.isdir(current_path):
        return "Path not found", 404

    # Separate folders and files
    folders = []
    files = []

    # Add parent directory link
    if subpath:  # Only add parent link if not at root
        parent_path = os.path.dirname(subpath)
        # Ensure we don't navigate above root
        if parent_path.startswith(ROOT_DIR) or not parent_path:
            folders.append(('..', parent_path, True))

    # Organize entries into folders and files
    for name in sorted(os.listdir(current_path)):
        full_path = os.path.join(current_path, name)
        entry_path = os.path.join(subpath, name).replace('\\', '/')
        is_dir = os.path.isdir(full_path)

        if is_dir:
            folders.append((name, entry_path, True))
        else:
            files.append((name, entry_path, False))

    # Sort each group alphabetically (case-insensitive)
    folders.sort(key=lambda x: x[0].lower())
    files.sort(key=lambda x: x[0].lower())

    # Combine with folders first
    entries = folders + files

    # Generate HTML with enhanced clickable areas
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>File Server - {{ root }}</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 20px auto; padding: 0 15px; }
        .entry { display: flex; align-items: center; padding: 5px; }
        .entry:hover { background-color: #f0f0f0; }
        .name-container { flex-grow: 1; }
        .clickable-name { display: flex; align-items: center; }
        a.name-link {
            display: block;
            flex-grow: 1;
            text-decoration: none;
            padding: 5px 0;
        }
        /* 文件夹链接颜色 */
        .folder .name-link {
            color: #1a73e8;
            font-weight: bold;
        }
        /* 文件链接颜色 */
        .file .name-link {
            color: #000000;
        }
        /* 文件名字体颜色 - 优化添加 */
        .folder-name {
            color: #1a73e8; /* 与文件夹链接相同的蓝色 */
            font-weight: bold;
        }
        .file-name {
            color: #000000; /* 纯黑色 */
        }
        /* 父目录链接样式 */
        .parent-dir .name-link {
            color: #555;
            font-style: italic;
            font-weight: normal;
        }
        a.name-link:hover { background-color: #e6f0ff; }
        .file-type {
            color: #888;
            margin-left: 8px;
            font-size: 0.9em;
        }
        .folder .file-type { color: #1a73e8; }
        .file .file-type { color: #666; }
        .open-btn {
            margin-left: 10px;
            padding: 4px 8px;
            cursor: pointer;
            background-color: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 3px;
        }
        .open-btn:hover {
            background-color: #e9e9e9;
        }
        .header-info {
            background-color: #f8f9fa;
            padding: 10px 15px;
            border-radius: 5px;
            margin-bottom: 15px;
            border: 1px solid #eaeaea;
        }
    </style>
</head>
<body>
    <h1>File Browser</h1>

    <div class="header-info">
        <div><strong>Root Directory:</strong> {{ root }}</div>
        <div><strong>Current Path:</strong> /{{ subpath if subpath else '.' }}</div>
    </div>

    <div class="file-list">
        {% for name, path, is_dir in entries %}
        <div class="entry {% if is_dir %}folder{% else %}file{% endif %} {% if name == '..' %}parent-dir{% endif %}">
            <div class="name-container">
                <div class="clickable-name">
                    <a href="/{{ path }}" class="name-link">
                        <span class="{% if is_dir %}folder-name{% else %}file-name{% endif %}">
                            {{ name }}
                        </span>
                    </a>
                    <span class="file-type">
                        {% if is_dir %}
                            {% if name == '..' %} (Parent Directory) {% else %} (Folder) {% endif %}
                        {% else %} (File) {% endif %}
                    </span>
                </div>
            </div>
            <button class="open-btn" onclick="openInBrowser('{{ path }}', event)">
                Open in File Browser
            </button>
        </div>
        {% endfor %}
    </div>

    <script>
        function openInBrowser(path, event) {
            // 重要: 停止事件传播到父元素
            event.stopPropagation();
            event.preventDefault();

            // 创建一个隐藏的iframe来执行打开操作
            const iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            iframe.src = `/open?path=${encodeURIComponent(path)}`;
            document.body.appendChild(iframe);

            // 稍后移除iframe
            setTimeout(() => {
                iframe.remove();
            }, 1000);
        }
    </script>
</body>
</html>
    """, entries=entries, subpath=subpath, root=ROOT_DIR)

@app.route('/open')
def open_path():
    """Handle requests to open in file browser"""
    path = request.args.get('path', '')
    if not path:
        return "Missing path parameter", 400

    target_path = os.path.join(ROOT_DIR, path)
    if not os.path.exists(target_path):
        return "Path not found", 404

    # Check path is within root directory
    if not os.path.commonpath([ROOT_DIR, os.path.abspath(target_path)]).startswith(ROOT_DIR):
        return "Access denied: Path is outside root directory", 403

    # Open in background thread to avoid blocking
    threading.Thread(target=open_in_file_browser, args=(target_path,)).start()

    # 返回简单响应 (200 OK)
    return "Opening in file browser...", 200

def open_browser():
    """Open default browser after server starts"""
    import time
    time.sleep(1)
    import webbrowser
    webbrowser.open(f'http://localhost:{PORT}')

if __name__ == '__main__':
    print(f"Serving files from: {ROOT_DIR}")
    print(f"Access at: http://localhost:{PORT}")
    print("Folder sorting: Directories first, then files (including parent directory)")
    print("Enhanced: Larger clickable area for entries")
    print("Fixed: Open button navigation bug with iFrame solution")
    print("Improved: Folder and file color differentiation with dedicated styling")
    print(f"Port: {PORT}")
    print(f"Auto-open browser: {'disabled' if args.no_browser else 'enabled'}")
    print("Press Ctrl+C to stop the server")

    # Open browser automatically unless --no-browser is specified
    if not args.no_browser:
        threading.Thread(target=open_browser).start()

    # Start Flask server
    app.run(host='127.0.0.1', port=PORT, debug=False)
