# Promo Site (עמוד יחצן לאירועים) – GitHub Pages

עמוד סטטי (עמוד אחד) שמציג אירועים בתור כרטיסיות, ממיין לפי תאריך, ומפריד בין:
- **אירועים קרובים**
- **Past events** (ארכיון, מוסתר כברירת מחדל)

כל אירוע הוא **תיקייה** תחת `events/` עם `meta.json` + `cover.jpg`.

## איך זה עובד
- האתר קורא `events/index.json` (רשימת תיקיות אירועים).
- לכל תיקייה נטען `meta.json`, ומוצגת כרטיסיה.
- GitHub Actions מריץ `python tools/promogen.py build` בכל push (וגם cron) כדי לייצר/לעדכן את `events/index.json`.

---

## שלב 1: להרים GitHub Pages
1. צור Repo חדש ב-GitHub (Public מומלץ ל-Pages חינמי).
2. העלה את כל הקבצים בריפו הזה (או `git push`).
3. GitHub: **Settings → Pages → Source = GitHub Actions**
4. דחוף ל-`main`. תוך דקה-שתיים תקבל לינק `https://<user>.github.io/<repo>/`.

---

## שלב 2: הוספת אירוע חדש (הכי קל)
### אופציה א': ידני
1. צור תיקייה:
   `events/YYYY-MM-DD-some-slug/`
2. הוסף:
   - `meta.json`
   - `cover.jpg`
3. `git add . && git commit -m "Add event" && git push`

ה-Action יעדכן אינדקס ויפרסם אוטומטית.

### אופציה ב': עם המחולל
```bash
python tools/promogen.py new --date 2026-03-15 --title "Sabres Night" --time 23:00 --location "תל אביב" --coupon "RON10" --ticket "https://..." --promoter "https://instagram.com/..."
python tools/promogen.py build
git add . && git commit -m "Add event" && git push
```

---

## בדיקה מקומית
```bash
python tools/promogen.py serve --port 8000
```
פתח:
`http://localhost:8000`

---

## פורמט meta.json
דוגמה:
```json
{
  "title": "No Name – פורים במדבר",
  "date": "2026-03-02",
  "time": "22:00",
  "location": "לב המדבר",
  "description": "2 במות | ...",
  "ticket_url": "https://example.com",
  "promoter_url": "https://instagram.com/yourpage",
  "coupon_code": "רוןקרובים",
  "image": "cover.jpg"
}
```

### הערות
- `date` בפורמט `YYYY-MM-DD` חובה.
- `time` מומלץ (כדי להבדיל בין אירועים באותו יום).
- `image` זה שם הקובץ בתיקייה (ברירת מחדל `cover.jpg`).

---

## התאמות קלות
- שינוי טקסט/שם מותג: `index.html` (כותרת למעלה).
- להוסיף כפתור WhatsApp/טלפון: להוסיף שדה ל-meta.json ולקרוא אותו ב-`card()`.

