import os
import time
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageGrab
import threading
import ctypes
from ctypes import wintypes
import win32con
import win32gui

# Import modules from our project
import direct_input
from bot import ForzaBot

# Try to import cv2
try:
    import cv2
except ImportError:
    cv2 = None

# Global WinAPI details for Hotkeys
user32 = ctypes.windll.user32
HOTKEY_START_ID = 100
HOTKEY_STOP_ID = 101
VK_F10 = 0x79  # F10 key
VK_F11 = 0x7A  # F11 key

FONT_FAMILY = "Microsoft JhengHei"

class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Forza Horizon 6 刷技能點小助手")
        self.root.geometry("640x580")
        self.root.configure(bg="#1a1a22")
        self.root.resizable(False, False)
        
        # Initialize the bot
        self.bot = ForzaBot()
        self.bot.log_callback = self.log_message
        self.bot.state_callback = self.on_state_change
        
        # Keep references to thumbnail images to prevent garbage collection
        self.thumbnails = {}
        
        # Track visible windows
        self.windows_map = {}
        
        # Track auto stop timer
        self.auto_stop_target_time = None
        
        # Thread safety control for hotkeys
        self.hotkey_stop_event = threading.Event()
        self.hotkey_thread = None
        
        # Custom styling
        self.setup_styles()
        # Build UI layout
        self.build_ui()
        # Start hotkey listener
        self.start_hotkey_listener()
        
        # Periodically refresh bot status in GUI
        self.refresh_timer()
        
        # Log init status
        self.log_message("系統初始化完成。")
        self.check_opencv_status()
        self.update_all_thumbnails()
        self.refresh_windows_list()

    def check_opencv_status(self):
        global cv2
        try:
            import cv2
            self.bot.log("OpenCV 載入成功！圖像比對功能已啟用。")
        except ImportError:
            self.log_message("警告: OpenCV (cv2) 尚未成功安裝。圖像辨識將無法運作！")
            self.log_message("正在等候背景安裝程序完成...")

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure frames and layouts
        style.configure("TFrame", background="#1a1a22")
        style.configure("Card.TFrame", background="#252533", relief="flat")
        
        # Notebook styling
        style.configure("TNotebook", background="#1a1a22", borderwidth=0)
        style.configure("TNotebook.Tab", background="#252533", foreground="#a0a0b0", font=(FONT_FAMILY, 10, "bold"), padding=[18, 6])
        style.map("TNotebook.Tab",
                  background=[("selected", "#00e5ff"), ("active", "#2e2e3d")],
                  foreground=[("selected", "#1a1a22"), ("active", "#ffffff")])
        
        # Scrollbar styling
        style.configure("Vertical.TScrollbar", background="#2a2a38", troughcolor="#15151d", bordercolor="#1a1a22", arrowcolor="#ffffff")

    def build_ui(self):
        # Header (Minimalist title + indicator)
        header_frame = tk.Frame(self.root, bg="#111116", height=50)
        header_frame.pack(fill="x", side="top")
        
        title_label = tk.Label(header_frame, text="FORZA HORIZON 6 SKILL BOT", font=(FONT_FAMILY, 14, "bold"), fg="#00e5ff", bg="#111116")
        title_label.pack(side="left", padx=15, pady=10)
        
        # Status indicator dot
        self.status_dot = tk.Canvas(header_frame, width=12, height=12, bg="#111116", highlightthickness=0)
        self.status_dot.pack(side="right", padx=(0, 15), pady=18)
        self.draw_status_dot("#ef4444") # Red for stopped
        
        self.status_text = tk.Label(header_frame, text="已停止 (IDLE)", font=(FONT_FAMILY, 9, "bold"), fg="#ef4444", bg="#111116")
        self.status_text.pack(side="right", padx=8, pady=15)
        
        # Main Tab Container
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=12)
        
        # Create Tab Frames
        self.tab_dash = ttk.Frame(self.notebook, style="TFrame")
        self.tab_settings = ttk.Frame(self.notebook, style="TFrame")
        self.tab_calib = ttk.Frame(self.notebook, style="TFrame")
        
        self.notebook.add(self.tab_dash, text=" 運行儀表板 ")
        self.notebook.add(self.tab_settings, text=" 參數設定 ")
        self.notebook.add(self.tab_calib, text=" 圖像校準 ")
        
        # Build contents for each tab
        self.build_dash_tab()
        self.build_settings_tab()
        self.build_calib_tab()

    def build_dash_tab(self):
        # 1. State card
        state_card = ttk.Frame(self.tab_dash, style="Card.TFrame")
        state_card.pack(fill="x", padx=10, pady=(10, 5))
        
        state_title = tk.Label(state_card, text="當前執行狀態", font=(FONT_FAMILY, 9), fg="#a0a0b0", bg="#252533")
        state_title.pack(anchor="w", padx=15, pady=(8, 2))
        
        self.state_desc = tk.Label(state_card, text="未啟動 - 請按 F10 鍵或點擊下方啟動按鈕", font=(FONT_FAMILY, 12, "bold"), fg="#ffffff", bg="#252533")
        self.state_desc.pack(anchor="w", padx=15, pady=(0, 8))
        
        # 2. Control Buttons
        btn_frame = tk.Frame(self.tab_dash, bg="#1a1a22")
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        self.btn_start = tk.Button(btn_frame, text="啟動腳本 (F10)", font=(FONT_FAMILY, 10, "bold"), bg="#10b981", fg="#ffffff", activebackground="#059669", activeforeground="#ffffff", relief="flat", padx=15, pady=6, command=self.start_bot)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.btn_stop = tk.Button(btn_frame, text="停止腳本 (F11)", font=(FONT_FAMILY, 10, "bold"), bg="#ef4444", fg="#ffffff", activebackground="#dc2626", activeforeground="#ffffff", relief="flat", padx=15, pady=6, command=self.stop_bot)
        self.btn_stop.pack(side="right", fill="x", expand=True, padx=(5, 0))
        
        # 3. Terminal Log
        log_frame = ttk.Frame(self.tab_dash, style="Card.TFrame")
        log_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        log_title = tk.Label(log_frame, text="實時運行日誌", font=(FONT_FAMILY, 9), fg="#a0a0b0", bg="#252533")
        log_title.pack(anchor="w", padx=15, pady=(6, 4))
        
        self.log_text = tk.Text(log_frame, bg="#15151c", fg="#2efb57", insertbackground="#ffffff", relief="flat", font=("Consolas", 9), wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=15, pady=(0, 10))

    def build_settings_tab(self):
        settings_card = ttk.Frame(self.tab_settings, style="Card.TFrame")
        settings_card.pack(fill="both", expand=True, padx=10, pady=10)
        
        settings_title = tk.Label(settings_card, text="自動化參數配置", font=(FONT_FAMILY, 11, "bold"), fg="#00e5ff", bg="#252533")
        settings_title.pack(anchor="w", padx=15, pady=(12, 10))
        
        grid_frame = tk.Frame(settings_card, bg="#252533")
        grid_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        # Row 0: Window selection
        tk.Label(grid_frame, text="選擇遊戲視窗:", font=(FONT_FAMILY, 9), fg="#a0a0b0", bg="#252533", anchor="w").grid(row=0, column=0, sticky="w", pady=8)
        
        win_select_frame = tk.Frame(grid_frame, bg="#252533")
        win_select_frame.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=8)
        
        self.combo_windows = ttk.Combobox(win_select_frame, width=24, state="readonly", font=(FONT_FAMILY, 9))
        self.combo_windows.pack(side="left")
        self.combo_windows.bind("<<ComboboxSelected>>", self.on_window_selected)
        
        self.btn_refresh_windows = tk.Button(win_select_frame, text="🔄 重新整理", font=(FONT_FAMILY, 8), bg="#4b5563", fg="#ffffff", activebackground="#374151", relief="flat", padx=6, pady=1, command=self.refresh_windows_list)
        self.btn_refresh_windows.pack(side="left", padx=(6, 0))
        
        self.is_topmost_var = tk.BooleanVar(value=False)
        self.chk_topmost = tk.Checkbutton(grid_frame, text="視窗強制置頂", variable=self.is_topmost_var, fg="#a0a0b0", bg="#252533", selectcolor="#15151c", activebackground="#252533", activeforeground="#a0a0b0", font=(FONT_FAMILY, 9), command=self.toggle_topmost)
        self.chk_topmost.grid(row=0, column=2, sticky="w", padx=(15, 0), pady=8)
        
        # Row 1: Duration & Background Mode
        tk.Label(grid_frame, text="單局賽事秒數:", font=(FONT_FAMILY, 9), fg="#a0a0b0", bg="#252533", anchor="w").grid(row=1, column=0, sticky="w", pady=8)
        self.entry_duration = tk.Entry(grid_frame, bg="#15151c", fg="#ffffff", insertbackground="#ffffff", relief="flat", width=12, font=(FONT_FAMILY, 9))
        self.entry_duration.insert(0, str(int(self.bot.race_duration)))
        self.entry_duration.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=8)
        
        self.prevent_deactivate_var = tk.BooleanVar(value=False)
        self.chk_prevent_deactivate = tk.Checkbutton(grid_frame, text="背景維持聚焦 (防止停用)", variable=self.prevent_deactivate_var, fg="#a0a0b0", bg="#252533", selectcolor="#15151c", activebackground="#252533", activeforeground="#a0a0b0", font=(FONT_FAMILY, 9), command=self.toggle_prevent_deactivate)
        self.chk_prevent_deactivate.grid(row=1, column=2, sticky="w", padx=(15, 0), pady=8)
        
        # Row 2: Threshold
        tk.Label(grid_frame, text="辨識相似門檻:", font=(FONT_FAMILY, 9), fg="#a0a0b0", bg="#252533", anchor="w").grid(row=2, column=0, sticky="w", pady=8)
        self.entry_threshold = tk.Entry(grid_frame, bg="#15151c", fg="#ffffff", insertbackground="#ffffff", relief="flat", width=12, font=(FONT_FAMILY, 9))
        self.entry_threshold.insert(0, str(self.bot.threshold))
        self.entry_threshold.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=8)
        
        # Row 3: Auto stop timer
        tk.Label(grid_frame, text="自動停止定時:", font=(FONT_FAMILY, 9), fg="#a0a0b0", bg="#252533", anchor="w").grid(row=3, column=0, sticky="w", pady=8)
        self.combo_timer = ttk.Combobox(grid_frame, width=10, state="readonly", values=["不限時", "1 小時", "1.5 小時", "2 小時", "3 小時"], font=(FONT_FAMILY, 9))
        self.combo_timer.set("不限時")
        self.combo_timer.grid(row=3, column=1, sticky="w", padx=(10, 0), pady=8)
        
        self.lbl_countdown = tk.Label(grid_frame, text="", fg="#ff007f", bg="#252533", font=(FONT_FAMILY, 9, "bold"))
        self.lbl_countdown.grid(row=3, column=2, sticky="w", padx=(15, 0), pady=8)
        
        # Save Button
        self.btn_save_settings = tk.Button(grid_frame, text="儲存並套用設定", font=(FONT_FAMILY, 9, "bold"), bg="#3b82f6", fg="#ffffff", activebackground="#2563eb", activeforeground="#ffffff", relief="flat", padx=15, pady=4, command=self.save_settings)
        self.btn_save_settings.grid(row=4, column=1, sticky="e", pady=(20, 0))

    def build_calib_tab(self):
        template_card = ttk.Frame(self.tab_calib, style="Card.TFrame")
        template_card.pack(fill="both", expand=True, padx=10, pady=10)
        
        temp_title = tk.Label(template_card, text="圖像匹配模板校準與設定", font=(FONT_FAMILY, 11, "bold"), fg="#00e5ff", bg="#252533")
        temp_title.pack(anchor="w", padx=15, pady=(12, 5))
        
        inst_text = tk.Label(template_card, text="如果辨識不準，請在遊戲執行至對應畫面時點擊「擷取」，然後在跳出的截圖中框選目標文字區域。", font=(FONT_FAMILY, 9), fg="#a0a0b0", bg="#252533", justify="left")
        inst_text.pack(anchor="w", padx=15, pady=(0, 10))
        
        # Grid list for template items
        self.temp_items = [
            ("restart.png", "重新開始字樣", "等待結算畫面出現此字樣以重新開始"),
            ("yes.png", "確認選單「是」", "確認重新開始對話框的「是」按鈕（偵測後模擬 Enter）"),
            ("start.png", "開始賽事字樣", "即將開始賽事時，按下 Enter 的字樣")
        ]
        
        self.temp_frames = {}
        for filename, title, desc in self.temp_items:
            item_frame = tk.Frame(template_card, bg="#1e1e28", bd=1, relief="solid", highlightthickness=0)
            item_frame.pack(fill="x", padx=15, pady=5)
            
            # Title
            lbl_title = tk.Label(item_frame, text=title, font=(FONT_FAMILY, 9, "bold"), fg="#ffffff", bg="#1e1e28")
            lbl_title.pack(anchor="w", padx=8, pady=(4, 0))
            
            # Subframe for contents
            detail_frame = tk.Frame(item_frame, bg="#1e1e28")
            detail_frame.pack(fill="x", padx=8, pady=4)
            
            # Thumbnail
            thumb_canvas = tk.Canvas(detail_frame, width=50, height=35, bg="#15151c", highlightthickness=1, highlightbackground="#3e3e4f")
            thumb_canvas.pack(side="left", padx=(0, 10))
            
            # Text information & button
            info_btn_frame = tk.Frame(detail_frame, bg="#1e1e28")
            info_btn_frame.pack(side="left", fill="both", expand=True)
            
            lbl_desc = tk.Label(info_btn_frame, text=desc, font=(FONT_FAMILY, 8), fg="#808090", bg="#1e1e28", justify="left")
            lbl_desc.pack(anchor="w", pady=(0, 2))
            
            btn_cap = tk.Button(info_btn_frame, text=" 重新擷取模板 ", font=(FONT_FAMILY, 8), bg="#00e5ff", fg="#1a1a22", activebackground="#00b8cc", activeforeground="#1a1a22", relief="flat", padx=8, pady=1, command=lambda fn=filename: self.capture_template(fn))
            btn_cap.pack(anchor="w")
            
            self.temp_frames[filename] = {
                "canvas": thumb_canvas,
                "label": lbl_title
            }

    def draw_status_dot(self, color):
        self.status_dot.delete("all")
        self.status_dot.create_oval(2, 2, 10, 10, fill=color, outline="")

    def log_message(self, message):
        """Thread-safe logging to the text widget."""
        def action():
            self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
            self.log_text.see(tk.END)
        self.root.after(0, action)

    def on_state_change(self, state):
        """Callback for bot state transitions."""
        def action():
            if state == "IDLE":
                self.draw_status_dot("#ef4444") # Red
                self.status_text.config(text="已停止 (IDLE)", fg="#ef4444")
                self.state_desc.config(text="未啟動 - 請按 F10 鍵或點擊下方啟動按鈕", fg="#ffffff")
            elif state == "WAIT_FOR_SETTLEMENT":
                self.draw_status_dot("#00e5ff") # Cyan
                self.status_text.config(text="偵測中 (ACTIVE)", fg="#00e5ff")
                self.state_desc.config(text="偵測結算畫面中... (尋找：重新開始)", fg="#00e5ff")
            elif state == "WAIT_FOR_CONFIRM":
                self.draw_status_dot("#3b82f6") # Blue
                self.status_text.config(text="偵測中 (ACTIVE)", fg="#3b82f6")
                self.state_desc.config(text="偵測對話框中... (尋找：確認-是)", fg="#3b82f6")
            elif state == "WAIT_FOR_START_EVENT":
                self.draw_status_dot("#ff007f") # Pink
                self.status_text.config(text="偵測中 (ACTIVE)", fg="#ff007f")
                self.state_desc.config(text="偵測賽事起跑中... (尋找：開始賽事)", fg="#ff007f")
            elif state == "RACING":
                self.draw_status_dot("#10b981") # Green
                self.status_text.config(text="執行中 (RACING)", fg="#10b981")
                self.state_desc.config(text="自動賽事計時等待中...", fg="#10b981")
        self.root.after(0, action)

    def save_settings(self):
        try:
            duration = float(self.entry_duration.get())
            threshold = float(self.entry_threshold.get())
            window_title = self.combo_windows.get()
            
            if duration <= 0:
                raise ValueError("秒數必須大於 0")
            if not (0.1 <= threshold <= 1.0):
                raise ValueError("相似度門檻必須在 0.1 到 1.0 之間")
            if not window_title:
                raise ValueError("未選擇遊戲視窗")
                
            self.bot.race_duration = duration
            self.bot.threshold = threshold
            self.bot.game_window_title = window_title
            self.bot.selected_hwnd = self.windows_map.get(window_title)
            
            self.log_message(f"設定已儲存：賽事時間 {duration} 秒，相似門檻 {threshold}，視窗標題「{window_title}」")
            messagebox.showinfo("成功", "設定參數已儲存！")
        except ValueError as e:
            messagebox.showerror("錯誤", f"輸入值無效：{e}")

    def start_bot(self):
        # Apply current inputs first
        try:
            self.bot.race_duration = float(self.entry_duration.get())
            self.bot.threshold = float(self.entry_threshold.get())
            window_title = self.combo_windows.get()
            self.bot.game_window_title = window_title
            self.bot.selected_hwnd = self.windows_map.get(window_title)
        except ValueError:
            pass
            
        if not self.bot.is_running:
            # Check OpenCV again in case it finished installing
            self.check_opencv_status()
            
            # Check if templates exist
            missing = []
            for filename, _, _ in self.temp_items:
                path = os.path.join(self.bot.templates_dir, filename)
                if not os.path.exists(path):
                    missing.append(filename)
            if missing:
                self.log_message(f"錯誤: 缺少模板檔案 {missing}，請先完成擷取。")
                messagebox.showwarning("警告", "請先截圖設定所有匹配模板再啟動腳本！")
                return
                
            self.bot.start()
            
            # Start timer if selected
            timer_val = self.combo_timer.get()
            if timer_val != "不限時":
                seconds = 0
                if timer_val == "1 小時":
                    seconds = 3600
                elif timer_val == "1.5 小時":
                    seconds = 5400
                elif timer_val == "2 小時":
                    seconds = 7200
                elif timer_val == "3 小時":
                    seconds = 10800
                    
                if seconds > 0:
                    self.auto_stop_target_time = time.time() + seconds
                    self.log_message(f"已啟動定時關閉：將於 {timer_val} 後自動停止掛機。")
            else:
                self.auto_stop_target_time = None
                
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
            
    def stop_bot(self):
        if self.bot.is_running:
            self.bot.stop()
            self.auto_stop_target_time = None
            self.lbl_countdown.config(text="")
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")

    def refresh_windows_list(self):
        """Refreshes the dropdown list with visible windows."""
        self.windows_map = {}
        window_list = []
        
        def enum_windows_callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and title != "Program Manager" and title != self.root.title():
                    rect = win32gui.GetWindowRect(hwnd)
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                    if w > 100 and h > 100:
                        window_list.append((title, hwnd))
                        
        win32gui.EnumWindows(enum_windows_callback, None)
        window_list.sort(key=lambda x: x[0].lower())
        
        titles = []
        for title, hwnd in window_list:
            display_title = title
            if display_title in self.windows_map:
                display_title = f"{title} (HWND: {hwnd})"
            self.windows_map[display_title] = hwnd
            titles.append(display_title)
            
        self.combo_windows["values"] = titles
        
        # Auto-select Forza
        for title in titles:
            if "forza" in title.lower():
                self.combo_windows.set(title)
                self.bot.game_window_title = title
                self.bot.selected_hwnd = self.windows_map[title]
                break
        else:
            if titles:
                self.combo_windows.set(titles[0])
                self.bot.game_window_title = titles[0]
                self.bot.selected_hwnd = self.windows_map[titles[0]]
                
        self.log_message(f"已整理目前電腦上的視窗列表（共 {len(titles)} 個）")

    def on_window_selected(self, event):
        selected_title = self.combo_windows.get()
        if selected_title:
            self.bot.game_window_title = selected_title
            self.bot.selected_hwnd = self.windows_map.get(selected_title)
            # Reset topmost when switching windows
            self.is_topmost_var.set(False)
            self.log_message(f"已選擇遊戲視窗：{selected_title}")

    def toggle_topmost(self):
        """Toggles the topmost status of the selected window."""
        selected_title = self.combo_windows.get()
        if not selected_title:
            messagebox.showwarning("警告", "請先選擇一個視窗！")
            self.is_topmost_var.set(False)
            return
            
        hwnd = self.windows_map.get(selected_title)
        if not hwnd or not win32gui.IsWindow(hwnd):
            messagebox.showerror("錯誤", "找不到該視窗的有效控制代碼 (HWND)，請重新整理列表。")
            self.is_topmost_var.set(False)
            return
            
        enable = self.is_topmost_var.get()
        try:
            if enable:
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                     win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
                self.log_message(f"已將視窗「{selected_title}」強制置頂顯示。")
            else:
                win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                                     win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
                self.log_message(f"已取消視窗「{selected_title}」的置頂顯示。")
        except Exception as e:
            self.log_message(f"置頂控制失敗: {e}")
            messagebox.showerror("錯誤", f"無法設定置頂狀態: {e}")
            self.is_topmost_var.set(False)

    def toggle_prevent_deactivate(self):
        """Logs the toggle of prevent deactivation state."""
        enable = self.prevent_deactivate_var.get()
        selected_title = self.combo_windows.get()
        if enable:
            if selected_title:
                self.log_message(f"已啟用視窗「{selected_title}」的背景維持聚焦（防止停用）功能。")
            else:
                self.log_message("已啟用背景維持聚焦功能（請先選擇視窗）。")
        else:
            self.log_message("已停用背景維持聚焦功能。")

    # Template Capture System
    def capture_template(self, filename):
        """Handles screenshot capturing and overlay for selection."""
        # Check if bot is running
        if self.bot.is_running:
            messagebox.showwarning("提示", "請先停止腳本後再擷取模板。")
            return
            
        self.log_message(f"開始擷取模板 {filename}... 視窗即將隱藏...")
        self.root.withdraw()
        self.root.update()
        
        time.sleep(0.6)
        
        hwnd, rect = self.bot.find_game_window()
        offset = (0, 0)
        
        if hwnd and rect:
            left, top, right, bottom = rect
            if left < 0: left = 0
            if top < 0: top = 0
            if right > left and bottom > top:
                screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
                offset = (left, top)
            else:
                screenshot = ImageGrab.grab()
        else:
            screenshot = ImageGrab.grab()
            self.log_message("找不到遊戲視窗，擷取全螢幕畫面。")
            
        def on_crop_finished(success, result):
            self.root.deiconify()
            self.root.update()
            
            if success:
                self.log_message(f"模板 {filename} 擷取儲存成功！")
                self.update_thumbnail(filename)
            else:
                self.log_message(f"模板擷取失敗或取消：{result}")
                
        save_path = os.path.join(self.bot.templates_dir, filename)
        CropOverlay(self.root, screenshot, save_path, on_crop_finished)

    def update_all_thumbnails(self):
        for filename, _, _ in self.temp_items:
            self.update_thumbnail(filename)

    def update_thumbnail(self, filename):
        path = os.path.join(self.bot.templates_dir, filename)
        canvas = self.temp_frames[filename]["canvas"]
        canvas.delete("all")
        
        if os.path.exists(path):
            try:
                img = Image.open(path)
                # Resize to fit 50x35 canvas
                img.thumbnail((50, 35))
                tk_img = ImageTk.PhotoImage(img)
                self.thumbnails[filename] = tk_img
                
                canvas.create_image(25, 17, image=tk_img)
                self.temp_frames[filename]["label"].config(fg="#2efb57")
            except Exception as e:
                self.log_message(f"無法載入模板預覽 {filename}: {e}")
        else:
            canvas.create_line(12, 17, 38, 17, fill="#ef4444", width=2)
            canvas.create_text(25, 17, text="未設定", fill="#ef4444", font=(FONT_FAMILY, 7))
            self.temp_frames[filename]["label"].config(fg="#ffffff")

    # Global Hotkey Listener System
    def start_hotkey_listener(self):
        self.hotkey_stop_event.clear()
        self.hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
        self.hotkey_thread.start()

    def _hotkey_loop(self):
        if not user32.RegisterHotKey(None, HOTKEY_START_ID, 0, VK_F10):
            self.log_message("警告: 無法註冊全域啟動快捷鍵 F10 (可能被佔用)")
        if not user32.RegisterHotKey(None, HOTKEY_STOP_ID, 0, VK_F11):
            self.log_message("警告: 無法註冊全域停止快捷鍵 F11 (可能被佔用)")
            
        msg = wintypes.MSG()
        while not self.hotkey_stop_event.is_set():
            r = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if r != 0:
                if msg.message == win32con.WM_HOTKEY:
                    if msg.wParam == HOTKEY_START_ID:
                        self.log_message("全域快捷鍵 F10 觸發 -> 啟動腳本")
                        self.root.after(0, self.start_bot)
                    elif msg.wParam == HOTKEY_STOP_ID:
                        self.log_message("全域快捷鍵 F11 觸發 -> 停止腳本")
                        self.root.after(0, self.stop_bot)
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
                
        user32.UnregisterHotKey(None, HOTKEY_START_ID)
        user32.UnregisterHotKey(None, HOTKEY_STOP_ID)

    def refresh_timer(self):
        """Periodic UI updates."""
        # Check auto stop countdown
        if self.bot.is_running and self.auto_stop_target_time:
            remaining = self.auto_stop_target_time - time.time()
            if remaining <= 0:
                self.auto_stop_target_time = None
                self.lbl_countdown.config(text="")
                self.log_message("定時掛機時間已到，自動停止腳本！")
                self.stop_bot()
                messagebox.showinfo("定時停止", "設定的自動掛機時間已到，腳本已安全停止。")
            else:
                hrs = int(remaining // 3600)
                mins = int((remaining % 3600) // 60)
                secs = int(remaining % 60)
                self.lbl_countdown.config(text=f"⏱️ 倒數停止: {hrs:02d}:{mins:02d}:{secs:02d}")
        else:
            if not self.bot.is_running:
                self.auto_stop_target_time = None
                self.lbl_countdown.config(text="")

        # Prevent window deactivation if enabled (DisplayFusion-like behavior)
        if hasattr(self, 'prevent_deactivate_var') and self.prevent_deactivate_var.get():
            selected_title = self.combo_windows.get()
            if selected_title:
                hwnd = self.windows_map.get(selected_title)
                if hwnd and win32gui.IsWindow(hwnd):
                    try:
                        win32gui.PostMessage(hwnd, 0x0086, 1, 0)
                        win32gui.PostMessage(hwnd, 0x0006, 1, 0)
                        win32gui.PostMessage(hwnd, 0x001C, 1, 0)
                    except Exception:
                        pass
                        
        # Schedule next tick every 500ms
        self.root.after(500, self.refresh_timer)

    def on_closing(self):
        if self.bot.is_running:
            self.bot.stop()
        self.hotkey_stop_event.set()
        user32.PostThreadMessageW(self.hotkey_thread.ident, win32con.WM_QUIT, 0, 0)
        self.root.destroy()


class CropOverlay:
    """Fullscreen borderless canvas that lets the user crop a region."""
    def __init__(self, parent, screenshot, save_path, callback):
        self.screenshot = screenshot
        self.save_path = save_path
        self.callback = callback
        
        self.top = tk.Toplevel(parent)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-topmost", True)
        
        self.width = screenshot.width
        self.height = screenshot.height
        
        self.canvas = tk.Canvas(self.top, width=self.width, height=self.height, cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        
        self.tk_img = ImageTk.PhotoImage(screenshot)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        
        self.inst_lbl = self.canvas.create_text(self.width // 2, 30, text="按住滑鼠左鍵並拖曳來框選按鈕文字區域。按 ESC 取消選取。", fill="#ef4444", font=(FONT_FAMILY, 12, "bold"))
        self.canvas.create_rectangle(self.width // 2 - 250, 10, self.width // 2 + 250, 50, fill="#15151c", outline="#00e5ff", width=1)
        self.canvas.tag_raise(self.inst_lbl)
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        
        self.top.bind("<Escape>", lambda e: self.close(False, "User cancelled"))

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="#00e5ff", width=2)

    def on_drag(self, event):
        cur_x = event.x
        cur_y = event.y
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event):
        end_x = event.x
        end_y = event.y
        
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        
        w = x2 - x1
        h = y2 - y1
        
        if w > 5 and h > 5:
            try:
                cropped = self.screenshot.crop((x1, y1, x2, y2))
                os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
                cropped.save(self.save_path)
                self.close(True, self.save_path)
            except Exception as e:
                self.close(False, f"儲存錯誤: {e}")
        else:
            self.close(False, "選取範圍過小")

    def close(self, success, msg):
        self.top.destroy()
        self.callback(success, msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = BotGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
