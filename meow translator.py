#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 桌面翻译小宠物（纯中文自动转英文 + 像素圆角版）
# 运行：python desktop_translator_pet.py
# 仅使用 Python 标准库 + Tkinter；翻译需要联网，不需要 API Key。

import json
import os
import platform
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

# 古早电子风配色方案
BG_COLOR = "#5EB77D"          # 主窗口背景：纯正草绿/复古绿
LCD_BG = "#C5E8B7"            # 结果展示框：LCD 液晶屏青绿色
CARD_BG = "#FFFFFF"           # 输入框背景：纯白
BORDER_COLOR = "#1D3B28"      # 像素边框：复古深绿黑框
TEXT_MAIN = "#0D2619"         # 主文字颜色：深墨绿
TEXT_MUTED = "#3D6B50"        # 次要文字/占位符：中深绿
TEXT_LCD = "#143D1A"          # 液晶屏内部字体：黑绿色

# 按钮复古黄绿配色
BTN_GREEN = "#8CE6A6"         # 粘贴按钮：嫩绿
BTN_YELLOW = "#FFD166"        # 复制按钮：亮黄
BTN_LIGHT_GREEN = "#B9FBC0"    # 发音按钮：浅绿
BTN_LEMON = "#FFE66D"         # Google按钮：柠檬黄

HISTORY_FILE = Path.home() / ".translator_pet_history.json"

DEFAULT_HINT_TEXT = "喵~ 准备好翻译了"
LOADING_EMOJI_TEXT = "(o.w.o) 正在翻译中喵..."


def google_translate(text, target="zh-CN"):
    """调用 Google 翻译接口。"""
    params = urllib.parse.urlencode({
        "client": "gtx",
        "sl": "auto",
        "tl": target,
        "dt": "t",
        "q": text
    }, doseq=True)

    url = "https://translate.googleapis.com/translate_a/single?" + params
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def translate_text(text):
    """快速翻译文本（纯中文自动转英文，其余转中文）。"""
    # 过滤空格及常见标点后，判断是否全是中文汉字
    cleaned_text = "".join(c for c in text if not c.isspace() and c not in "，。！？；：‘’“”（）《》【】…—,-.!?")
    is_pure_chinese = bool(cleaned_text) and all('\u4e00' <= c <= '\u9fff' for c in cleaned_text)

    # 纯中文翻译为英文，中英混杂或外文翻译为中文
    target_lang = "en" if is_pure_chinese else "zh-CN"

    data = google_translate(text, target=target_lang)

    main = "".join(
        part[0]
        for part in (data[0] or [])
        if isinstance(part, list)
        and part
        and isinstance(part[0], str)
    ).strip()

    source_lang = (
        data[2]
        if len(data) > 2 and isinstance(data[2], str)
        else ("zh-CN" if is_pure_chinese else "en")
    )

    return main, source_lang


def speak_text(text, language="en"):
    """通过 Google TTS 获取语音并调用系统播放器播放。"""
    params = urllib.parse.urlencode({
        "ie": "UTF-8",
        "client": "tw-ob",
        "tl": language,
        "q": text
    })

    url = "https://translate.google.com/translate_tts?" + params
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req, timeout=15) as response:
        audio = response.read()

    import tempfile
    fd, filename = tempfile.mkstemp(
        suffix=".mp3",
        prefix="translator_pet_"
    )
    os.close(fd)

    Path(filename).write_bytes(audio)

    if platform.system() == "Windows":
        ps = (
            '$p=New-Object System.Windows.Media.MediaPlayer; '
            f'$p.Open([uri]"{filename}"); '
            '$p.Play(); '
            'Start-Sleep -Seconds 15; '
            '$p.Close()'
        )
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-WindowStyle",
                "Hidden",
                "-Command",
                "Add-Type -AssemblyName presentationCore; " + ps
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    elif platform.system() == "Darwin":
        subprocess.Popen(
            ["afplay", filename],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        subprocess.Popen(
            ["mpg123", filename],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )


class PixelRoundedButton(tk.Frame):
    """明显突出的像素风圆角矩形按钮（稳定布局，绝无跑偏变形）"""
    def __init__(self, parent, text="", command=None, bg=BTN_GREEN, fg=TEXT_MAIN):
        super().__init__(parent, bg=BORDER_COLOR, bd=1)
        self.command = command
        self.btn_bg = bg
        self.btn_fg = fg
        self.is_disabled = False

        self.inner = tk.Frame(self, bg=bg)
        self.inner.pack(fill="both", expand=True, padx=1, pady=1)

        # 4角 4x4px 明显梯形像素切角
        self.c_top_left = tk.Frame(self.inner, bg=BORDER_COLOR, width=4, height=4)
        self.c_top_left.place(x=0, y=0)
        self.c_top_right = tk.Frame(self.inner, bg=BORDER_COLOR, width=4, height=4)
        self.c_top_right.place(relx=1.0, y=0, x=-4)
        self.c_bot_left = tk.Frame(self.inner, bg=BORDER_COLOR, width=4, height=4)
        self.c_bot_left.place(x=0, rely=1.0, y=-4)
        self.c_bot_right = tk.Frame(self.inner, bg=BORDER_COLOR, width=4, height=4)
        self.c_bot_right.place(relx=1.0, rely=1.0, x=-4, y=-4)

        # 切角内部补点，防露空
        tk.Frame(self.inner, bg=BG_COLOR, width=3, height=3).place(x=0, y=0)
        tk.Frame(self.inner, bg=BG_COLOR, width=3, height=3).place(relx=1.0, y=0, x=-3)
        tk.Frame(self.inner, bg=BG_COLOR, width=3, height=3).place(x=0, rely=1.0, y=-3)
        tk.Frame(self.inner, bg=BG_COLOR, width=3, height=3).place(relx=1.0, rely=1.0, x=-3, y=-3)

        tk.Frame(self.inner, bg=BORDER_COLOR, width=2, height=2).place(x=1, y=1)
        tk.Frame(self.inner, bg=BORDER_COLOR, width=2, height=2).place(relx=1.0, y=1, x=-3)
        tk.Frame(self.inner, bg=BORDER_COLOR, width=2, height=2).place(x=1, rely=1.0, y=-3)
        tk.Frame(self.inner, bg=BORDER_COLOR, width=2, height=2).place(relx=1.0, rely=1.0, x=-3, y=-3)

        self.label = tk.Label(
            self.inner,
            text=text,
            bg=bg,
            fg=fg,
            font=("Microsoft YaHei UI", 11, "bold")
        )
        self.label.pack(fill="both", expand=True, ipady=4)

        self.bind_events(self)
        self.bind_events(self.inner)
        self.bind_events(self.label)

    def bind_events(self, widget):
        widget.bind("<Button-1>", self._on_click)

    def set_state(self, state, text=None):
        if text:
            self.label.config(text=text)
        if state == "disabled":
            self.is_disabled = True
            self.inner.config(bg="#A3C4AC")
            self.label.config(bg="#A3C4AC", fg="#708A77")
        else:
            self.is_disabled = False
            self.inner.config(bg=self.btn_bg)
            self.label.config(bg=self.btn_bg, fg=self.btn_fg)

    def _on_click(self, event):
        if not self.is_disabled and self.command:
            self.command()


class TranslatorPet:

    def __init__(self, root):
        self.root = root

        self.root.title("喵喵翻译")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BORDER_COLOR)
        self.root.geometry("380x290+80+120")

        self.history = self.load_history()
        self.busy = False
        self.result_text = ""
        self.source_text = ""
        self.drag = None
        self.compact = False

        self.main_container = tk.Frame(self.root, bg=BG_COLOR)
        self.main_container.pack(fill="both", expand=True, padx=2, pady=2)

        self.build_ui()

    def load_history(self):
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []

    def save_history(self):
        try:
            HISTORY_FILE.write_text(
                json.dumps(self.history[-500:], ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    def draw_cat_icon(self, canvas):
        canvas.delete("all")
        c = TEXT_MAIN
        e = TEXT_MAIN

        canvas.create_polygon(3, 12, 8, 2, 13, 12, outline=c, fill=BG_COLOR, width=1)
        canvas.create_polygon(17, 12, 22, 2, 27, 12, outline=c, fill=BG_COLOR, width=1)
        canvas.create_oval(2, 8, 28, 26, outline=c, fill=BG_COLOR, width=1)
        canvas.create_oval(8, 14, 11, 17, fill=e, outline="")
        canvas.create_oval(19, 14, 22, 17, fill=e, outline="")
        canvas.create_line(13, 20, 15, 22, 17, 20, fill=c, width=1)
        canvas.create_line(0, 15, 6, 17, fill=c, width=1)
        canvas.create_line(0, 20, 6, 20, fill=c, width=1)
        canvas.create_line(30, 15, 24, 17, fill=c, width=1)
        canvas.create_line(30, 20, 24, 20, fill=c, width=1)

    def build_ui(self):
        # 1. 顶部标题栏
        top = tk.Frame(self.main_container, bg=BG_COLOR)
        top.pack(side="top", fill="x", padx=10, pady=(6, 2))
        self.bind_drag(top)

        cat_canvas = tk.Canvas(top, width=30, height=28, bg=BG_COLOR, highlightthickness=0, bd=0)
        cat_canvas.pack(side="left", padx=(0, 4))
        self.draw_cat_icon(cat_canvas)
        self.bind_drag(cat_canvas)

        self.title_label = tk.Label(
            top,
            text="喵  喵  翻  译",
            bg=BG_COLOR,
            fg=TEXT_MAIN,
            font=("Microsoft YaHei UI", 12, "bold"),
            cursor="hand2"
        )
        self.title_label.pack(side="left")
        self.title_label.bind("<Button-1>", self.on_title_click)

        close_btn = tk.Label(top, text="✕", bg=BG_COLOR, fg=TEXT_MAIN, font=("Arial", 12, "bold"), cursor="hand2")
        close_btn.pack(side="right", padx=(6, 0))
        close_btn.bind("<Button-1>", lambda e: self.close())

        min_btn = tk.Label(top, text="━", bg=BG_COLOR, fg=TEXT_MAIN, font=("Arial", 10, "bold"), cursor="hand2")
        min_btn.pack(side="right", padx=4)
        min_btn.bind("<Button-1>", lambda e: self.toggle_compact())

        # 2. 主内容框
        self.content_frame = tk.Frame(self.main_container, bg=BG_COLOR)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        # 底部栏
        bottom = tk.Frame(self.content_frame, bg=BG_COLOR)
        bottom.pack(side="bottom", fill="x", pady=(4, 0))

        self.status = tk.Label(
            bottom,
            text="古早电子风 · 本地掌上助手",
            bg=BG_COLOR,
            fg=TEXT_MAIN,
            font=("Microsoft YaHei UI", 9, "bold")
        )
        self.status.pack(side="left")

        history_btn = tk.Label(
            bottom,
            text="历史记录 📜",
            bg=BG_COLOR,
            fg=TEXT_MAIN,
            font=("Microsoft YaHei UI", 10, "bold", "underline"),
            cursor="hand2"
        )
        history_btn.pack(side="right")
        history_btn.bind("<Button-1>", lambda e: self.show_history())

        # 输入框部分
        input_border = tk.Frame(self.content_frame, bg=BORDER_COLOR, bd=1)
        input_border.pack(side="top", fill="x", pady=(2, 4))

        input_row = tk.Frame(input_border, bg=CARD_BG)
        input_row.pack(fill="x", padx=1, pady=1)

        self.entry = tk.Entry(
            input_row,
            font=("Microsoft YaHei UI", 11),
            relief="flat",
            bg=CARD_BG,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            bd=0
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(8, 4), ipady=5)
        self.entry.insert(0, "输入单词或句子…")
        self.entry.config(fg=TEXT_MUTED)

        self.entry.bind("<FocusIn>", self.clear_placeholder)
        self.entry.bind("<FocusOut>", self.restore_placeholder)
        self.entry.bind("<KeyRelease>", self.on_entry_key_release)
        self.entry.bind("<Return>", lambda event: self.start_translate())

        self.clear_btn = tk.Label(
            input_row,
            text="✕",
            bg=CARD_BG,
            fg=TEXT_MUTED,
            font=("Arial", 11, "bold"),
            cursor="hand2"
        )
        self.clear_btn.bind("<Button-1>", lambda e: self.clear_input())

        # 3. 按钮区域
        btn_frame = tk.Frame(self.content_frame, bg=BG_COLOR)
        btn_frame.pack(side="top", fill="x", pady=(0, 4))

        for i in range(4):
            btn_frame.columnconfigure(i, weight=1, uniform="btn_col")

        self.btn_paste = PixelRoundedButton(
            btn_frame, text="粘贴", command=self.paste_and_translate, bg=BTN_GREEN, fg=TEXT_MAIN
        )
        self.btn_paste.grid(row=0, column=0, padx=1, sticky="ew")

        self.btn_copy = PixelRoundedButton(
            btn_frame, text="复制", command=self.copy_result, bg=BTN_YELLOW, fg=TEXT_MAIN
        )
        self.btn_copy.grid(row=0, column=1, padx=1, sticky="ew")

        self.btn_speak = PixelRoundedButton(
            btn_frame, text="发音", command=self.play_pronunciation, bg=BTN_LIGHT_GREEN, fg=TEXT_MAIN
        )
        self.btn_speak.grid(row=0, column=2, padx=1, sticky="ew")

        self.btn_google = PixelRoundedButton(
            btn_frame, text="Google", command=self.open_google, bg=BTN_LEMON, fg=TEXT_MAIN
        )
        self.btn_google.grid(row=0, column=3, padx=1, sticky="ew")

        # 4. 译文输出 Display
        output_border = tk.Frame(self.content_frame, bg=BORDER_COLOR, bd=1)
        output_border.pack(side="top", fill="both", expand=True, pady=(0, 2))

        output_inner = tk.Frame(output_border, bg=LCD_BG)
        output_inner.pack(fill="both", expand=True, padx=1, pady=1)

        self.output = tk.Text(
            output_inner,
            bg=LCD_BG,
            fg=TEXT_LCD,
            relief="flat",
            bd=0,
            wrap="word",
            font=("Microsoft YaHei UI", 11, "bold"),
            selectbackground="#FFFFFF",
            selectforeground=TEXT_LCD
        )
        self.output.pack(fill="both", expand=True, padx=6, pady=6)

        self.set_output_text(DEFAULT_HINT_TEXT)

    def set_output_text(self, text):
        """写入译文文本"""
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.config(state="disabled")

    def bind_drag(self, widget):
        widget.bind("<ButtonPress-1>", self.drag_start)
        widget.bind("<B1-Motion>", self.drag_move)

    def drag_start(self, event):
        self.drag = (
            event.x_root - self.root.winfo_x(),
            event.y_root - self.root.winfo_y()
        )

    def drag_move(self, event):
        if self.drag:
            x = event.x_root - self.drag[0]
            y = event.y_root - self.drag[1]
            self.root.geometry(f"+{x}+{y}")

    def on_title_click(self, event):
        if self.compact:
            self.toggle_compact()

    def clear_placeholder(self, _event=None):
        if self.entry.get() == "输入单词或句子…":
            self.entry.delete(0, "end")
            self.entry.config(fg=TEXT_MAIN)

    def restore_placeholder(self, _event=None):
        if not self.entry.get().strip():
            self.entry.delete(0, "end")
            self.entry.insert(0, "输入单词或句子…")
            self.entry.config(fg=TEXT_MUTED)
            self.clear_btn.pack_forget()

    def on_entry_key_release(self, _event=None):
        val = self.entry.get()
        if val and val != "输入单词或句子…":
            self.clear_btn.pack(side="right", padx=(0, 6))
        else:
            self.clear_btn.pack_forget()

    def clear_input(self):
        self.entry.delete(0, "end")
        self.clear_btn.pack_forget()
        self.entry.focus_set()
        self.result_text = ""
        self.source_text = ""
        self.set_output_text(DEFAULT_HINT_TEXT)
        self.status.config(text="已清空")

    def paste_and_translate(self):
        try:
            clipboard_text = self.root.clipboard_get().strip()
        except Exception:
            clipboard_text = ""

        if not clipboard_text:
            self.status.config(text="剪贴板中没有文本喵")
            return

        self.entry.delete(0, "end")
        self.entry.insert(0, clipboard_text)
        self.entry.config(fg=TEXT_MAIN)
        self.clear_btn.pack(side="right", padx=(0, 6))

        self.start_translate()

    def start_translate(self):
        text = self.entry.get().strip()

        if not text or text == "输入单词或句子…" or self.busy:
            return

        self.busy = True
        self.btn_paste.set_state("disabled", "翻译中")
        self.set_output_text(LOADING_EMOJI_TEXT)

        threading.Thread(
            target=self.translate_worker,
            args=(text,),
            daemon=True
        ).start()

    def translate_worker(self, text):
        try:
            meaning, source_lang = translate_text(text)

            if not meaning:
                raise ValueError("没有获取到译文")

            self.root.after(
                0,
                lambda: self.show_translation(text, meaning, source_lang)
            )

        except Exception as exc:
            self.root.after(
                0,
                lambda message=str(exc): self.show_error(message)
            )

    def show_translation(self, original, meaning, source_lang="en"):
        self.busy = False
        self.btn_paste.set_state("normal", "粘贴")

        self.result_text = meaning
        self.source_text = original
        self.source_lang = source_lang or "en"

        self.set_output_text(meaning)
        self.status.config(text="翻译成功 ✓")

        self.history.insert(
            0,
            {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": original,
                "translations": [meaning]
            }
        )
        self.history = self.history[:500]
        self.save_history()

    def show_error(self, message):
        self.busy = False
        self.btn_paste.set_state("normal", "粘贴")
        self.set_output_text("翻译失败，请检查网络连接重试。")
        self.status.config(text=("失败：" + message)[:35])

    def copy_result(self):
        source = self.source_text or self.entry.get().strip()
        if source == "输入单词或句子…":
            source = ""

        result = self.result_text

        if source and result:
            combined_text = f"{source} {result}"
        elif result:
            combined_text = result
        elif source:
            combined_text = source
        else:
            self.status.config(text="没有可复制的内容喵")
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(combined_text)
        self.root.update()

        self.status.config(text="原文和译文已复制 ✓")

    def play_pronunciation(self):
        text = self.source_text or self.entry.get().strip()
        if text == "输入单词或句子…":
            text = ""

        if not text:
            self.status.config(text="请先输入单词喵")
            return

        self.status.config(text="正在获取发音…")

        def worker():
            try:
                speak_text(text, getattr(self, "source_lang", "en") or "en")
                self.root.after(0, lambda: self.status.config(text="播放中 🔊"))
            except Exception as exc:
                msg = str(exc)
                self.root.after(0, lambda: self.status.config(text=("发音失败：" + msg)[:30]))

        threading.Thread(target=worker, daemon=True).start()

    def open_google(self):
        text = self.entry.get().strip()
        if text == "输入单词或句子…":
            text = ""

        url = "https://translate.google.com/?sl=auto&tl=zh-CN&text=" + urllib.parse.quote(text) + "&op=translate"
        webbrowser.open(url)

    def show_history(self):
        win = tk.Toplevel(self.root)
        win.title("翻译历史")
        win.geometry("540x390+180+120")
        win.configure(bg=BORDER_COLOR)
        win.attributes("-topmost", True)

        container = tk.Frame(win, bg=BG_COLOR)
        container.pack(fill="both", expand=True, padx=2, pady=2)

        head = tk.Frame(container, bg=BG_COLOR)
        head.pack(fill="x", padx=14, pady=10)

        tk.Label(
            head,
            text="📜 翻译历史记录",
            bg=BG_COLOR,
            fg=TEXT_MAIN,
            font=("Microsoft YaHei UI", 12, "bold")
        ).pack(side="left")

        PixelRoundedButton(
            head,
            text="清空",
            command=lambda: self.clear_history_direct(win),
            bg=BTN_YELLOW,
            fg=TEXT_MAIN
        ).pack(side="right")

        body = tk.Frame(container, bg=BG_COLOR)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        scroll = tk.Scrollbar(body, bg=LCD_BG, troughcolor=BG_COLOR, bd=0)
        scroll.pack(side="right", fill="y")

        listing = tk.Listbox(
            body,
            font=("Microsoft YaHei UI", 11),
            bg=LCD_BG,
            fg=TEXT_LCD,
            selectbackground=BORDER_COLOR,
            selectforeground="#FFFFFF",
            relief="flat",
            bd=0,
            yscrollcommand=scroll.set,
            activestyle="none"
        )
        listing.pack(side="left", fill="both", expand=True)
        scroll.config(command=listing.yview)

        for item in self.history:
            translations = item.get("translations", [])
            listing.insert(
                "end",
                f"{item.get('time', '')[5:16]} | {item.get('source', '')} -> {translations[0] if translations else ''}"
            )

    def clear_history_direct(self, parent):
        self.history = []
        self.save_history()
        parent.destroy()
        self.show_history()

    def toggle_compact(self):
        if self.compact:
            self.content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
            self.root.geometry("380x290")
            self.compact = False
        else:
            self.content_frame.pack_forget()
            self.root.geometry("170x44")
            self.compact = True

    def close(self):
        self.save_history()
        self.root.destroy()


def enable_startup():
    script = Path(__file__).resolve()
    system = platform.system()

    if system == "Windows":
        folder = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup"
        folder.mkdir(parents=True, exist_ok=True)
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if not pythonw.exists():
            pythonw = Path(sys.executable)
        target = folder / "TranslatorPet.bat"
        target.write_text(f'@echo off\nstart "" "{pythonw}" "{script}"\n', encoding="utf-8")
    elif system == "Darwin":
        folder = Path.home() / "Library/LaunchAgents"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "com.translator.pet.plist"
        content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<plist version="1.0"><dict>\n'
            '<key>Label</key><string>com.translator.pet</string>\n'
            f'<key>ProgramArguments</key><array><string>{sys.executable}</string><string>{script}</string></array>\n'
            '<key>RunAtLoad</key><true/>\n</dict></plist>'
        )
        target.write_text(content, encoding="utf-8")
    else:
        folder = Path.home() / ".config/autostart"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "translator-pet.desktop"
        target.write_text(
            f'[Desktop Entry]\nType=Application\nName=Translator Pet\nExec={sys.executable} "{script}"\nX-GNOME-Autostart-enabled=true\n',
            encoding="utf-8"
        )
    return target


def main():
    if "--enable-startup" in sys.argv:
        print("开机自启已设置：", enable_startup())
        return

    root = tk.Tk()
    app = TranslatorPet(root)

    menu = tk.Menu(root, tearoff=0, bg=LCD_BG, fg=TEXT_LCD, activebackground=BORDER_COLOR, activeforeground="#FFFFFF")
    menu.add_command(
        label="设置开机自启",
        command=lambda: messagebox.showinfo("开机自启", "已创建启动项：\n" + str(enable_startup()))
    )
    menu.add_command(label="退出", command=app.close)

    root.bind("<Button-3>", lambda event: menu.tk_popup(event.x_root, event.y_root))
    root.mainloop()


if __name__ == "__main__":
    main()