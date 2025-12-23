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
def build_common_opts(cookies_path=None):
    opts = {
        "quiet": False,
        "noprogress": False,
        "progress_with_newline": True,
        "ffmpeg_location": FFMPEG_BIN if os.path.exists(FFMPEG_EXE) else None,
        "retries": 10,
        "socket_timeout": 20,
        "geo_bypass": True,
    }
    if cookies_path:
        opts["cookiefile"] = cookies_path
    return opts

# =========================
# APP
# =========================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouDownload — Selector de calidad")
        self.geometry("820x520")
        self.resizable(False, False)

        self.url_var = tk.StringVar()
        self.save_dir = tk.StringVar()
        self.cookies_path = tk.StringVar()

        self.quality_var = tk.StringVar(value="best")
        self.available_qualities = {}

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
        self.info_lbl = ttk.Label(self, text="Información del video aparecerá aquí", wraplength=780)
        self.info_lbl.pack(pady=8)

        # Calidad
        qf = ttk.Frame(self)
        qf.pack(pady=6)

        ttk.Label(qf, text="Calidad:").pack(side="left")
        self.quality_combo = ttk.Combobox(
            qf,
            textvariable=self.quality_var,
            state="readonly",
            width=25
        )
        self.quality_combo.pack(side="left", padx=6)

        ttk.Button(self, text="Descargar", command=self.download).pack(pady=14)

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

                # Extraer calidades únicas
                qualities = {}
                max_h = 0
                max_fps = 0
                codec = None

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

                labels = ["best (automático)"] + [
                    f"{h}p" for h in self.available_qualities
                ]

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

    def download(self):
        url = self.url_var.get().strip()
        outdir = self.save_dir.get().strip()
        cookies = self.cookies_path.get().strip() or None

        if not url or not outdir:
            return

        choice = self.quality_var.get()

        if choice == "best (automático)":
            fmt = "best"
        else:
            h = int(choice.replace("p", ""))
            fmt = f"bestvideo[height={h}]+bestaudio/best"

        def worker():
            try:
                opts = build_common_opts(cookies)
                opts["outtmpl"] = os.path.join(outdir, "%(title)s.%(ext)s")
                opts["format"] = fmt

                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])

                self.after(0, lambda: messagebox.showinfo("Listo", "Descarga completada"))

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    App().mainloop()
