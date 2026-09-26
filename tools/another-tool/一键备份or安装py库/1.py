import os
import platform
import datetime
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

def backup_libraries():
    backup_dir = os.path.join(os.getcwd(), 'all')
    os.makedirs(backup_dir, exist_ok=True)
    
    computer_name = platform.node().replace(' ', '_')
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{computer_name}_{timestamp}.txt"
    filepath = os.path.join(backup_dir, filename)
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'freeze'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # 提取库名（移除版本信息）
        libraries = [line.split('==')[0] for line in result.stdout.splitlines()]
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(libraries))
        
        messagebox.showinfo("备份成功", f"已备份 {len(libraries)} 个库\n保存至: {filepath}")
    except Exception as e:
        messagebox.showerror("备份失败", f"错误: {str(e)}")

def install_libraries(file_path):
    try:
        with open(file_path, 'r') as f:
            libraries = [line.strip() for line in f.readlines()]
        
        if not libraries:
            messagebox.showwarning("安装失败", "选中的文件为空！")
            return
        
        output = []
        for lib in libraries:
            if lib:  # 跳过空行
                try:
                    result = subprocess.run(
                        [sys.executable, '-m', 'pip', 'install', lib, '--upgrade'],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    output.append(f"✓ {lib}: 安装成功")
                except subprocess.CalledProcessError as e:
                    output.append(f"✕ {lib}: 安装失败 - {e.stderr.strip()}")
        
        result_text = "安装完成:\n" + "\n".join(output)
        messagebox.showinfo("安装结果", result_text)
    except Exception as e:
        messagebox.showerror("安装错误", f"错误: {str(e)}")

def select_backup_file():
    backup_dir = os.path.join(os.getcwd(), 'all')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # 修复文件对话框调用
    file_path = filedialog.askopenfilename(
        initialdir=backup_dir,
        title="选择备份文件",
        filetypes=(("文本文件", "*.txt"), ("所有文件", "*.*")))
    
    if file_path:  # 检查用户是否选择了文件
        install_libraries(file_path)

def create_gui():
    root = tk.Tk()
    root.title("Python库管理器")
    root.geometry("400x300")
    
    # 设置样式
    style = ttk.Style()
    style.configure('TButton', font=('Arial', 12), padding=10)
    
    # 创建主框架
    main_frame = ttk.Frame(root, padding=20)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # 标题
    title_label = ttk.Label(main_frame, text="Python库管理工具", font=('Arial', 16))
    title_label.pack(pady=10)
    
    # 按钮区域
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(pady=20)
    
    # 备份按钮
    backup_btn = ttk.Button(
        button_frame, 
        text="备份库", 
        command=backup_libraries,
        width=15
    )
    backup_btn.pack(pady=10)
    
    # 安装按钮
    install_btn = ttk.Button(
        button_frame, 
        text="安装库", 
        command=select_backup_file,
        width=15
    )
    install_btn.pack(pady=10)
    
    # 状态栏
    status_var = tk.StringVar(value="就绪")
    status_bar = ttk.Label(root, textvariable=status_var, relief=tk.SUNKEN, anchor=tk.W)
    status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    root.mainloop()

if __name__ == "__main__":
    create_gui()
