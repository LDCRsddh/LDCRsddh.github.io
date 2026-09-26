import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import winreg
import os
import json
from datetime import datetime
import ctypes
import sys

class RightClickManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows 右键菜单管理器")
        self.root.geometry("900x600")
        self.root.resizable(True, True)
        
        # 检查管理员权限
        if not self.is_admin():
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit()
        
        # 应用主题
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # 配置颜色
        self.bg_color = "#2c3e50"
        self.header_color = "#3498db"
        self.accent_color = "#e74c3c"
        self.success_color = "#2ecc71"
        self.text_color = "#ecf0f1"
        self.list_bg = "#34495e"
        
        self.root.configure(bg=self.bg_color)
        
        # 创建标题
        title_frame = tk.Frame(root, bg=self.bg_color)
        title_frame.pack(fill="x", padx=20, pady=15)
        
        title_label = tk.Label(
            title_frame, 
            text="Windows 右键菜单管理器", 
            font=("Segoe UI", 20, "bold"), 
            fg=self.text_color,
            bg=self.bg_color
        )
        title_label.pack(side="left")
        
        # 创建主内容框架
        main_frame = tk.Frame(root, bg=self.bg_color)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 左侧菜单类型选择
        menu_type_frame = tk.LabelFrame(
            main_frame, 
            text="菜单类型", 
            font=("Segoe UI", 10, "bold"),
            fg=self.text_color,
            bg=self.bg_color,
            relief="flat"
        )
        menu_type_frame.pack(side="left", fill="y", padx=(0, 10))
        
        self.menu_types = {
            "文件右键菜单": winreg.HKEY_CLASSES_ROOT,
            "文件夹右键菜单": winreg.HKEY_CLASSES_ROOT,
            "桌面背景右键菜单": winreg.HKEY_CLASSES_ROOT,
            "驱动器右键菜单": winreg.HKEY_CLASSES_ROOT
        }
        
        self.menu_paths = {
            "文件右键菜单": r"*\shell",
            "文件夹右键菜单": r"Directory\shell",
            "桌面背景右键菜单": r"Directory\Background\shell",
            "驱动器右键菜单": r"Drive\shell"
        }
        
        self.selected_menu_type = tk.StringVar(value="文件右键菜单")
        
        for i, menu_type in enumerate(self.menu_types.keys()):
            rb = ttk.Radiobutton(
                menu_type_frame, 
                text=menu_type, 
                variable=self.selected_menu_type, 
                value=menu_type,
                command=self.load_menu_items,
                style="Toolbutton"
            )
            rb.pack(anchor="w", padx=10, pady=5, fill="x")
        
        # 中间菜单项列表
        list_frame = tk.LabelFrame(
            main_frame, 
            text="菜单项列表", 
            font=("Segoe UI", 10, "bold"),
            fg=self.text_color,
            bg=self.bg_color,
            relief="flat"
        )
        list_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        # 创建Treeview
        columns = ("name", "command", "icon")
        self.tree = ttk.Treeview(
            list_frame, 
            columns=columns, 
            show="headings",
            selectmode="browse"
        )
        
        # 设置列
        self.tree.heading("name", text="菜单名称", anchor="w")
        self.tree.heading("command", text="关联命令", anchor="w")
        self.tree.heading("icon", text="图标路径", anchor="w")
        
        # 设置列宽
        self.tree.column("name", width=200)
        self.tree.column("command", width=350)
        self.tree.column("icon", width=200)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 右侧操作面板
        action_frame = tk.Frame(main_frame, bg=self.bg_color)
        action_frame.pack(side="left", fill="y", padx=(10, 0))
        
        # 添加菜单项按钮
        add_btn = ttk.Button(
            action_frame, 
            text="添加菜单项", 
            command=self.add_menu_item,
            style="Accent.TButton",
            width=15
        )
        add_btn.pack(pady=5, fill="x")
        
        # 删除菜单项按钮
        remove_btn = ttk.Button(
            action_frame, 
            text="删除选中项", 
            command=self.remove_menu_item,
            style="Danger.TButton",
            width=15
        )
        remove_btn.pack(pady=5, fill="x")
        
        # 备份按钮
        backup_btn = ttk.Button(
            action_frame, 
            text="备份当前配置", 
            command=self.backup_config,
            style="Success.TButton",
            width=15
        )
        backup_btn.pack(pady=5, fill="x")
        
        # 还原按钮
        restore_btn = ttk.Button(
            action_frame, 
            text="还原备份配置", 
            command=self.restore_config,
            width=15
        )
        restore_btn.pack(pady=5, fill="x")
        
        # 重置按钮
        reset_btn = ttk.Button(
            action_frame, 
            text="重置默认设置", 
            command=self.reset_default,
            style="Warning.TButton",
            width=15
        )
        reset_btn.pack(pady=5, fill="x")
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = tk.Label(
            root, 
            textvariable=self.status_var,
            anchor="w",
            font=("Segoe UI", 9),
            fg="#95a5a6",
            bg="#1a242d",
            padx=10
        )
        status_bar.pack(side="bottom", fill="x")
        
        # 自定义样式
        self.style.configure("Treeview", 
                            background=self.list_bg, 
                            foreground=self.text_color,
                            fieldbackground=self.list_bg,
                            rowheight=25,
                            font=("Segoe UI", 9))
        
        self.style.configure("Treeview.Heading", 
                            background="#1a242d", 
                            foreground=self.text_color,
                            font=("Segoe UI", 9, "bold"))
        
        self.style.map("Treeview", background=[("selected", "#3498db")])
        
        self.style.configure("Accent.TButton", 
                            foreground="white", 
                            background=self.header_color,
                            font=("Segoe UI", 9, "bold"))
        
        self.style.configure("Danger.TButton", 
                            foreground="white", 
                            background=self.accent_color,
                            font=("Segoe UI", 9, "bold"))
        
        self.style.configure("Success.TButton", 
                            foreground="white", 
                            background=self.success_color,
                            font=("Segoe UI", 9, "bold"))
        
        self.style.configure("Warning.TButton", 
                            foreground="white", 
                            background="#f39c12",
                            font=("Segoe UI", 9, "bold"))
        
        # 加载初始数据
        self.load_menu_items()
        
        # 绑定事件
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)
    
    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def load_menu_items(self):
        self.tree.delete(*self.tree.get_children())
        menu_type = self.selected_menu_type.get()
        base_key = self.menu_types[menu_type]
        menu_path = self.menu_paths[menu_type]
        
        try:
            with winreg.OpenKey(base_key, menu_path) as key:
                index = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, index)
                        index += 1
                        
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            # 获取显示名称
                            try:
                                display_name = winreg.QueryValueEx(subkey, None)[0]
                            except:
                                display_name = subkey_name
                            
                            # 获取图标
                            icon_path = ""
                            try:
                                icon_path = winreg.QueryValueEx(subkey, "Icon")[0]
                            except:
                                pass
                            
                            # 获取命令
                            command = ""
                            try:
                                with winreg.OpenKey(subkey, "command") as cmd_key:
                                    command = winreg.QueryValueEx(cmd_key, None)[0]
                            except:
                                pass
                            
                            self.tree.insert("", "end", values=(display_name, command, icon_path))
                    except OSError:
                        break
        except FileNotFoundError:
            self.status_var.set(f"找不到 {menu_type} 的注册表项")
        except Exception as e:
            self.status_var.set(f"加载错误: {str(e)}")
    
    def on_item_select(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            self.status_var.set(f"已选择: {item['values'][0]}")
    
    def add_menu_item(self):
        add_window = tk.Toplevel(self.root)
        add_window.title("添加右键菜单项")
        add_window.geometry("500x400")
        add_window.resizable(False, False)
        add_window.transient(self.root)
        add_window.grab_set()
        
        # 设置背景色
        add_window.configure(bg=self.bg_color)
        
        # 菜单名称
        tk.Label(
            add_window, 
            text="菜单名称:", 
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.text_color
        ).grid(row=0, column=0, padx=10, pady=10, sticky="e")
        
        name_var = tk.StringVar()
        name_entry = ttk.Entry(add_window, textvariable=name_var, width=40)
        name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # 菜单命令
        tk.Label(
            add_window, 
            text="关联程序:", 
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.text_color
        ).grid(row=1, column=0, padx=10, pady=10, sticky="e")
        
        command_var = tk.StringVar()
        command_entry = ttk.Entry(add_window, textvariable=command_var, width=40)
        command_entry.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        def browse_command():
            file_path = filedialog.askopenfilename(
                title="选择程序",
                filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
            )
            if file_path:
                command_var.set(f'"{file_path}" "%1"')
        
        browse_btn = ttk.Button(
            add_window, 
            text="浏览...", 
            command=browse_command,
            width=10
        )
        browse_btn.grid(row=1, column=2, padx=5, pady=10)
        
        # 图标路径
        tk.Label(
            add_window, 
            text="图标路径 (可选):", 
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.text_color
        ).grid(row=2, column=0, padx=10, pady=10, sticky="e")
        
        icon_var = tk.StringVar()
        icon_entry = ttk.Entry(add_window, textvariable=icon_var, width=40)
        icon_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        
        def browse_icon():
            file_path = filedialog.askopenfilename(
                title="选择图标",
                filetypes=[("图标文件", "*.ico"), ("可执行文件", "*.exe"), ("所有文件", "*.*")]
            )
            if file_path:
                icon_var.set(file_path)
        
        icon_btn = ttk.Button(
            add_window, 
            text="浏览...", 
            command=browse_icon,
            width=10
        )
        icon_btn.grid(row=2, column=2, padx=5, pady=10)
        
        # 菜单类型
        tk.Label(
            add_window, 
            text="添加到:", 
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.text_color
        ).grid(row=3, column=0, padx=10, pady=10, sticky="e")
        
        menu_type_var = tk.StringVar(value=self.selected_menu_type.get())
        menu_type_dropdown = ttk.Combobox(
            add_window, 
            textvariable=menu_type_var, 
            values=list(self.menu_types.keys()),
            state="readonly",
            width=37
        )
        menu_type_dropdown.grid(row=3, column=1, padx=10, pady=10, sticky="w")
        
        # 操作按钮
        btn_frame = tk.Frame(add_window, bg=self.bg_color)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        def save_menu_item():
            name = name_var.get().strip()
            command = command_var.get().strip()
            icon = icon_var.get().strip()
            menu_type = menu_type_var.get()
            
            if not name:
                messagebox.showerror("错误", "菜单名称不能为空")
                return
            
            if not command:
                messagebox.showerror("错误", "关联程序不能为空")
                return
            
            try:
                base_key = self.menu_types[menu_type]
                menu_path = self.menu_paths[menu_type]
                
                # 创建菜单项
                key_path = f"{menu_path}\\{name}"
                with winreg.CreateKey(base_key, key_path) as key:
                    winreg.SetValueEx(key, None, 0, winreg.REG_SZ, name)
                    if icon:
                        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon)
                
                # 创建命令项
                cmd_path = f"{key_path}\\command"
                with winreg.CreateKey(base_key, cmd_path) as cmd_key:
                    winreg.SetValueEx(cmd_key, None, 0, winreg.REG_SZ, command)
                
                messagebox.showinfo("成功", "菜单项已成功添加")
                add_window.destroy()
                self.load_menu_items()
                self.status_var.set(f"已添加菜单项: {name}")
            except Exception as e:
                messagebox.showerror("错误", f"添加菜单项失败: {str(e)}")
        
        save_btn = ttk.Button(
            btn_frame, 
            text="保存", 
            command=save_menu_item,
            style="Accent.TButton",
            width=10
        )
        save_btn.pack(side="left", padx=10)
        
        cancel_btn = ttk.Button(
            btn_frame, 
            text="取消", 
            command=add_window.destroy,
            width=10
        )
        cancel_btn.pack(side="left", padx=10)
    
    def remove_menu_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个菜单项")
            return
        
        item = self.tree.item(selected[0])
        menu_name = item["values"][0]
        
        if not messagebox.askyesno("确认删除", f"确定要删除菜单项 '{menu_name}' 吗？"):
            return
        
        menu_type = self.selected_menu_type.get()
        base_key = self.menu_types[menu_type]
        menu_path = self.menu_paths[menu_type]
        
        try:
            # 查找实际的注册表键名
            with winreg.OpenKey(base_key, menu_path) as key:
                index = 0
                found = False
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, index)
                        index += 1
                        
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            display_name = winreg.QueryValueEx(subkey, None)[0]
                            if display_name == menu_name:
                                found = True
                                break
                    except OSError:
                        break
                
                if found:
                    # 删除菜单项
                    winreg.DeleteKey(base_key, f"{menu_path}\\{subkey_name}\\command")
                    winreg.DeleteKey(base_key, f"{menu_path}\\{subkey_name}")
                    messagebox.showinfo("成功", "菜单项已删除")
                    self.load_menu_items()
                    self.status_var.set(f"已删除菜单项: {menu_name}")
                else:
                    messagebox.showerror("错误", "找不到对应的注册表项")
        except Exception as e:
            messagebox.showerror("错误", f"删除菜单项失败: {str(e)}")
    
    def backup_config(self):
        menu_type = self.selected_menu_type.get()
        base_key = self.menu_types[menu_type]
        menu_path = self.menu_paths[menu_type]
        
        backup_data = {
            "menu_type": menu_type,
            "timestamp": datetime.now().isoformat(),
            "items": []
        }
        
        try:
            with winreg.OpenKey(base_key, menu_path) as key:
                index = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, index)
                        index += 1
                        
                        item_data = {"key": subkey_name}
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            # 获取显示名称
                            try:
                                display_name = winreg.QueryValueEx(subkey, None)[0]
                                item_data["display_name"] = display_name
                            except:
                                item_data["display_name"] = subkey_name
                            
                            # 获取图标
                            try:
                                icon_path = winreg.QueryValueEx(subkey, "Icon")[0]
                                item_data["icon"] = icon_path
                            except:
                                pass
                            
                            # 获取命令
                            try:
                                with winreg.OpenKey(subkey, "command") as cmd_key:
                                    command = winreg.QueryValueEx(cmd_key, None)[0]
                                    item_data["command"] = command
                            except:
                                pass
                            
                        backup_data["items"].append(item_data)
                    except OSError:
                        break
            
            # 保存为JSON文件
            file_path = filedialog.asksaveasfilename(
                title="保存备份",
                filetypes=[("JSON文件", "*.json")],
                defaultextension=".json",
                initialfile=f"right_click_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            if file_path:
                with open(file_path, "w") as f:
                    json.dump(backup_data, f, indent=2)
                
                messagebox.showinfo("成功", f"备份已保存到: {file_path}")
                self.status_var.set(f"配置已备份到: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("错误", f"备份失败: {str(e)}")
    
    def restore_config(self):
        file_path = filedialog.askopenfilename(
            title="选择备份文件",
            filetypes=[("JSON文件", "*.json")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, "r") as f:
                backup_data = json.load(f)
            
            menu_type = backup_data.get("menu_type", self.selected_menu_type.get())
            base_key = self.menu_types[menu_type]
            menu_path = self.menu_paths[menu_type]
            
            # 删除现有菜单项
            try:
                with winreg.OpenKey(base_key, menu_path) as key:
                    index = 0
                    to_delete = []
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, index)
                            to_delete.append(subkey_name)
                            index += 1
                        except OSError:
                            break
                
                # 删除所有子项
                for subkey_name in to_delete:
                    try:
                        winreg.DeleteKey(base_key, f"{menu_path}\\{subkey_name}\\command")
                        winreg.DeleteKey(base_key, f"{menu_path}\\{subkey_name}")
                    except:
                        pass
            except:
                pass
            
            # 恢复备份的菜单项
            for item in backup_data.get("items", []):
                key = item.get("key", "")
                display_name = item.get("display_name", key)
                command = item.get("command", "")
                icon = item.get("icon", "")
                
                if not key or not command:
                    continue
                
                try:
                    # 创建菜单项
                    key_path = f"{menu_path}\\{key}"
                    with winreg.CreateKey(base_key, key_path) as reg_key:
                        winreg.SetValueEx(reg_key, None, 0, winreg.REG_SZ, display_name)
                        if icon:
                            winreg.SetValueEx(reg_key, "Icon", 0, winreg.REG_SZ, icon)
                    
                    # 创建命令项
                    cmd_path = f"{key_path}\\command"
                    with winreg.CreateKey(base_key, cmd_path) as cmd_key:
                        winreg.SetValueEx(cmd_key, None, 0, winreg.REG_SZ, command)
                except:
                    pass
            
            messagebox.showinfo("成功", "配置已恢复")
            self.load_menu_items()
            self.status_var.set(f"已从 {os.path.basename(file_path)} 恢复配置")
        except Exception as e:
            messagebox.showerror("错误", f"恢复失败: {str(e)}")
    
    def reset_default(self):
        if not messagebox.askyesno("确认重置", "确定要重置为默认设置吗？这将删除所有自定义菜单项。"):
            return
        
        menu_type = self.selected_menu_type.get()
        base_key = self.menu_types[menu_type]
        menu_path = self.menu_paths[menu_type]
        
        try:
            with winreg.OpenKey(base_key, menu_path) as key:
                index = 0
                to_delete = []
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, index)
                        to_delete.append(subkey_name)
                        index += 1
                    except OSError:
                        break
            
            # 删除所有子项
            for subkey_name in to_delete:
                try:
                    winreg.DeleteKey(base_key, f"{menu_path}\\{subkey_name}\\command")
                    winreg.DeleteKey(base_key, f"{menu_path}\\{subkey_name}")
                except:
                    pass
            
            messagebox.showinfo("成功", "已重置为默认设置")
            self.load_menu_items()
            self.status_var.set(f"{menu_type} 已重置")
        except Exception as e:
            messagebox.showerror("错误", f"重置失败: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = RightClickManager(root)
    root.mainloop()
