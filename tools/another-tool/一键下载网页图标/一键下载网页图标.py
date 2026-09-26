import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from ttkbootstrap import Style
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import os
import threading
import queue
import logging
from PIL import Image, ImageTk
import time
import io
import winsound

class FaviconDownloaderApp:
    def __init__(self):
        self.style = Style(theme='flatly')
        self.root = self.style.master
        self.root.title("Favicon下载工具")
        self.root.geometry("800x600")
        
        # 初始化界面组件
        self.create_widgets()
        
        # 初始化下载队列和控制变量
        self.download_queue = queue.Queue()
        self.is_paused = False
        self.is_downloading = False
        self.threads = []
        self.total_tasks = 0
        
        # 配置日志系统
        self.setup_logging()
        
        # 创建图标保存目录
        if not os.path.exists('icons'):
            os.makedirs('icons')

    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 网址输入区域
        input_frame = ttk.LabelFrame(main_frame, text="网址列表（每行一个）")
        input_frame.pack(fill=tk.X, pady=5)

        self.url_entry = tk.Text(input_frame, height=5)
        self.url_entry.pack(fill=tk.X, padx=5, pady=5)

        # 控制按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.start_btn = ttk.Button(btn_frame, text="开始下载", command=self.start_download)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.pause_btn = ttk.Button(btn_frame, text="暂停", command=self.toggle_pause, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=5)

        self.task_counter = ttk.Label(btn_frame, text="0/0")
        self.task_counter.pack(side=tk.LEFT, padx=10)

        ttk.Button(btn_frame, text="清空", command=self.clear_input).pack(side=tk.RIGHT, padx=5)

        # 下载列表
        list_frame = ttk.LabelFrame(main_frame, text="下载进度")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        columns = ('url', 'status', 'preview', 'path')
        self.download_tree = ttk.Treeview(list_frame, columns=columns, show='headings', selectmode='browse')
        self.download_tree.heading('url', text='网址')
        self.download_tree.heading('status', text='状态')
        self.download_tree.heading('preview', text='预览')
        self.download_tree.heading('path', text='保存路径')
        self.download_tree.column('url', width=250)
        self.download_tree.column('status', width=100)
        self.download_tree.column('preview', width=80)
        self.download_tree.column('path', width=200)
        self.download_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="日志输出")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_logging(self):
        """配置日志系统"""
        self.logger = logging.getLogger("FaviconDownloader")
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # 文件日志处理器
        file_handler = logging.FileHandler('download.log', encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # 界面日志处理器
        class TextHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)
                self.text_widget.configure(state='normal')
                self.text_widget.insert(tk.END, msg + '\n')
                self.text_widget.configure(state='disabled')
                self.text_widget.see(tk.END)

        text_handler = TextHandler(self.log_text)
        text_handler.setFormatter(formatter)
        self.logger.addHandler(text_handler)

    def start_download(self):
        """启动下载任务"""
        urls = self.url_entry.get("1.0", tk.END).strip().split('\n')
        if not urls:
            messagebox.showwarning("警告", "请输入至少一个网址")
            return

        # 初始化任务状态
        self.total_tasks = len([url for url in urls if url.strip()])
        self.task_counter.config(text=f"0/{self.total_tasks}")

        # 清空之前的下载列表
        for item in self.download_tree.get_children():
            self.download_tree.delete(item)

        # 将任务加入队列
        for url in urls:
            if url.strip():
                self.download_queue.put(url.strip())
                self.download_tree.insert('', tk.END, values=(
                    url.strip(),
                    '等待中',
                    '',
                    ''
                ))

        # 启动工作线程
        self.is_downloading = True
        self.is_paused = False
        self.pause_btn.config(state=tk.NORMAL)
        self.start_btn.config(state=tk.DISABLED)

        # 创建3个工作线程
        for _ in range(3):
            thread = threading.Thread(target=self.worker, daemon=True)
            thread.start()
            self.threads.append(thread)

        # 启动状态检查
        self.root.after(100, self.check_download_status)

    def worker(self):
        """工作线程处理函数"""
        while self.is_downloading or not self.download_queue.empty():
            if self.is_paused:
                time.sleep(0.1)
                continue
            
            try:
                url = self.download_queue.get_nowait()
                self.process_url(url)
                self.download_queue.task_done()
            except queue.Empty:
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"工作线程异常: {str(e)}")

    def check_download_status(self):
        """定期检查下载状态"""
        if self.download_queue.empty():
            # 停止下载标志
            self.is_downloading = False
            
            # 等待所有线程结束
            alive_threads = sum(1 for t in self.threads if t.is_alive())
            if alive_threads == 0:
                self.start_btn.config(state=tk.NORMAL)
                self.pause_btn.config(state=tk.DISABLED)
                self.logger.info("所有任务已完成")
                winsound.MessageBeep()
                # 清空线程列表
                self.threads = []
            else:
                self.root.after(100, self.check_download_status)
        else:
            # 更新任务计数器
            completed = sum(1 for item in self.download_tree.get_children()
                          if self.download_tree.item(item, 'values')[1].startswith('完成'))
            self.task_counter.config(text=f"{completed}/{self.total_tasks}")
            self.root.after(100, self.check_download_status)

    def process_url(self, url):
        """处理单个URL"""
        self.update_status(url, '下载中')
        self.logger.info(f"开始处理: {url}")

        try:
            # 获取favicon地址
            favicon_url = self.get_favicon_url(url)
            if not favicon_url:
                raise Exception("找不到favicon地址")

            # 下载文件
            response = requests.get(favicon_url, timeout=10, stream=True)
            response.raise_for_status()

            # 生成保存路径
            domain = urlparse(url).netloc.split(':')[0]
            filename = f"icons/{domain}.ico"
            
            # 保存文件
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)

            # 更新界面
            self.update_status(url, '完成', filename)
            self.show_preview(url, filename)
            self.logger.info(f"成功下载: {url}")

        except Exception as e:
            self.update_status(url, f'失败: {str(e)}')
            self.logger.error(f"下载失败: {url} - {str(e)}")

    def get_favicon_url(self, url):
        """获取favicon实际地址"""
        try:
            # 尝试解析HTML中的link标签
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            icon_link = soup.find('link', rel=lambda x: x and 'icon' in x.lower())
            if icon_link and icon_link.get('href'):
                return urljoin(url, icon_link['href'])
        except:
            pass

        # 尝试默认的/favicon.ico
        parsed = urlparse(url)
        default_url = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
        try:
            response = requests.head(default_url, timeout=5)
            if response.status_code == 200:
                return default_url
        except:
            pass

        return None

    def update_status(self, url, status, path=''):
        """更新下载状态"""
        for item in self.download_tree.get_children():
            values = self.download_tree.item(item, 'values')
            if values[0] == url:
                self.download_tree.item(item, values=(values[0], status, values[2], path))
                break

    def show_preview(self, url, filename):
        """显示缩略图预览"""
        try:
            img = Image.open(filename)
            img.thumbnail((32, 32))
            photo = ImageTk.PhotoImage(img)

            for item in self.download_tree.get_children():
                values = self.download_tree.item(item, 'values')
                if values[0] == url:
                    # 使用自定义图像显示（需要保持图像引用）
                    self.download_tree.image = photo  # 保持引用
                    self.download_tree.item(item, values=(values[0], values[1], "", values[3]))
                    break
        except Exception as e:
            self.logger.error(f"生成预览失败: {str(e)}")

    def toggle_pause(self):
        """暂停/继续下载"""
        self.is_paused = not self.is_paused
        self.pause_btn.config(text="继续" if self.is_paused else "暂停")
        self.logger.info("下载已暂停" if self.is_paused else "下载已恢复")

    def clear_input(self):
        """清空输入和列表"""
        self.url_entry.delete("1.0", tk.END)
        for item in self.download_tree.get_children():
            self.download_tree.delete(item)
        self.log_text.configure(state='normal')
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state='disabled')
        self.task_counter.config(text="0/0")

    def on_closing(self):
        """关闭窗口时的处理"""
        self.is_downloading = False
        self.root.destroy()

if __name__ == "__main__":
    app = FaviconDownloaderApp()
    app.root.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.root.mainloop()
