import os
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
from datetime import datetime
import threading
import queue
import time
import difflib
import binascii

def calculate_file_hash(filepath):
    """计算文件的SHA1哈希值（比MD5更快）"""
    hash_sha1 = hashlib.sha1()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):  # 使用更大的块大小
                hash_sha1.update(chunk)
        return hash_sha1.hexdigest()
    except Exception as e:
        print(f"无法读取文件 {filepath}: {str(e)}")
        return None

def file_worker():
    """工作线程：计算文件哈希"""
    while True:
        filepath = hash_queue.get()
        if filepath is None:  # 终止信号
            break
            
        file_size = os.path.getsize(filepath)
        file_hash = calculate_file_hash(filepath)
        result_queue.put((filepath, file_size, file_hash))
        hash_queue.task_done()

def find_duplicate_files(folder_path, progress_callback=None):
    """查找文件夹中的重复文件（优化版本）"""
    # 第一阶段：按文件大小分组
    size_groups = {}
    total_files = 0
    potential_duplicates = 0
    
    # 使用更高效的os.scandir
    for root, dirs, files in os.walk(folder_path):
        for entry in os.scandir(root):
            if entry.is_file():
                total_files += 1
                file_size = entry.stat().st_size
                
                if file_size == 0:  # 跳过空文件
                    continue
                    
                if file_size not in size_groups:
                    size_groups[file_size] = []
                size_groups[file_size].append(entry.path)
    
    # 第二阶段：在相同大小的文件中查找哈希重复
    duplicates = {}
    processed_files = 0
    
    # 启动工作线程
    num_workers = min(8, os.cpu_count() * 2)  # 根据CPU核心数确定线程数
    threads = []
    for _ in range(num_workers):
        t = threading.Thread(target=file_worker)
        t.daemon = True
        t.start()
        threads.append(t)
    
    # 只处理可能有重复的大小组
    for size, filepaths in size_groups.items():
        if len(filepaths) > 1:  # 只有多个文件才可能重复
            potential_duplicates += len(filepaths)
            for filepath in filepaths:
                hash_queue.put(filepath)
    
    # 添加终止信号
    for _ in range(num_workers):
        hash_queue.put(None)
    
    # 等待所有任务完成并收集结果
    hash_groups = {}
    while processed_files < potential_duplicates:
        try:
            filepath, file_size, file_hash = result_queue.get(timeout=0.1)
            processed_files += 1
            
            if progress_callback:
                progress = int(processed_files / potential_duplicates * 100)
                progress_callback(progress, f"处理中: {processed_files}/{potential_duplicates} 文件")
            
            if file_hash:
                if file_hash not in hash_groups:
                    hash_groups[file_hash] = []
                hash_groups[file_hash].append(filepath)
        except queue.Empty:
            continue
    
    # 等待所有工作线程完成
    for t in threads:
        t.join()
    
    # 第三阶段：识别真正的重复文件
    for file_hash, filepaths in hash_groups.items():
        if len(filepaths) > 1:
            # 按修改时间排序（最早的排在最前）
            filepaths.sort(key=lambda x: os.path.getmtime(x))
            duplicates[file_hash] = {
                "keep": filepaths[0],  # 保留最早的文件
                "delete": filepaths[1:]  # 删除其余副本
            }
    
    return duplicates, total_files

class FileViewerDialog(tk.Toplevel):
    """文件查看器对话框"""
    def __init__(self, parent, filepath1, filepath2):
        super().__init__(parent)
        self.title("文件对比查看器")
        self.geometry("1000x600")
        self.resizable(True, True)
        
        # 设置网格布局
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # 创建标题
        title1 = tk.Label(self, text=f"文件1: {os.path.basename(filepath1)}", font=("Arial", 10, "bold"))
        title1.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        title2 = tk.Label(self, text=f"文件2: {os.path.basename(filepath2)}", font=("Arial", 10, "bold"))
        title2.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        # 文件信息
        info_frame1 = tk.Frame(self)
        info_frame1.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.display_file_info(info_frame1, filepath1)
        
        info_frame2 = tk.Frame(self)
        info_frame2.grid(row=1, column=1, sticky="nsew", padx=10, pady=5)
        self.display_file_info(info_frame2, filepath2)
        
        # 差异对比按钮
        compare_btn = tk.Button(
            self, 
            text="对比差异", 
            command=lambda: self.compare_files(filepath1, filepath2),
            bg="#4CAF50",
            fg="white",
            padx=10,
            pady=5
        )
        compare_btn.grid(row=2, column=0, columnspan=2, pady=10)
        
        # 关闭按钮
        close_btn = tk.Button(
            self, 
            text="关闭", 
            command=self.destroy,
            padx=10,
            pady=5
        )
        close_btn.grid(row=3, column=0, columnspan=2, pady=5)
    
    def display_file_info(self, parent, filepath):
        """显示文件信息和内容预览"""
        # 文件基本信息
        file_size = os.path.getsize(filepath)
        mod_time = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M:%S")
        
        info_text = (
            f"路径: {filepath}\n"
            f"大小: {self.format_size(file_size)}\n"
            f"修改时间: {mod_time}"
        )
        
        info_label = tk.Label(parent, text=info_text, justify="left", anchor="w")
        info_label.pack(fill="x", pady=5)
        
        # 分隔线
        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=5)
        
        # 文件内容预览
        preview_label = tk.Label(parent, text="内容预览:", anchor="w")
        preview_label.pack(fill="x", pady=5)
        
        # 创建带滚动条的文本区域
        scroll_frame = tk.Frame(parent)
        scroll_frame.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(scroll_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.text_area = scrolledtext.ScrolledText(
            scroll_frame, 
            wrap="word", 
            yscrollcommand=scrollbar.set,
            height=15
        )
        self.text_area.pack(fill="both", expand=True)
        scrollbar.config(command=self.text_area.yview)
        
        # 加载文件内容
        self.load_file_content(filepath)
    
    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"
    
    def load_file_content(self, filepath):
        """加载文件内容到文本区域"""
        max_size = 1024 * 1024  # 最大预览1MB
        
        try:
            file_size = os.path.getsize(filepath)
            if file_size > max_size:
                self.text_area.insert("end", f"文件过大 ({self.format_size(file_size)})，仅显示前1MB内容\n\n")
            
            with open(filepath, "rb") as f:
                content = f.read(min(file_size, max_size))
                
                # 尝试解码为文本
                try:
                    text_content = content.decode("utf-8", errors="replace")
                    self.text_area.insert("end", text_content)
                except UnicodeDecodeError:
                    # 如果是二进制文件，显示十六进制预览
                    self.text_area.insert("end", "二进制文件内容（十六进制预览）:\n\n")
                    hex_content = binascii.hexlify(content).decode("utf-8")
                    # 格式化十六进制显示
                    formatted_hex = ""
                    for i in range(0, len(hex_content), 32):
                        formatted_hex += hex_content[i:i+32] + " "
                        if (i // 32) % 4 == 3:  # 每4行换行
                            formatted_hex += "\n"
                    self.text_area.insert("end", formatted_hex)
            
            self.text_area.config(state="disabled")
        except Exception as e:
            self.text_area.insert("end", f"无法读取文件: {str(e)}")
            self.text_area.config(state="disabled")
    
    def compare_files(self, filepath1, filepath2):
        """对比两个文件的差异"""
        try:
            # 读取文件内容
            with open(filepath1, "r", encoding="utf-8", errors="replace") as f1:
                lines1 = f1.readlines()
            
            with open(filepath2, "r", encoding="utf-8", errors="replace") as f2:
                lines2 = f2.readlines()
            
            # 计算差异
            d = difflib.Differ()
            diff = list(d.compare(lines1, lines2))
            
            # 创建差异查看窗口
            diff_window = tk.Toplevel(self)
            diff_window.title("文件差异对比")
            diff_window.geometry("800x600")
            
            # 添加标题
            title = tk.Label(diff_window, text="文件差异对比", font=("Arial", 12, "bold"))
            title.pack(pady=10)
            
            # 添加滚动文本框
            scroll_frame = tk.Frame(diff_window)
            scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)
            
            scrollbar = tk.Scrollbar(scroll_frame)
            scrollbar.pack(side="right", fill="y")
            
            diff_text = tk.Text(
                scroll_frame, 
                wrap="word", 
                yscrollcommand=scrollbar.set,
                font=("Courier New", 10)
            )
            diff_text.pack(fill="both", expand=True)
            scrollbar.config(command=diff_text.yview)
            
            # 添加差异内容（带颜色）
            for line in diff:
                if line.startswith('+ '):
                    diff_text.insert("end", line[2:], "added")
                elif line.startswith('- '):
                    diff_text.insert("end", line[2:], "removed")
                elif line.startswith('? '):
                    diff_text.insert("end", line[2:], "changed")
                else:
                    diff_text.insert("end", line[2:])
            
            # 配置标签样式
            diff_text.tag_config("added", background="#ccffcc")
            diff_text.tag_config("removed", background="#ffcccc")
            diff_text.tag_config("changed", background="#ffffcc")
            
            diff_text.config(state="disabled")
            
            # 添加关闭按钮
            close_btn = tk.Button(
                diff_window, 
                text="关闭", 
                command=diff_window.destroy,
                padx=10,
                pady=5
            )
            close_btn.pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("对比错误", f"无法对比文件:\n{str(e)}")

class DuplicateCleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("高效重复文件清理工具")
        self.root.geometry("600x350")
        self.root.resizable(True, True)
        
        # 创建界面元素
        self.create_widgets()
        
        # 当前扫描状态
        self.scanning = False
        self.stop_requested = False
    
    def create_widgets(self):
        # 标题
        header = tk.Label(
            self.root,
            text="高效重复文件清理工具",
            font=("Arial", 16, "bold"),
            pady=15
        )
        header.pack()
        
        # 描述
        description = tk.Label(
            self.root,
            text="此程序将扫描选定文件夹中的重复文件\n"
                 "保留修改时间最早的文件，删除其他重复文件",
            pady=10
        )
        description.pack()
        
        # 文件夹选择部分
        folder_frame = tk.Frame(self.root)
        folder_frame.pack(pady=10, fill="x", padx=20)
        
        tk.Label(folder_frame, text="目标文件夹:").pack(side="left")
        
        self.folder_path = tk.StringVar()
        folder_entry = tk.Entry(folder_frame, textvariable=self.folder_path, width=50)
        folder_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        browse_btn = tk.Button(folder_frame, text="浏览...", command=self.select_folder)
        browse_btn.pack(side="right")
        
        # 进度条
        self.progress_frame = tk.Frame(self.root)
        self.progress_frame.pack(fill="x", padx=20, pady=10)
        
        self.progress_label = tk.Label(self.progress_frame, text="就绪")
        self.progress_label.pack(anchor="w")
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, 
            variable=self.progress_var, 
            maximum=100,
            mode="determinate"
        )
        self.progress_bar.pack(fill="x", pady=5)
        
        # 统计信息
        self.stats_frame = tk.Frame(self.root)
        self.stats_frame.pack(fill="x", padx=20, pady=5)
        
        self.stats_label = tk.Label(self.stats_frame, text="")
        self.stats_label.pack(anchor="w")
        
        # 按钮区域
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=15)
        
        self.scan_btn = tk.Button(
            btn_frame,
            text="扫描重复文件",
            command=self.start_scan,
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=5
        )
        self.scan_btn.pack(side="left", padx=10)
        
        self.stop_btn = tk.Button(
            btn_frame,
            text="停止扫描",
            command=self.stop_scan,
            state="disabled",
            padx=20,
            pady=5
        )
        self.stop_btn.pack(side="left", padx=10)
    
    def select_folder(self):
        path = filedialog.askdirectory(title="选择要扫描的文件夹")
        if path:
            self.folder_path.set(path)
    
    def update_progress(self, progress, message):
        self.progress_var.set(progress)
        self.progress_label.config(text=message)
        self.root.update_idletasks()
    
    def start_scan(self):
        folder_path = self.folder_path.get()
        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showerror("错误", "请选择有效的文件夹路径")
            return
        
        # 重置状态
        self.scanning = True
        self.stop_requested = False
        self.scan_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.update_progress(0, "准备扫描...")
        
        # 在后台线程中运行扫描
        self.duplicates = {}
        self.total_files = 0
        
        scan_thread = threading.Thread(
            target=self.run_scan, 
            args=(folder_path,),
            daemon=True
        )
        scan_thread.start()
    
    def stop_scan(self):
        self.stop_requested = True
        self.stop_btn.config(state="disabled")
        self.update_progress(0, "正在停止...")
    
    def run_scan(self, folder_path):
        try:
            start_time = time.time()
            
            # 查找重复文件
            self.duplicates, self.total_files = find_duplicate_files(
                folder_path,
                progress_callback=self.update_progress
            )
            
            if self.stop_requested:
                self.update_progress(0, "扫描已取消")
                messagebox.showinfo("已取消", "扫描操作已被用户取消")
                return
            
            scan_time = time.time() - start_time
            
            if not self.duplicates:
                message = (
                    f"扫描完成！耗时 {scan_time:.1f} 秒\n"
                    f"在 {folder_path} 中未找到重复文件\n"
                    f"共扫描 {self.total_files} 个文件"
                )
                self.update_progress(100, "扫描完成")
                messagebox.showinfo("无重复文件", message)
                return
            
            # 准备统计信息
            delete_count = sum(len(files["delete"]) for files in self.duplicates.values())
            duplicate_groups = len(self.duplicates)
            total_duplicates = sum(len(files["delete"]) + 1 for files in self.duplicates.values())
            
            stats_msg = (
                f"扫描完成！耗时 {scan_time:.1f} 秒\n"
                f"共扫描文件: {self.total_files} 个\n"
                f"发现重复组: {duplicate_groups} 组\n"
                f"重复文件总数: {total_duplicates} 个\n"
                f"可删除文件: {delete_count} 个"
            )
            
            self.stats_label.config(text=stats_msg)
            self.update_progress(100, "扫描完成 - 准备删除确认")
            
            # 显示确认对话框
            self.show_confirmation()
            
        except Exception as e:
            self.update_progress(0, f"错误: {str(e)}")
            messagebox.showerror("扫描错误", f"扫描过程中发生错误:\n{str(e)}")
        finally:
            self.scanning = False
            self.scan_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
    
    def show_confirmation(self):
        # 准备删除列表
        delete_list = []
        for files in self.duplicates.values():
            delete_list.extend(files["delete"])
        
        delete_count = len(delete_list)
        
        # 创建确认对话框
        confirm_dialog = tk.Toplevel(self.root)
        confirm_dialog.title("确认删除重复文件")
        confirm_dialog.geometry("900x600")
        confirm_dialog.transient(self.root)
        confirm_dialog.grab_set()
        
        # 对话框内容
        content_frame = tk.Frame(confirm_dialog, padx=10, pady=10)
        content_frame.pack(fill="both", expand=True)
        
        # 统计信息
        stats_frame = tk.Frame(content_frame)
        stats_frame.pack(fill="x", pady=5)
        
        stats_text = (
            f"发现 {len(self.duplicates)} 组重复文件\n"
            f"即将删除 {delete_count} 个重复文件\n"
            f"保留每组中最早修改的文件"
        )
        tk.Label(stats_frame, text=stats_text, justify="left").pack(anchor="w")
        
        # 文件组列表
        group_frame = tk.LabelFrame(content_frame, text="重复文件组列表")
        group_frame.pack(fill="both", expand=True, pady=10)
        
        # 创建Treeview显示重复组
        tree_columns = ("哈希值", "保留文件", "删除文件数")
        tree = ttk.Treeview(
            group_frame, 
            columns=tree_columns,
            show="headings",
            selectmode="browse"
        )
        
        # 定义列
        tree.heading("哈希值", text="哈希值 (前8位)")
        tree.heading("保留文件", text="保留文件")
        tree.heading("删除文件数", text="删除文件数")
        
        tree.column("哈希值", width=100, anchor="center")
        tree.column("保留文件", width=400, anchor="w")
        tree.column("删除文件数", width=100, anchor="center")
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(group_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True, side="left")
        
        # 添加数据
        for file_hash, files in self.duplicates.items():
            keep_file = files["keep"]
            delete_count = len(files["delete"])
            tree.insert("", "end", values=(
                file_hash[:8], 
                os.path.basename(keep_file), 
                delete_count
            ))
        
        # 文件详情区域
        detail_frame = tk.LabelFrame(content_frame, text="文件详情")
        detail_frame.pack(fill="x", pady=5)
        
        # 详情文本区域
        self.detail_text = scrolledtext.ScrolledText(
            detail_frame, 
            wrap="word",
            height=8
        )
        self.detail_text.pack(fill="x", padx=5, pady=5)
        self.detail_text.config(state="disabled")
        
        # 对比按钮
        compare_frame = tk.Frame(content_frame)
        compare_frame.pack(fill="x", pady=5)
        
        compare_btn = tk.Button(
            compare_frame, 
            text="对比选中组的文件", 
            command=lambda: self.compare_selected_group(tree),
            bg="#2196F3",
            fg="white",
            padx=10,
            pady=5
        )
        compare_btn.pack(side="left", padx=5)
        
        # 操作按钮
        btn_frame = tk.Frame(content_frame)
        btn_frame.pack(fill="x", pady=10)
        
        def perform_deletion():
            """执行删除操作"""
            success_count = 0
            error_count = 0
            
            for files in self.duplicates.values():
                for file_to_delete in files["delete"]:
                    try:
                        os.remove(file_to_delete)
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"删除失败 {file_to_delete}: {str(e)}")
            
            # 显示结果
            result_msg = (
                f"删除完成！\n"
                f"成功删除: {success_count} 个文件\n"
                f"删除失败: {error_count} 个文件"
            )
            messagebox.showinfo("操作完成", result_msg)
            confirm_dialog.destroy()
            
            # 重置界面
            self.update_progress(0, "就绪")
            self.stats_label.config(text="")
        
        # 添加按钮
        delete_btn = tk.Button(
            btn_frame, 
            text="确认删除", 
            command=perform_deletion, 
            bg="#ff4444", 
            fg="white",
            padx=15
        )
        delete_btn.pack(side="left", padx=10)
        
        cancel_btn = tk.Button(
            btn_frame, 
            text="取消", 
            command=confirm_dialog.destroy,
            padx=15
        )
        cancel_btn.pack(side="right", padx=10)
        
        # 绑定Treeview选择事件
        def on_tree_select(event):
            selected = tree.focus()
            if not selected:
                return
                
            values = tree.item(selected, "values")
            if not values:
                return
                
            # 获取完整的哈希值
            short_hash = values[0]
            full_hash = next((h for h in self.duplicates.keys() if h.startswith(short_hash)), None)
            if not full_hash:
                return
                
            files = self.duplicates[full_hash]
            
            # 更新详情区域
            self.detail_text.config(state="normal")
            self.detail_text.delete(1.0, "end")
            
            # 添加保留文件信息
            self.detail_text.insert("end", "保留文件:\n", "header")
            self.detail_text.insert("end", f"  {files['keep']}\n\n")
            
            # 添加删除文件信息
            self.detail_text.insert("end", "删除文件:\n", "header")
            for i, file_to_delete in enumerate(files["delete"]):
                self.detail_text.insert("end", f"  {i+1}. {file_to_delete}\n")
            
            self.detail_text.tag_config("header", font=("Arial", 10, "bold"))
            self.detail_text.config(state="disabled")
        
        tree.bind("<<TreeviewSelect>>", on_tree_select)
        
        # 默认选择第一项
        if self.duplicates:
            first_item = tree.get_children()[0]
            tree.selection_set(first_item)
            tree.focus(first_item)
            on_tree_select(None)
    
    def compare_selected_group(self, tree):
        """对比选中组的所有文件"""
        selected = tree.focus()
        if not selected:
            messagebox.showwarning("未选择", "请先选择一个文件组")
            return
            
        values = tree.item(selected, "values")
        if not values:
            return
            
        # 获取完整的哈希值
        short_hash = values[0]
        full_hash = next((h for h in self.duplicates.keys() if h.startswith(short_hash)), None)
        if not full_hash:
            return
            
        files = self.duplicates[full_hash]
        all_files = [files["keep"]] + files["delete"]
        
        if len(all_files) < 2:
            messagebox.showinfo("无需对比", "该组只有一个文件，无需对比")
            return
            
        # 弹出文件选择对话框
        compare_dialog = tk.Toplevel(self.root)
        compare_dialog.title("选择要对比的文件")
        compare_dialog.geometry("400x300")
        compare_dialog.transient(self.root)
        compare_dialog.grab_set()
        
        tk.Label(compare_dialog, text="选择两个文件进行对比:", font=("Arial", 10)).pack(pady=10)
        
        # 文件列表
        list_frame = tk.Frame(compare_dialog)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        file_list = tk.Listbox(
            list_frame, 
            selectmode="extended",
            yscrollcommand=scrollbar.set,
            height=8
        )
        file_list.pack(fill="both", expand=True)
        scrollbar.config(command=file_list.yview)
        
        for i, filepath in enumerate(all_files):
            file_list.insert("end", f"{i+1}. {os.path.basename(filepath)}")
        
        # 对比按钮
        def start_compare():
            selected = file_list.curselection()
            if len(selected) != 2:
                messagebox.showwarning("选择错误", "请选择两个文件进行对比")
                return
                
            file1 = all_files[selected[0]]
            file2 = all_files[selected[1]]
            compare_dialog.destroy()
            FileViewerDialog(self.root, file1, file2)
        
        btn_frame = tk.Frame(compare_dialog)
        btn_frame.pack(pady=10)
        
        compare_btn = tk.Button(
            btn_frame, 
            text="对比文件", 
            command=start_compare,
            bg="#4CAF50",
            fg="white",
            padx=10
        )
        compare_btn.pack(side="left", padx=5)
        
        cancel_btn = tk.Button(
            btn_frame, 
            text="取消", 
            command=compare_dialog.destroy,
            padx=10
        )
        cancel_btn.pack(side="right", padx=5)

if __name__ == "__main__":
    # 初始化全局队列
    hash_queue = queue.Queue()
    result_queue = queue.Queue()
    
    root = tk.Tk()
    app = DuplicateCleanerApp(root)
    root.mainloop()
