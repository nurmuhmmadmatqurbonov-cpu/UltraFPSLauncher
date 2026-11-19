# -*- coding: utf-8 -*-
"""
UltraFPSLauncher — один файл: сам ставит зависимости, сам собирается в .exe,
запускает Minecraft с ультра-лёгкими настройками.
Запуск: python ultrafps.py
"""

import os
import sys
import time
import zipfile
import threading
import subprocess
from pathlib import Path
import psutil
import requests
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


TEMURIN_21_URL = (
    "https://github.com/adoptium/temurin21-binaries/releases/download/"
    "jdk-21.0.5%2B11/OpenJDK21U-jdk_x64_windows_hotspot_21.0.5_11.zip"
)

ULTRA_LIGHT_OPTIONS = {
    "version": "3955",
    "enableVsync": "false",
    "maxFps": "260",
    "ao": "false",
    "entityShadows": "false",
    "renderClouds": "off",
    "particles": "2",
    "biomeBlendRadius": "0",
    "graphicsPreset": "fast",
    "fullscreen": "true",
    "prioritizeChunkUpdates": "0",
    "mipmapLevels": "0",
    "entityDistanceScaling": "0.5",
    "fov": "0.0",
    "gamma": "1.0",
    "guiScale": "2",
    "narrator": "0",
}

PROFILES = {
    "Старый ноутбук": {"render_distance": 4, "ram_mb": 2048, "resolution": "1024x600"},
    "Баланс":         {"render_distance": 6, "ram_mb": 3072, "resolution": "1280x720"},
    "Ультра FPS":     {"render_distance": 4, "ram_mb": 4096, "resolution": "1280x720"},
}


def build_exe():
    script = Path(__file__).resolve()
    print("Сборка UltraFPSLauncher.exe ...")
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--windowed",
        "--name", "UltraFPSLauncher",
        "--distpath", "dist",
        "--workpath", "build",
        "--specpath", ".",
        str(script),
    ])
    exe = Path("dist") / "UltraFPSLauncher.exe"
    print(f"Готово: {exe.resolve()}")
    return exe


def ask_build_or_run():
    if getattr(sys, "frozen", False):
        return "run"
    root = tk.Tk()
    root.withdraw()
    answer = messagebox.askyesno(
        "UltraFPSLauncher",
        "Собрать UltraFPSLauncher.exe?\n\n"
        "Да — соберёт .exe в папку dist\n"
        "Нет — запустит лаунчер сразу"
    )
    root.destroy()
    return "build" if answer else "run"


def generate_options_txt(minecraft_dir: str, render_distance: int = 4) -> str:
    opts = ULTRA_LIGHT_OPTIONS.copy()
    opts["renderDistance"] = str(render_distance)
    opts["simulationDistance"] = str(max(4, render_distance - 1))
    options_path = os.path.join(minecraft_dir, "options.txt")
    lines = [f"{k}:{v}" for k, v in opts.items()]
    with open(options_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return options_path


def download_and_extract_java(target_dir: str, log=print) -> str:
    target = Path(target_dir)
    java_home = target / "jdk21"
    java_exe = java_home / "bin" / "java.exe"
    if java_exe.exists():
        log(f"Java уже установлена: {java_exe}")
        return str(java_exe)
    target.mkdir(parents=True, exist_ok=True)
    zip_path = target / "jdk21.zip"
    if not zip_path.exists():
        log("Скачивание JDK 21 (Temurin)...")
        resp = requests.get(TEMURIN_21_URL, stream=True, timeout=180)
        resp.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
    log("Распаковка JDK...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(target)
    for item in target.iterdir():
        if item.is_dir() and item.name.startswith("jdk-21") and item != java_home:
            item.rename(java_home)
            break
    return str(java_exe)


def get_jvm_args(ram_mb: int) -> list:
    return [
        f"-Xmx{ram_mb}M",
        f"-Xms{ram_mb}M",
        "-XX:+UseG1GC",
        "-XX:+UnlockExperimentalVMOptions",
        "-XX:+AlwaysPreTouch",
        "-XX:+ParallelRefProcEnabled",
        "-XX:MaxGCPauseMillis=30",
        "-XX:G1NewSizePercent=20",
        "-XX:G1MaxNewSizePercent=40",
        "-Djava.net.preferIPv4Stack=true",
    ]


def boost_java_priority(log=print):
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() in ('javaw.exe', 'java.exe'):
                p = psutil.Process(proc.info['pid'])
                p.nice(psutil.HIGH_PRIORITY_CLASS)
                log(f"Приоритет повышен для PID {proc.info['pid']}")
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def find_minecraft_jar(mc_dir: str, version: str) -> str:
    version_dir = Path(mc_dir) / "versions" / version
    if not version_dir.exists():
        raise FileNotFoundError(f"Версия {version} не найдена: {version_dir}")
    for jar in version_dir.glob("*.jar"):
        return str(jar)
    raise FileNotFoundError(f"Jar не найден для {version}")


class LauncherUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("UltraFPSLauncher")
        self.root.geometry("620x520")
        self.root.resizable(False, False)
        self.mc_dir = tk.StringVar(value=os.path.expanduser("~/.minecraft"))
        self.version = tk.StringVar(value="1.21.4")
        self.username = tk.StringVar(value="Player")
        self.profile = tk.StringVar(value="Старый ноутбук")
        self.close_after_launch = tk.BooleanVar(value=True)
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}
        frm = ttk.LabelFrame(self.root, text="Настройки")
        frm.pack(fill="x", padx=10, pady=8)

        ttk.Label(frm, text="Папка .minecraft:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.mc_dir, width=42).grid(row=0, column=1, **pad)
        ttk.Button(frm, text="...", width=3, command=self._pick_dir).grid(row=0, column=2, **pad)

        ttk.Label(frm, text="Версия:").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.version, width=20).grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(frm, text="Никнейм:").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.username, width=20).grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(frm, text="Профиль:").grid(row=3, column=0, sticky="w", **pad)
        ttk.Combobox(frm, textvariable=self.profile, values=list(PROFILES.keys()),
                     state="readonly", width=18).grid(row=3, column=1, sticky="w", **pad)

        ttk.Checkbutton(frm, text="Закрыть лаунчер после запуска",
                        variable=self.close_after_launch).grid(row=4, column=0, columnspan=3,
                                                               sticky="w", **pad)

        ttk.Button(self.root, text="🚀 Запустить Minecraft",
                   command=self._launch_async).pack(fill="x", padx=10, pady=6)

        self.log_box = tk.Text(self.root, height=14, state="disabled",
                               bg="#111", fg="#0f0", font=("Consolas", 9))
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _pick_dir(self):
        d = filedialog.askdirectory(initialdir=self.mc_dir.get())
        if d:
            self.mc_dir.set(d)

    def log(self, msg: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.root.update_idletasks()

    def _launch_async(self):
        threading.Thread(target=self._launch, daemon=True).start()

    def _launch(self):
        try:
            mc_dir = self.mc_dir.get()
            version = self.version.get()
            username = self.username.get()
            prof = PROFILES[self.profile.get()]

            self.log("=== UltraFPSLauncher ===")
            path = generate_options_txt(mc_dir, prof["render_distance"])
            self.log(f"options.txt обновлён: {path}")

            java_exe = download_and_extract_java(
                str(Path(mc_dir).parent / "ultrafps_java"), log=self.log)
            jar_path = find_minecraft_jar(mc_dir, version)
            self.log(f"Jar: {jar_path}")

            classpath_entries = [jar_path]
            libs_dir = Path(mc_dir) / "libraries"
            if libs_dir.exists():
                for lib in libs_dir.rglob("*.jar"):
                    classpath_entries.append(str(lib))
            classpath = os.pathsep.join(classpath_entries)

            w, h = prof["resolution"].split("x")
            cmd = [
                java_exe,
                *get_jvm_args(prof["ram_mb"]),
                "-cp", classpath,
                "net.minecraft.client.main.Main",
                "--username", username,
                "--version", version,
                "--gameDir", mc_dir,
                "--assetsDir", os.path.join(mc_dir, "assets"),
                "--assetIndex", version,
                "--accessToken", "0",
                "--uuid", "00000000-0000-0000-0000-000000000000",
                "--width", w,
                "--height", h,
            ]

            self.log("Запуск Minecraft...")
            proc = subprocess.Popen(cmd, cwd=mc_dir)

            for _ in range(10):
                if boost_java_priority(log=self.log):
                    break
                time.sleep(0.5)

            if self.close_after_launch.get():
                self.log("Закрытие лаунчера через 3 сек...")
                time.sleep(3)
                os._exit(0)

            proc.wait()

        except Exception as e:
            self.log(f"ОШИБКА: {e}")
            messagebox.showerror("Ошибка", str(e))


def main():
    mode = ask_build_or_run()
    if mode == "build":
        exe = build_exe()
        root = tk.Tk()
        root.withdraw()
        run_now = messagebox.askyesno("Готово", f"Собрано:\n{exe}\n\nЗапустить сейчас?")
        root.destroy()
        if run_now:
            subprocess.Popen([str(exe)])
        return
    root = tk.Tk()
    LauncherUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
