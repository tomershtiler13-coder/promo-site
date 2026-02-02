import json
import os
import re
import shutil
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import sys

try:
    from PIL import Image
    PIL_OK = True
except Exception:
    PIL_OK = False


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-") or "event"


def validate_date(date_str: str) -> str:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise ValueError("תאריך לא תקין. השתמש בפורמט YYYY-MM-DD (למשל 2026-03-07).")


def validate_time(time_str: str) -> str:
    if not time_str.strip():
        return "00:00"
    if not re.fullmatch(r"\d{2}:\d{2}", time_str.strip()):
        raise ValueError("שעה לא תקינה. השתמש בפורמט HH:MM (למשל 22:00).")
    hh, mm = map(int, time_str.split(":"))
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise ValueError("שעה לא תקינה (טווח).")
    return time_str.strip()


def find_repo_root(start: Path) -> Path | None:
    p = start.resolve()
    for _ in range(20):
        if (p / ".git").exists():
            return p
        p = p.parent
    return None

def app_start_dir() -> Path:
    # כשמריצים מתוך .app של PyInstaller, sys.executable נמצא בתוך ...EventFolderMaker.app/Contents/MacOS/...
    exe = Path(sys.executable).resolve()
    # exe.parents[3] לרוב זה התיקייה שמכילה את ה-.app (למשל repo/tools/)
    if len(exe.parents) > 3:
        return exe.parents[3]
    return Path.cwd()

def default_events_root() -> str:
    root = find_repo_root(app_start_dir())
    if root:
        return str(root / "events")
    # fallback אם לא מצא repo
    return os.path.join(os.path.expanduser("~"), "Desktop", "events")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Event Folder Maker")
        self.geometry("520x700")
        self.minsize(520, 650)
        self.resizable(True, True)
        



        self.image_path = tk.StringVar(value="")

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 14, "pady": 7}

        header = tk.Label(self, text="הוספת אירוע (יוצר תיקייה + meta.json + cover.jpg)", font=("Arial", 13, "bold"))
        header.pack(pady=14)

        frm = tk.Frame(self)
        frm.pack(fill="x", **pad)

        self.title_var = self._row(frm, "שם האירוע*", "")
        self.date_var = self._row(frm, "תאריך* (YYYY-MM-DD)", datetime.now().strftime("%Y-%m-%d"))
        self.time_var = self._row(frm, "שעה* (HH:MM)", "22:00")
        self.loc_var = self._row(frm, "מיקום", "")
        self.ticket_var = self._row(frm, "לינק לכרטיסים*", "")
        self.coupon_var = self._row(frm, "קופון", "")
        self.desc_var = self._row(frm, "תיאור קצר", "", multiline=True)

        imgfrm = tk.Frame(self)
        imgfrm.pack(fill="x", **pad)

        tk.Label(imgfrm, text="תמונה/פלייר*").grid(row=0, column=0, sticky="w")
        tk.Entry(imgfrm, textvariable=self.image_path, width=44).grid(row=1, column=0, sticky="w", pady=4)
        tk.Button(imgfrm, text="בחר קובץ…", command=self.pick_image).grid(row=1, column=1, padx=8)

        outfrm = tk.Frame(self)
        outfrm.pack(fill="x", **pad)
        tk.Label(outfrm, text="איפה ליצור את התיקיות").grid(row=0, column=0, sticky="w")
        self.out_root = tk.StringVar(value=default_events_root())
        tk.Entry(outfrm, textvariable=self.out_root, width=44).grid(row=1, column=0, sticky="w", pady=4)
        tk.Button(outfrm, text="בחר…", command=self.pick_out_root).grid(row=1, column=1, padx=8)

        btnfrm = tk.Frame(self)
        btnfrm.pack(fill="x", padx=14, pady=16)
        tk.Button(btnfrm, text="צור תיקיית אירוע", font=("Arial", 12, "bold"), command=self.create_event).pack(fill="x", pady=10)

        hint = tk.Label(self, text="* שדות חובה. ייצא בתיקייה: Desktop/events/YYYY-MM-DD-slug/", fg="#666")
        hint.pack(pady=6)

        if not PIL_OK:
            warn = tk.Label(self, text="הערה: Pillow לא מותקן, אז התמונה תועתק כמו שהיא (עדיין בשם cover.jpg).",
                            fg="#a00")
            warn.pack(pady=4)

    def _row(self, parent, label, default, multiline=False):
        frame = tk.Frame(parent)
        frame.pack(fill="x", pady=4)
        tk.Label(frame, text=label).pack(anchor="w")
        if multiline:
            txt = tk.Text(frame, height=4, width=58)
            txt.insert("1.0", default)
            txt.pack()
            # return a getter wrapper
            class TVar:
                def get(self_inner): return txt.get("1.0", "end").strip()
                def set(self_inner, v):
                    txt.delete("1.0", "end")
                    txt.insert("1.0", v)
            return TVar()
        else:
            var = tk.StringVar(value=default)
            tk.Entry(frame, textvariable=var, width=60).pack()
            return var

    def pick_image(self):
        p = filedialog.askopenfilename(
            title="בחר פלייר/תמונה",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.heic"), ("All files", "*.*")]
        )
        if p:
            self.image_path.set(p)

    def pick_out_root(self):
        d = filedialog.askdirectory(title="בחר תיקיית יעד (root)")
        if d:
            self.out_root.set(d)

    def create_event(self):
        try:
            title = self.title_var.get().strip()
            if not title:
                raise ValueError("חסר שם אירוע.")
            date = validate_date(self.date_var.get().strip())
            time_str = validate_time(self.time_var.get().strip())

            ticket_url = self.ticket_var.get().strip()
            if not ticket_url:
                raise ValueError("חסר לינק לכרטיסים.")

            img = self.image_path.get().strip()
            if not img or not os.path.isfile(img):
                raise ValueError("חובה לבחור תמונה קיימת.")

            location = self.loc_var.get().strip()
            coupon = self.coupon_var.get().strip()
            description = self.desc_var.get().strip() if hasattr(self.desc_var, "get") else ""

            folder = f"{date}-{slugify(title)}"
            out_dir = os.path.join(self.out_root.get().strip() or default_events_root(), folder)
            os.makedirs(out_dir, exist_ok=True)

            meta = {
                "title": title,
                "date": date,
                "time": time_str,
                "location": location,
                "description": description,
                "ticket_url": ticket_url,
                "promoter_url": "",
                "coupon_code": coupon,
                "image": "cover.jpg"
            }

            with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

            cover_path = os.path.join(out_dir, "cover.jpg")

            if PIL_OK:
                try:
                    im = Image.open(img)
                    im = im.convert("RGB")
                    im.save(cover_path, format="JPEG", quality=92, optimize=True)
                except Exception:
                    shutil.copyfile(img, cover_path)
            else:
                shutil.copyfile(img, cover_path)

            messagebox.showinfo("הצלחה ✅", f"נוצר אירוע:\n{out_dir}\n\nבתיקייה יש meta.json + cover.jpg")
        except Exception as e:
            messagebox.showerror("שגיאה", str(e))


if __name__ == "__main__":
    app = App()
    app.mainloop()