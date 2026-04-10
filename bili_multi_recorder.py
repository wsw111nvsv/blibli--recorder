import tkinter as tk
from tkinter import messagebox, scrolledtext
import subprocess
import threading
import datetime
import time
import os

class RoomRecorder(threading.Thread):
    """专门负责单个直播间录制的线程类"""
    def __init__(self, room_id, log_func):
        super().__init__()
        self.room_id = room_id
        self.log = log_func
        self.is_running = True
        self.process = None
        self.daemon = True

    def run(self):
        url = f"https://live.bilibili.com/{self.room_id}"
        self.log(f"【{self.room_id}】开始持续监控...")
        
        while self.is_running:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"Live_{self.room_id}_{timestamp}.ts"
            
            # 使用 streamlink 获取流
            cmd = ["streamlink", url, "best", "-o", filename, "--loglevel", "info"]
            
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                self.process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, creationflags=creationflags
                )

                active_recording = False
                for line in self.process.stdout:
                    if not self.is_running: break
                    if "Writing stream to output" in line:
                        if not active_recording:
                            self.log(f"【{self.room_id}】正在录制中 -> {filename}")
                            active_recording = True
                
                self.process.wait()
            except Exception as e:
                self.log(f"【{self.room_id}】异常: {e}")

            if not self.is_running: break
            
            # 状态检查间隔
            time.sleep(30) 

    def stop(self):
        self.is_running = False
        if self.process:
            self.process.terminate()

class MultiRecorderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("B站多房间自动录制工具 v2.0")
        self.root.geometry("600x500")
        
        self.recorder_threads = {} # 存放 {room_id: thread_object}
        self.setup_ui()

    def setup_ui(self):
        # 顶部：输入和添加
        top_frame = tk.Frame(self.root)
        top_frame.pack(pady=15, padx=20, fill="x")

        tk.Label(top_frame, text="房间号:").pack(side="left")
        self.room_entry = tk.Entry(top_frame, width=15)
        self.room_entry.pack(side="left", padx=5)
        
        self.add_btn = tk.Button(top_frame, text="添加并开始监控", command=self.add_room, bg="#00a1d6", fg="white")
        self.add_btn.pack(side="left", padx=5)

        # 中部：房间列表展示
        list_label = tk.Label(self.root, text="当前监控列表 (双击房间号停止并删除):")
        list_label.pack(anchor="w", padx=20)
        
        self.room_listbox = tk.Listbox(self.root, height=5, font=("Arial", 10))
        self.room_listbox.pack(pady=5, padx=20, fill="x")
        self.room_listbox.bind('<Double-Button-1>', self.remove_room)

        # 底部：日志展示
        tk.Label(self.root, text="运行状态日志:").pack(anchor="w", padx=20)
        self.log_area = scrolledtext.ScrolledText(self.root, height=15, state='disabled', font=("Consolas", 9))
        self.log_area.pack(pady=5, padx=20, fill="both", expand=True)

    def write_log(self, message):
        """线程安全的日志打印"""
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"[{now}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def add_room(self):
        room_id = self.room_entry.get().strip()
        if not room_id or room_id in self.recorder_threads:
            messagebox.showwarning("提示", "房间号不能为空且不能重复添加！")
            return
        
        # 启动新线程
        t = RoomRecorder(room_id, self.write_log)
        t.start()
        
        self.recorder_threads[room_id] = t
        self.room_listbox.insert(tk.END, room_id)
        self.room_entry.delete(0, tk.END)
        self.write_log(f"已成功添加房间: {room_id}")

    def remove_room(self, event):
        selection = self.room_listbox.curselection()
        if selection:
            index = selection[0]
            room_id = self.room_listbox.get(index)
            
            # 停止线程
            if room_id in self.recorder_threads:
                self.recorder_threads[room_id].stop()
                del self.recorder_threads[room_id]
            
            self.room_listbox.delete(index)
            self.write_log(f"已移除房间: {room_id}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MultiRecorderGUI(root)
    
    # 退出程序时确保杀死所有子进程
    def on_closing():
        for t in app.recorder_threads.values():
            t.stop()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
