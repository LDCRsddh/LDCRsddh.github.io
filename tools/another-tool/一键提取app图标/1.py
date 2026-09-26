import os
import sys
import win32com.client
import win32gui
import win32ui
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import ctypes
import traceback

class IconExtractor:
    def __init__(self, root):
        self.root = root
        self.root.title("应用程序图标提取工具")
        self.root.geometry("600x450")
        self.root.resizable(True, True)
        
        # 创建主题样式
        self.style = ttk.Style()
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", font=("Arial", 10))
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("Title.TLabel", background="#4b6eaf", 
                            foreground="white", font=("Arial", 14, "bold"))
        
        # 创建UI
        self.create_widgets()
        
        # 存储图标数据
        self.icon_data = None
        self.target_path = ""
        
    def create_widgets(self):
        # 标题栏
        title_frame = ttk.Frame(self.root, style="TFrame")
        title_frame.pack(fill=tk.X, padx=10, pady=10)
        
        title_label = ttk.Label(title_frame, text="应用程序图标提取工具", style="Title.TLabel")
        title_label.pack(fill=tk.X, ipady=10)
        
        # 说明文本
        desc_frame = ttk.Frame(self.root, style="TFrame")
        desc_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        desc_text = "本工具可以提取Windows应用程序(.exe)或快捷方式(.lnk)的图标。\n" \
                    "选择文件后，预览将显示在下方，点击'保存图标'按钮可将图标保存为PNG文件。"
        desc_label = ttk.Label(desc_frame, text=desc_text, style="TLabel", justify=tk.LEFT)
        desc_label.pack(fill=tk.X, pady=5)
        
        # 选择文件区域
        file_frame = ttk.Frame(self.root, style="TFrame")
        file_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(file_frame, text="选择应用程序或快捷方式:", style="TLabel").grid(row=0, column=0, sticky=tk.W)
        
        self.file_path = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path, width=50)
        file_entry.grid(row=1, column=0, padx=(0, 5), sticky=tk.EW)
        
        browse_btn = ttk.Button(file_frame, text="浏览...", command=self.browse_file)
        browse_btn.grid(row=1, column=1)
        
        # 预览区域
        preview_frame = ttk.LabelFrame(self.root, text="图标预览", style="TFrame")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.preview_label = ttk.Label(preview_frame, text="图标预览区域", 
                                      background="white", anchor=tk.CENTER)
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 按钮区域
        button_frame = ttk.Frame(self.root, style="TFrame")
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        extract_btn = ttk.Button(button_frame, text="提取图标", command=self.extract_icon)
        extract_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        save_btn = ttk.Button(button_frame, text="保存图标", command=self.save_icon)
        save_btn.pack(side=tk.LEFT)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W, style="TLabel")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 配置网格权重
        file_frame.columnconfigure(0, weight=1)
    
    def browse_file(self):
        file_types = [
            ("应用程序/快捷方式", "*.exe;*.lnk"),
            ("可执行文件", "*.exe"),
            ("快捷方式", "*.lnk"),
            ("所有文件", "*.*")
        ]
        
        file_path = filedialog.askopenfilename(
            title="选择应用程序或快捷方式",
            filetypes=file_types
        )
        
        if file_path:
            self.file_path.set(file_path)
            self.status_var.set(f"已选择文件: {os.path.basename(file_path)}")
    
    def resolve_shortcut(self, shortcut_path):
        """解析快捷方式文件，返回目标路径"""
        try:
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            return shortcut.Targetpath
        except Exception as e:
            self.status_var.set(f"错误: 无法解析快捷方式 - {str(e)}")
            return None
    
    def extract_icon(self):
        file_path = self.file_path.get()
        if not file_path:
            self.status_var.set("错误: 请先选择一个文件")
            return
        
        if not os.path.exists(file_path):
            self.status_var.set("错误: 文件不存在")
            return
        
        # 处理快捷方式
        if file_path.lower().endswith('.lnk'):
            self.target_path = self.resolve_shortcut(file_path)
            if not self.target_path:
                return
            if not os.path.exists(self.target_path):
                self.status_var.set(f"错误: 快捷方式目标不存在 - {self.target_path}")
                return
        else:
            self.target_path = file_path
        
        # 提取图标
        try:
            # 获取图标数量
            icon_count = win32gui.ExtractIconEx(self.target_path, -1, 0)
            if icon_count == 0:
                self.status_var.set("错误: 未找到图标资源")
                return
            
            # 提取第一个图标
            large_icons, small_icons = win32gui.ExtractIconEx(self.target_path, 0, 1)
            
            # 使用大图标（索引0）
            if large_icons and large_icons[0]:
                hicon = large_icons[0]
            elif small_icons and small_icons[0]:
                hicon = small_icons[0]
            else:
                self.status_var.set("错误: 无法获取图标句柄")
                return
            
            # 获取图标信息
            icon_info = win32gui.GetIconInfo(hicon)
            
            # 修复：正确获取图标尺寸
            # 优先使用颜色位图获取尺寸，否则使用掩码位图
            if icon_info[0]:  # hbmColor
                bmp = win32ui.CreateBitmapFromHandle(icon_info[0])
            else:  # hbmMask
                bmp = win32ui.CreateBitmapFromHandle(icon_info[1])
                
            bmp_info = bmp.GetInfo()
            width = bmp_info['bmWidth']
            height = bmp_info['bmHeight']
            
            # 清理GetIconInfo创建的位图
            if icon_info[0]:
                win32gui.DeleteObject(icon_info[0])
            if icon_info[1]:
                win32gui.DeleteObject(icon_info[1])
            
            # 创建位图
            hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, width, height)
            mem_dc = hdc.CreateCompatibleDC()
            old_bmp = mem_dc.SelectObject(hbmp)
            mem_dc.DrawIcon((0, 0), hicon)
            mem_dc.SelectObject(old_bmp)  # 恢复原始位图
            
            # 转换为PIL图像
            bmpinfo = hbmp.GetInfo()
            bmpstr = hbmp.GetBitmapBits(True)
            image = Image.frombuffer(
                'RGBA',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRA', 0, 1
            )
            
            # 清理资源
            win32gui.DestroyIcon(hicon)
            for icon in large_icons:
                if icon:
                    win32gui.DestroyIcon(icon)
            for icon in small_icons:
                if icon:
                    win32gui.DestroyIcon(icon)
            
            # 存储图标数据
            self.icon_data = image
            self.update_preview(image)
            self.status_var.set(f"成功提取图标: {os.path.basename(self.target_path)}")
            
        except Exception as e:
            self.status_var.set(f"错误: {str(e)}")
            traceback.print_exc()  # 打印完整错误信息到日志
    
    def update_preview(self, image):
        # 调整预览大小
        preview_size = (256, 256)
        preview = image.copy()
        preview.thumbnail(preview_size, Image.LANCZOS)
        
        # 转换为PhotoImage
        try:
            self.preview_image = ImageTk.PhotoImage(preview)
        except Exception:
            # 如果出现图像模式问题，转换为RGBA
            if preview.mode != 'RGBA':
                preview = preview.convert('RGBA')
            self.preview_image = ImageTk.PhotoImage(preview)
        
        # 更新标签
        self.preview_label.configure(image=self.preview_image)
        self.preview_label.image = self.preview_image
    
    def save_icon(self):
        if not self.icon_data:
            self.status_var.set("错误: 没有可保存的图标数据")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="保存图标",
            defaultextension=".png",
            filetypes=[("PNG 图像", "*.png"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # 确保使用PNG格式保存
            self.icon_data.save(file_path, "PNG")
            self.status_var.set(f"图标已保存到: {file_path}")
            messagebox.showinfo("保存成功", f"图标已成功保存到:\n{file_path}")
        except Exception as e:
            self.status_var.set(f"保存失败: {str(e)}")
            messagebox.showerror("保存错误", f"无法保存图标:\n{str(e)}")

def hide_console():
    """隐藏控制台窗口（仅Windows有效）"""
    if sys.platform == "win32":
        kernel32 = ctypes.WinDLL('kernel32')
        user32 = ctypes.WinDLL('user32')
        SW_HIDE = 0
        
        # 获取控制台窗口句柄
        console_window = kernel32.GetConsoleWindow()
        
        # 隐藏控制台窗口
        if console_window:
            user32.ShowWindow(console_window, SW_HIDE)

def main():
    # 检查依赖库
    try:
        import win32com
        import win32gui
        import win32ui
        from PIL import Image, ImageTk
    except ImportError:
        # 尝试安装缺失的库
        import subprocess
        import sys
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "pywin32"], 
                                 creationflags=subprocess.CREATE_NO_WINDOW)
            # 重新启动程序
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            print(f"安装依赖失败: {str(e)}")
            messagebox.showerror("错误", f"无法安装依赖库:\n{str(e)}\n请手动安装: pip install pillow pywin32")
            return
    
    # 隐藏控制台窗口
    hide_console()
    
    # 创建主窗口
    root = tk.Tk()
    app = IconExtractor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
