import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    from PIL import Image
    PIL_OK = True
except Exception:
    PIL_OK = False


# ---------- repo detection ----------
def find_repo_root(start: Path) -> Path | None:
    p = start.resolve()
    for _ in range(25):
        if (p / ".git").exists():
            return p
        p = p.parent
    return None


def app_start_dir() -> Path:
    # When packaged with PyInstaller, sys.executable is inside ...EventFolderMaker.app/Contents/MacOS/...
    exe = Path(sys.executable).resolve()
    # Usually parents[3] is the folder containing the .app (e.g. repo/tools/)
    if len(exe.parents) > 3:
        return exe.parents[3]
    return Path.cwd()


def default_events_root() -> str:
    root = find_repo_root(app_start_dir())
    if root:
        return str(root / "events")
    # fallback if not in a repo
    return os.path.join(os.path.expanduser("~"), "Desktop", "events")


# ---------- helpers ----------
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


def run_cmd(cmd: list[str], cwd: str, log_fn):
    log_fn(f"$ {' '.join(cmd)}")
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if p.stdout.strip():
        log_fn(p.stdout.strip())
    if p.stderr.strip():
        log_fn(p.stderr.strip())
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")


def command_exists(name: str) -> bool:
    from shutil import which
    return which(name) is not None


def gh_authed(repo_cwd: str) -> bool:
    p = subprocess.run(["gh", "auth", "status"], cwd=repo_cwd, text=True, capture_output=True)
    return p.returncode == 0


# ---------- GUI ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Event Folder Maker")
        self.geometry("580x820")
        self.minsize(580, 780)
        self.resizable(True, True)

        self.image_path = tk.StringVar(value="")
        self.auto_pr = tk.BooleanVar(value=True)  # default ON

        self._build_ui()

    def _build_ui(self):
        header = tk.Label(
            self,
            text="הוספת אירוע (יוצר תיקייה + meta.json + cover.jpg)\nואופציונלי: Sync + Push + PR אוטומטי",
            font=("Arial", 13, "bold"),
            justify="center"
        )
        header.pack(pady=10)

        frm = tk.Frame(self)
        frm.pack(fill="x", padx=14, pady=4)

        self.title_var = self._row(frm, "שם האירוע*", "")
        self.date_var = self._row(frm, "תאריך* (YYYY-MM-DD)", datetime.now().strftime("%Y-%m-%d"))
        self.time_var = self._row(frm, "שעה* (HH:MM)", "22:00")
        self.loc_var = self._row(frm, "מיקום", "")
        self.ticket_var = self._row(frm, "לינק לכרטיסים*", "")
        self.coupon_var = self._row(frm, "קופון", "")
        self.desc_var = self._row(frm, "תיאור קצר", "", multiline=True)

        imgfrm = tk.Frame(self)
        imgfrm.pack(fill="x", padx=14, pady=4)
        tk.Label(imgfrm, text="תמונה/פלייר*").grid(row=0, column=0, sticky="w")
        tk.Entry(imgfrm, textvariable=self.image_path, width=52).grid(row=1, column=0, sticky="w", pady=4)
        tk.Button(imgfrm, text="בחר קובץ…", command=self.pick_image).grid(row=1, column=1, padx=8)

        outfrm = tk.Frame(self)
        outfrm.pack(fill="x", padx=14, pady=4)
        tk.Label(outfrm, text="איפה ליצור את התיקיות (ברירת מחדל: events בתוך הריפו)").grid(row=0, column=0, sticky="w")
        self.out_root = tk.StringVar(value=default_events_root())
        tk.Entry(outfrm, textvariable=self.out_root, width=52).grid(row=1, column=0, sticky="w", pady=4)
        tk.Button(outfrm, text="בחר…", command=self.pick_out_root).grid(row=1, column=1, padx=8)

        optfrm = tk.Frame(self)
        optfrm.pack(fill="x", padx=14, pady=8)
        tk.Checkbutton(
            optfrm,
            text="אחרי יצירה: Sync + Push + Create PR אוטומטי",
            variable=self.auto_pr
        ).pack(anchor="w")

        btnfrm = tk.Frame(self)
        btnfrm.pack(fill="x", padx=14, pady=8)

        tk.Button(
            btnfrm,
            text="✅ צור תיקיית אירוע",
            font=("Arial", 12, "bold"),
            command=self.create_event
        ).pack(fill="x", pady=6)

        tk.Button(
            btnfrm,
            text="🚀 Push + PR (רק אם כבר יש שינויים ב-events/)",
            command=self.push_pr_only
        ).pack(fill="x", pady=6)

        tk.Button(
            btnfrm,
            text="🔐 התחבר ל-GitHub (gh auth login)",
            command=self.gh_login
        ).pack(fill="x", pady=6)

        hint = tk.Label(
            self,
            text="הערות:\n- כדי ש-Push+PR יעבוד: צריך Clone אמיתי של הריפו (לא ZIP), וגם git+gh מותקנים.\n- אם אין חיבור ל-gh: לחץ על 'התחבר ל-GitHub'",
            fg="#666",
            justify="left"
        )
        hint.pack(padx=14, pady=6, anchor="w")

        if not PIL_OK:
            warn = tk.Label(self, text="הערה: Pillow לא מותקן, אז התמונה תועתק כמו שהיא (עדיין בשם cover.jpg).", fg="#a00")
            warn.pack(pady=4)

        # log box
        loglbl = tk.Label(self, text="Log", font=("Arial", 11, "bold"))
        loglbl.pack(padx=14, pady=(8, 4), anchor="w")

        self.log = tk.Text(self, height=14, width=90)
        self.log.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def _row(self, parent, label, default, multiline=False):
        frame = tk.Frame(parent)
        frame.pack(fill="x", pady=4)
        tk.Label(frame, text=label).pack(anchor="w")
        if multiline:
            txt = tk.Text(frame, height=4, width=70)
            txt.insert("1.0", default)
            txt.pack(fill="x")
            class TVar:
                def get(self_inner): return txt.get("1.0", "end").strip()
                def set(self_inner, v):
                    txt.delete("1.0", "end")
                    txt.insert("1.0", v)
            return TVar()
        else:
            var = tk.StringVar(value=default)
            tk.Entry(frame, textvariable=var, width=74).pack(fill="x")
            return var

    def log_line(self, s: str):
        self.log.insert("end", s + "\n")
        self.log.see("end")
        self.update_idletasks()

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

    # ---------- GH login ----------
    def gh_login(self):
        try:
            self.log_line("---- gh auth login ----")
            if not command_exists("gh"):
                raise RuntimeError("לא מצאתי gh (GitHub CLI). התקן gh ואז נסה שוב.")
            # open interactive login in Terminal
            subprocess.Popen(["open", "-a", "Terminal", "gh", "auth", "login"])
            messagebox.showinfo("התחברות", "פתחתי טרמינל להתחברות. סיים את התהליך שם ואז חזור לאפליקציה.")
        except Exception as e:
            messagebox.showerror("שגיאה", str(e))
            self.log_line(f"ERROR: {e}")

    # ---------- main actions ----------
    def create_event(self):
        try:
            self.log_line("---- Create Event ----")

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

            meta_path = os.path.join(out_dir, "meta.json")
            with open(meta_path, "w", encoding="utf-8") as f:
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

            self.log_line(f"Created: {out_dir}")
            messagebox.showinfo("הצלחה ✅", f"נוצר אירוע:\n{out_dir}\n\nבתיקייה יש meta.json + cover.jpg")

            # auto PR
            if self.auto_pr.get():
                self.push_pr(repo_hint_path=out_dir)

            # reset a bit
            self.image_path.set("")
            self.title_var.set("")
            self.ticket_var.set("")
            self.coupon_var.set("")
            self.loc_var.set("")
            try:
                self.desc_var.set("")
            except Exception:
                pass

        except Exception as e:
            messagebox.showerror("שגיאה", str(e))
            self.log_line(f"ERROR: {e}")

    def push_pr_only(self):
        try:
            self.push_pr(repo_hint_path=None)
        except Exception as e:
            messagebox.showerror("שגיאה", str(e))
            self.log_line(f"ERROR: {e}")

    def push_pr(self, repo_hint_path: str | None):
        self.log_line("---- Push + PR ----")

        if not command_exists("git"):
            raise RuntimeError("לא מצאתי git במחשב. התקן GitHub Desktop או Xcode Command Line Tools.")
        if not command_exists("gh"):
            raise RuntimeError("לא מצאתי gh (GitHub CLI). התקן gh ואז נסה שוב.")

        # locate repo root
        start = Path(repo_hint_path) if repo_hint_path else app_start_dir()
        repo_root = find_repo_root(start) or find_repo_root(app_start_dir())
        if not repo_root:
            raise RuntimeError("לא מצאתי .git. כדי ש-Push+PR יעבוד צריך Clone אמיתי של הריפו (לא ZIP).")

        repo = str(repo_root)
        self.log_line(f"Repo: {repo}")

        # if not authed -> offer login
        if not gh_authed(repo):
            do = messagebox.askyesno("לא מחובר ל-GitHub", "לא מצאתי חיבור ל-gh.\nרוצה להתחבר עכשיו? (יפתח טרמינל)")
            if do:
                self.gh_login()
            raise RuntimeError("צריך להתחבר ל-gh ואז לנסות שוב (gh auth login).")

        # detect default branch + parent (upstream)
        default_branch = "main"
        try:
            p = subprocess.run(["gh", "repo", "view", "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name"],
                               cwd=repo, text=True, capture_output=True)
            if p.returncode == 0 and p.stdout.strip():
                default_branch = p.stdout.strip()
        except Exception:
            pass

        parent_full = ""
        try:
            p = subprocess.run(["gh", "repo", "view", "--json", "parent", "-q", ".parent.nameWithOwner"],
                               cwd=repo, text=True, capture_output=True)
            if p.returncode == 0:
                parent_full = p.stdout.strip()
        except Exception:
            pass

        # sync fork on GitHub if parent exists
        if parent_full:
            self.log_line(f"Detected fork. Upstream: {parent_full}")
            try:
                run_cmd(["gh", "repo", "sync", "-b", default_branch], cwd=repo, log_fn=self.log_line)
            except Exception:
                self.log_line("Warning: gh repo sync failed (continuing).")

        # pull latest on default branch
        run_cmd(["git", "checkout", default_branch], cwd=repo, log_fn=self.log_line)
        run_cmd(["git", "pull", "--ff-only"], cwd=repo, log_fn=self.log_line)

        # check if there are changes in events/
        p = subprocess.run(["git", "status", "--porcelain", "events/"], cwd=repo, text=True, capture_output=True)
        if p.returncode != 0:
            raise RuntimeError("git status נכשל.")
        if not p.stdout.strip():
            messagebox.showinfo("אין שינויים", "לא נמצאו שינויים בתוך events/.")
            self.log_line("No changes in events/.")
            return

        # create branch
        ts = time.strftime("%Y%m%d-%H%M%S")
        branch = f"partner/events-{ts}"
        run_cmd(["git", "checkout", "-b", branch], cwd=repo, log_fn=self.log_line)

        # stage only events/
        run_cmd(["git", "add", "events/"], cwd=repo, log_fn=self.log_line)

        # commit message
        msg = f"Update events ({ts})"
        run_cmd(["git", "commit", "-m", msg], cwd=repo, log_fn=self.log_line)

        # push
        run_cmd(["git", "push", "-u", "origin", branch], cwd=repo, log_fn=self.log_line)

        # create PR
        pr_repo_flag = []
        if parent_full:
            pr_repo_flag = ["--repo", parent_full]
            fork_full = ""
            p2 = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                                cwd=repo, text=True, capture_output=True)
            if p2.returncode == 0:
                fork_full = p2.stdout.strip()
            fork_owner = fork_full.split("/")[0] if "/" in fork_full else ""
            head = f"{fork_owner}:{branch}" if fork_owner else branch

            pr_cmd = ["gh", "pr", "create", *pr_repo_flag, "--base", default_branch, "--head", head,
                      "--title", msg, "--body", "Auto PR from EventFolderMaker."]
        else:
            pr_cmd = ["gh", "pr", "create", "--base", default_branch, "--head", branch,
                      "--title", msg, "--body", "Auto PR from EventFolderMaker."]

        p3 = subprocess.run(pr_cmd, cwd=repo, text=True, capture_output=True)
        if p3.returncode != 0:
            self.log_line(p3.stdout.strip())
            self.log_line(p3.stderr.strip())
            raise RuntimeError("לא הצלחתי ליצור PR אוטומטי. פתח PR ידנית מה-branch.")

        pr_url = p3.stdout.strip()
        self.log_line(f"PR: {pr_url}")

        try:
            subprocess.run(["open", pr_url], cwd=repo)
        except Exception:
            pass

        messagebox.showinfo("PR נוצר ✅", f"פתחתי Pull Request:\n{pr_url}")


if __name__ == "__main__":
    app = App()
    app.mainloop()