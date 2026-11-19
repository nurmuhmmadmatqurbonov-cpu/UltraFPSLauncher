# -*- coding: utf-8 -*-
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import psutil

# Импортируем библиотеку для автоскачивания и запуска
try:
    from easy_mc_launcher import EasyLauncher, SettingsManager
except ImportError:
    messagebox.showerror("Ошибка", "Библиотека easy-mc-launcher не установлена. Проверьте build.yml")
    sys.exit(1)

class NovaLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("NovaLauncher — Full Edition")
        self.root.geometry("750x600")
        self.root.configure(bg="#1e1e1e")
        
        self.mc_dir = tk.StringVar(value=os.path.expanduser("~/.minecraft"))
        self.version = tk.StringVar(value="1.21.4")
        self.username = tk.StringVar(value="Player")
        self.profile = tk.StringVar(value="Слабый ПК")
        
        self.profiles = {
            "Слабый ПК": {"ram": "2G", "res": {"width": 1024, "height": 600}},
            "Средний ПК": {"ram": "4G", "res": {"width": 1280, "height": 720}},
            "Мощный ПК": {"ram": "8G", "res": {"width": 1920, "height": 1080}},
        }
        
        self.build_ui()

    def build_ui(self):
        frame = ttk.LabelFrame(self.root, text="Настройки")
        frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(frame, text="Папка .minecraft:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.mc_dir, width=50).grid(row=0, column=1, pady=5)
        
        ttk.Label(frame, text="Версия:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.version, width=20).grid(row=1, column=1, sticky="w", pady=5)
        
        ttk.Label(frame, text="Никнейм:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.username, width=20).grid(row=2, column=1, sticky="w", pady=5)
        
        ttk.Label(frame, text="Профиль:").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Combobox(frame, textvariable=self.profile, values=list(self.profiles.keys()), state="readonly").grid(row=3, column=1, sticky="w", pady=5)

        ttk.Button(self.root, text="🚀 Скачать и Запустить", command=self.launch_game).pack(fill="x", padx=10, pady=5)
        
        self.log_box = tk.Text(self.root, height=15, bg="#000", fg="#0f0", font=("Consolas", 9))
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

    def log(self, text):
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.root.update()

    def launch_game(self):
        # Запускаем в отдельном потоке, чтобы окно не зависало
        threading.Thread(target=self._launch_thread, daemon=True).start()

    def _launch_thread(self):
        try:
            self.log("=== NovaLauncher Full ===")
            
            # Очистка памяти от зависших процессов Java
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and 'javaw' in proc.info['name'].lower():
                    self.log("Minecraft уже запущен! Закройте игру перед новым запуском.")
                    return

            prof = self.profiles[self.profile.get()]
            
            self.log("Настройка параметров...")
            settings = SettingsManager()
            settings.set("username", self.username.get())
            settings.set("ram_max", prof["ram"])
            settings.set("resolution", prof["res"])
            
            self.log(f"Проверка и скачивание версии {self.version.get()} (если нужно)...")
            self.log("Это может занять несколько минут при первом запуске.")
            
            # Запуск через библиотеку
            launcher = EasyLauncher()
            
            # Эта функция скачает игру, Java и запустит её
            launcher.launch(self.version.get(), settings)
            
            self.log("Игра запущена! Лаунчер можно свернуть.")
            
        except Exception as e:
            self.log(f"ОШИБКА: {e}")
            messagebox.showerror("Ошибка", f"Не удалось запустить:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = NovaLauncher(root)
    root.mainloop()
