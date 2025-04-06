import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
import threading
import queue
import os
import sys
import subprocess
from html2md import convert_url_to_md, convert_file_to_md, convert_directory_to_md

class RedirectText:
    def __init__(self, text_widget, queue):
        self.queue = queue
        self.text_widget = text_widget

    def write(self, string):
        self.queue.put(string)

    def flush(self):
        pass

class HTML2MDGui(ttk.Window):
    def __init__(self):
        super().__init__(themename="cosmo")
        self.title("HTML2MD")
        self.geometry("800x600")
        self.queue = queue.Queue()
        
        # 设置默认输出目录
        self.default_output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        if not os.path.exists(self.default_output_dir):
            os.makedirs(self.default_output_dir)
            
        self.create_widgets()
        
        # 重定向标准输出到GUI
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        sys.stdout = RedirectText(self.output_text, self.queue)
        sys.stderr = RedirectText(self.output_text, self.queue)
        
        self.check_queue()

    def __del__(self):
        # 恢复标准输出
        sys.stdout = self.stdout
        sys.stderr = self.stderr

    def create_widgets(self):
        # 主容器
        main_container = ttk.Frame(self, padding=20)
        main_container.pack(fill=BOTH, expand=YES)

        # 输入区域
        input_frame = ttk.LabelFrame(main_container, text="输入", padding=10)
        input_frame.pack(fill=X, pady=(0, 10))

        # URL输入
        url_frame = ttk.Frame(input_frame)
        url_frame.pack(fill=X, pady=(0, 5))
        ttk.Label(url_frame, text="URL:").pack(side=LEFT)
        self.url_entry = ttk.Entry(url_frame)
        self.url_entry.pack(side=LEFT, fill=X, expand=YES, padx=(5, 5))
        ttk.Button(
            url_frame,
            text="转换URL",
            command=lambda: self.start_conversion("url"),
            style="primary.TButton"
        ).pack(side=LEFT)

        # 文件选择
        file_frame = ttk.Frame(input_frame)
        file_frame.pack(fill=X, pady=5)
        ttk.Label(file_frame, text="文件:").pack(side=LEFT)
        self.file_entry = ttk.Entry(file_frame)
        self.file_entry.pack(side=LEFT, fill=X, expand=YES, padx=(5, 5))
        ttk.Button(
            file_frame,
            text="选择文件",
            command=self.choose_file
        ).pack(side=LEFT)
        ttk.Button(
            file_frame,
            text="转换文件",
            command=lambda: self.start_conversion("file"),
            style="primary.TButton"
        ).pack(side=LEFT, padx=(5, 0))

        # 目录选择
        dir_frame = ttk.Frame(input_frame)
        dir_frame.pack(fill=X, pady=(0, 5))
        ttk.Label(dir_frame, text="目录:").pack(side=LEFT)
        self.dir_entry = ttk.Entry(dir_frame)
        self.dir_entry.pack(side=LEFT, fill=X, expand=YES, padx=(5, 5))
        ttk.Button(
            dir_frame,
            text="选择目录",
            command=self.choose_directory
        ).pack(side=LEFT)
        ttk.Button(
            dir_frame,
            text="转换目录",
            command=lambda: self.start_conversion("directory"),
            style="primary.TButton"
        ).pack(side=LEFT, padx=(5, 0))

        # 输出目录选择
        output_dir_frame = ttk.Frame(input_frame)
        output_dir_frame.pack(fill=X)
        ttk.Label(output_dir_frame, text="输出:").pack(side=LEFT)
        self.output_dir_entry = ttk.Entry(output_dir_frame)
        self.output_dir_entry.pack(side=LEFT, fill=X, expand=YES, padx=(5, 5))
        self.output_dir_entry.insert(0, self.default_output_dir)  # 设置默认值
        ttk.Button(
            output_dir_frame,
            text="选择输出目录",
            command=self.choose_output_directory
        ).pack(side=LEFT)
        ttk.Button(
            output_dir_frame,
            text="打开输出目录",
            command=self.open_output_directory,
            style="info.TButton"
        ).pack(side=LEFT, padx=(5, 0))

        # 输出区域
        output_frame = ttk.LabelFrame(main_container, text="输出", padding=10)
        output_frame.pack(fill=BOTH, expand=YES)

        # 输出文本框
        self.output_text = ScrolledText(output_frame)
        self.output_text.pack(fill=BOTH, expand=YES)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=BOTTOM, fill=X)

    def choose_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )
        if filename:
            self.file_entry.delete(0, END)
            self.file_entry.insert(0, filename)

    def choose_directory(self):
        dirname = filedialog.askdirectory()
        if dirname:
            self.dir_entry.delete(0, END)
            self.dir_entry.insert(0, dirname)

    def choose_output_directory(self):
        dirname = filedialog.askdirectory()
        if dirname:
            self.output_dir_entry.delete(0, END)
            self.output_dir_entry.insert(0, dirname)

    def start_conversion(self, mode):
        if mode == "url" and not self.url_entry.get():
            messagebox.showwarning("警告", "请输入URL")
            return
        elif mode == "file" and not self.file_entry.get():
            messagebox.showwarning("警告", "请选择文件")
            return
        elif mode == "directory" and not self.dir_entry.get():
            messagebox.showwarning("警告", "请选择目录")
            return

        # 确保输出目录存在
        output_dir = self.output_dir_entry.get() or self.default_output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        self.status_var.set("正在转换...")
        self.output_text.delete(1.0, END)
        
        # 显示开始转换信息
        if mode == "url":
            print(f"开始转换URL: {self.url_entry.get()}")
            print(f"输出目录: {output_dir}")
        elif mode == "file":
            print(f"开始转换文件: {self.file_entry.get()}")
            print(f"输出目录: {output_dir}")
        else:
            print(f"开始转换目录: {self.dir_entry.get()}")
            print(f"输出目录: {output_dir}")
        print("-" * 50)
        
        thread = threading.Thread(target=self.convert, args=(mode,))
        thread.daemon = True
        thread.start()

    def convert(self, mode):
        try:
            output_dir = self.output_dir_entry.get() or self.default_output_dir
            result = None
            
            if mode == "url":
                result = convert_url_to_md(self.url_entry.get(), output_dir)
            elif mode == "file":
                result = convert_file_to_md(self.file_entry.get(), output_dir)
            else:
                result = convert_directory_to_md(self.dir_entry.get(), output_dir)
                
            print("-" * 50)
            if result:
                print("\n转换完成！")
                if isinstance(result, str):
                    print(f"输出文件: {result}")
                print(f"\n所有文件已保存到: {output_dir}")
            else:
                print("\n转换失败，请检查输入是否正确")
                
            self.status_var.set("转换完成")
        except Exception as e:
            print("-" * 50)
            print(f"\n错误: {str(e)}")
            self.status_var.set("转换失败")

    def check_queue(self):
        while True:
            try:
                msg = self.queue.get_nowait()
                self.output_text.insert(END, msg)
                self.output_text.see(END)
            except queue.Empty:
                break
        self.after(100, self.check_queue)

    def open_output_directory(self):
        """打开输出目录"""
        output_dir = self.output_dir_entry.get() or self.default_output_dir
        if os.path.exists(output_dir):
            try:
                # Windows系统
                if os.name == 'nt':
                    os.startfile(output_dir)
                # macOS系统
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', output_dir])
                # Linux系统
                else:
                    subprocess.Popen(['xdg-open', output_dir])
            except Exception as e:
                messagebox.showerror("错误", f"无法打开输出目录: {str(e)}")
        else:
            messagebox.showwarning("警告", "输出目录不存在")

def main():
    app = HTML2MDGui()
    app.mainloop()

if __name__ == "__main__":
    main() 