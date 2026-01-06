# =========================
# IMPORTS
# =========================
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp

# =========================
# FFmpeg
# =========================
BASE_DIR = os.path.dirname(__file__)
FFMPEG_BIN = os.path.join(BASE_DIR, "ffmpeg-8.0-full_build", "bin")
FFMPEG_EXE = os.path.join(FFMPEG_BIN, "ffmpeg.exe")

# =========================
# yt-dlp OPTIONS (CLI-LIKE)
# =========================
def build_common_opts(cookies_path=None, progress_hook=None):
    opts = {
        "quiet": True,
        "noprogress": True,
        "ffmpeg_location": FFMPEG_BIN if os.path.exists(FFMPEG_EXE) else None,
        "retries": 10,
        "socket_timeout": 20,
        "geo_bypass": True,
    }
    if cookies_path:
        opts["cookiefile"] = cookies_path
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    return opts

# =========================
# APP
# =========================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouDownload — completo")
        self.geometry("860x640")
        self.resizable(False, False)

        self.url_var = tk.StringVar()
        self.save_dir = tk.StringVar()
        self.cookies_path = tk.StringVar()

        self.quality_var = tk.StringVar(value="best")
        self.mode_var = tk.StringVar(value="video_audio")  # video_audio | video | audio

        self.available_qualities = {}

        # progreso
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_text = tk.StringVar(value="En espera…")

        self._build_ui()

    # =========================
    # UI
    # =========================
    def _build_ui(self):
        frm = ttk.Frame(self)
        frm.pack(padx=12, pady=12, fill="x")

        ttk.Label(frm, text="URL").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.url_var, width=70).grid(row=0, column=1, columnspan=3)

        ttk.Label(frm, text="Destino").grid(row=1, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.save_dir, width=55).grid(row=1, column=1)
        ttk.Button(frm, text="Seleccionar", command=self.choose_dir).grid(row=1, column=2)

        ttk.Label(frm, text="Cookies (opcional)").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.cookies_path, width=55).grid(row=2, column=1)
        ttk.Button(frm, text="Buscar", command=self.choose_cookies).grid(row=2, column=2)

        ttk.Button(frm, text="Analizar video", command=self.analyze).grid(row=3, column=1, pady=10)

        # Info
        self.info_lbl = ttk.Label(self, text="Información del video aparecerá aquí", wraplength=820)
        self.info_lbl.pack(pady=8)

        # ---- MODO ----
        mf = ttk.LabelFrame(self, text="Tipo de descarga")
        mf.pack(pady=6)

        ttk.Radiobutton(mf, text="🎬 Video + audio", variable=self.mode_var, value="video_audio").pack(anchor="w")
        ttk.Radiobutton(mf, text="🎥 Solo video", variable=self.mode_var, value="video").pack(anchor="w")
        ttk.Radiobutton(mf, text="🎧 Solo audio", variable=self.mode_var, value="audio").pack(anchor="w")

        # ---- CALIDAD ----
        qf = ttk.Frame(self)
        qf.pack(pady=6)

        ttk.Label(qf, text="Calidad de video:").pack(side="left")
        self.quality_combo = ttk.Combobox(
            qf,
            textvariable=self.quality_var,
            state="readonly",
            width=25
        )
        self.quality_combo.pack(side="left", padx=6)

        ttk.Button(self, text="Descargar", command=self.download).pack(pady=10)

        # ---- PROGRESO ----
        ttk.Progressbar(self, variable=self.progress_var, maximum=100, length=800).pack(pady=6)
        ttk.Label(self, textvariable=self.progress_text).pack()

    # =========================
    # HANDLERS
    # =========================
    def choose_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.save_dir.set(d)

    def choose_cookies(self):
        f = filedialog.askopenfilename(filetypes=[("TXT", "*.txt")])
        if f:
            self.cookies_path.set(f)

    def analyze(self):
        url = self.url_var.get().strip()
        if not url:
            return

        cookies = self.cookies_path.get().strip() or None

        def worker():
            try:
                opts = build_common_opts(cookies)
                opts["skip_download"] = True

                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                formats = info.get("formats", [])

                qualities = {}
                max_h, max_fps, codec = 0, 0, None

                for f in formats:
                    if f.get("vcodec") == "none":
                        continue
                    h = f.get("height")
                    if h:
                        qualities[h] = f
                        max_h = max(max_h, h)
                        max_fps = max(max_fps, int(f.get("fps") or 0))
                        codec = codec or f.get("vcodec")

                self.available_qualities = dict(sorted(qualities.items(), reverse=True))
                labels = ["best (automático)"] + [f"{h}p" for h in self.available_qualities]

                self.after(0, lambda: self.quality_combo.configure(values=labels))
                self.after(0, lambda: self.quality_combo.current(0))

                title = info.get("title", "Desconocido")
                text = (
                    f"🎬 {title}\n"
                    f"📺 Resolución máxima: {max_h}p\n"
                    f"🎞 FPS máximo: {max_fps}\n"
                    f"🎥 Codec: {codec}"
                )
                self.after(0, lambda: self.info_lbl.config(text=text))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    # =========================
    # DESCARGA
    # =========================
    def download(self):
        url = self.url_var.get().strip()
        outdir = self.save_dir.get().strip()
        cookies = self.cookies_path.get().strip() or None

        if not url or not outdir:
            return

        mode = self.mode_var.get()
        quality = self.quality_var.get()

        # ---- construir formato ----
        if mode == "audio":
            fmt = "bestaudio/best"
        else:
            if quality == "best (automático)":
                base = "bestvideo"
            else:
                h = int(quality.replace("p", ""))
                base = f"bestvideo[height={h}]"

            if mode == "video":
                fmt = f"{base}/bestvideo"
            else:
                fmt = f"{base}+bestaudio/best"

        self.progress_var.set(0)
        self.progress_text.set("Iniciando descarga…")

        def progress_hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                if total:
                    percent = downloaded / total * 100
                    self.after(0, lambda: self.progress_var.set(percent))
                    txt = f"Descargando… {percent:.1f}%"
                    self.after(0, lambda: self.progress_text.set(txt))
            elif d["status"] == "finished":
                self.after(0, lambda: self.progress_text.set("Procesando…"))

        def worker():
            try:
                opts = build_common_opts(cookies, progress_hook)
                opts["outtmpl"] = os.path.join(outdir, "%(title)s.%(ext)s")
                opts["format"] = fmt

                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])

                self.after(0, lambda: self.progress_var.set(100))
                self.after(0, lambda: self.progress_text.set("Completado ✅"))
                self.after(0, lambda: messagebox.showinfo("Listo", "Descarga completada"))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    App().mainloop()
