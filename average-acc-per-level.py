import sqlite3, json, datetime
import tkinter as tk
from tkinter import filedialog, messagebox
from tkcalendar import DateEntry
import matplotlib.pyplot as plt
from pathlib import Path

cfg_file = Path(__file__).with_name('config.json')
cfg = json.loads(cfg_file.read_text()) if cfg_file.exists() else {}

def save_cfg(data):
    cfg_file.write_text(json.dumps(data))

def get_settings():
    today = datetime.date.today()
    all_def = cfg.get("all_time", True)
    sd_def = cfg.get("start")
    ed_def = cfg.get("end")
    if sd_def:
        y1, m1, d1 = map(int, sd_def.split('-'))
    else:
        y1, m1, d1 = today.year, today.month, today.day
    if ed_def:
        y2, m2, d2 = map(int, ed_def.split('-'))
    else:
        y2, m2, d2 = today.year, today.month, today.day

    root = tk.Tk()
    root.title("DDR Stats Settings")
    db_var  = tk.StringVar(value=cfg.get("db_path",""))
    f1_var  = tk.StringVar(value=cfg.get("last_f1",""))
    f2_var  = tk.StringVar(value=cfg.get("last_f2",""))
    avg_var = tk.BooleanVar(value=cfg.get("avg_only",False))
    all_var = tk.BooleanVar(master=root, value=all_def)

    tk.Label(root, text="Database:").grid(row=0,column=0,sticky="e")
    tk.Entry(root, textvariable=db_var, width=40).grid(row=0,column=1)
    tk.Button(root, text="Browse", command=lambda: db_var.set(
        filedialog.askopenfilename(filetypes=[("SQLite DB","*.db")])
    )).grid(row=0,column=2)

    tk.Label(root, text="Flower 1 (ID or Name):").grid(row=1,column=0,sticky="e")
    tk.Entry(root, textvariable=f1_var).grid(row=1,column=1,columnspan=2,sticky="we")
    tk.Label(root, text="Flower 2 (ID or Name):").grid(row=2,column=0,sticky="e")
    tk.Entry(root, textvariable=f2_var).grid(row=2,column=1,columnspan=2,sticky="we")
    tk.Checkbutton(root, text="Show average only", variable=avg_var).grid(row=3,columnspan=3,sticky="w")

    def toggle_dates():
        st = "disabled" if all_var.get() else "normal"
        start_entry.config(state=st)
        end_entry.config(state=st)

    tk.Checkbutton(root, text="All time", variable=all_var, command=toggle_dates)\
      .grid(row=4,columnspan=3,sticky="w")

    tk.Label(root, text="Start date:").grid(row=5,column=0,sticky="e")
    start_entry = DateEntry(root, date_pattern="yyyy-MM-dd",
                            year=y1, month=m1, day=d1,
                            state="disabled" if all_def else "normal")
    start_entry.grid(row=5,column=1)
    tk.Label(root, text="End date:").grid(row=6,column=0,sticky="e")
    end_entry = DateEntry(root, date_pattern="yyyy-MM-dd",
                          year=y2, month=m2, day=d2,
                          state="disabled" if all_def else "normal")
    end_entry.grid(row=6,column=1)

    def on_ok():
        if not db_var.get():
            messagebox.showerror("Error","Select a database"); return
        if all_var.get():
            sd = ed = None
        else:
            sd = start_entry.get_date().isoformat()
            ed = end_entry.get_date().isoformat()
        root.settings = {
            "db_path":  db_var.get(),
            "last_f1":  f1_var.get(),
            "last_f2":  f2_var.get(),
            "avg_only": avg_var.get(),
            "all_time": all_var.get(),
            "start":    sd,
            "end":      ed
        }
        root.destroy()

    tk.Button(root, text="OK", command=on_ok).grid(row=7,column=1)
    root.mainloop()
    return root.settings

def resolve(db, inp):
    conn = sqlite3.connect(db); cur = conn.cursor()
    fid = name = None
    if inp.isdigit():
        cur.execute("SELECT FlowerId,DdrName FROM users WHERE FlowerId=?", (int(inp),))
        row = cur.fetchone()
        if row: fid, name = row
    if fid is None:
        cur.execute("SELECT FlowerId,DdrName FROM users WHERE DdrName=?", (inp,))
        row = cur.fetchone()
        if row: fid, name = row
    conn.close()
    return fid, name

def fetch(db, fid, all_time, s, e):
    conn = sqlite3.connect(db); cur = conn.cursor()
    q = "SELECT Level,MAX(Score),MIN(Score),AVG(Score) FROM DdrPlays WHERE FlowerId=? AND Grade!='E'"
    params = [fid]
    if not all_time and s and e:
        q += " AND Timestamp BETWEEN ? AND ?"; params += [s, e]
    q += " GROUP BY Level ORDER BY Level"
    cur.execute(q, params); rows = cur.fetchall(); conn.close()
    if rows: return zip(*rows)
    return ([], [], [], [])

def main():
    cfg_data = get_settings()
    save_cfg(cfg_data)
    db = cfg_data["db_path"]
    inputs = [cfg_data["last_f1"]]
    if cfg_data["last_f2"]:
        inputs.append(cfg_data["last_f2"])
    flowers = []
    for inp in inputs:
        fid, name = resolve(db, inp)
        if fid is None:
            messagebox.showerror("Error", f"No match for '{inp}'"); return
        flowers.append((fid, name))

    avg_only = cfg_data["avg_only"]
    all_time = cfg_data["all_time"]
    sd = cfg_data["start"]
    ed = cfg_data["end"]

    fig, ax = plt.subplots(figsize=(8,5))
    colors = [("lightgreen","green","darkgreen"), ("lightblue","blue","darkblue")]
    all_lv = set()
    for i, (fid, name) in enumerate(flowers):
        lv, mx, mn, av = fetch(db, fid, all_time, sd, ed)
        all_lv.update(lv)
        cmax, cav, cmin = colors[i]
        if avg_only:
            ax.plot(lv, av, "o-", label=f"{name} Avg", color=cav)
        else:
            ax.plot(lv, mx, "o-", label=f"{name} Max", color=cmax)
            ax.plot(lv, av, "o-", label=f"{name} Avg", color=cav)
            ax.plot(lv, mn, "o-", label=f"{name} Min", color=cmin)

    if all_lv:
        ax.set_xticks(range(min(all_lv), max(all_lv)+1))
    ax.set_ylim(0.6e6, 1.0e6)
    ax.set_xlabel("Level"); ax.set_ylabel("Score")
    ax.set_title("DDR Flower Score Comparison"); ax.legend()
    plt.show()

if __name__=="__main__":
    main()

