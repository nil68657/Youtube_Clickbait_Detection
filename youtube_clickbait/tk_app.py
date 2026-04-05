"""
Desktop UI (Tkinter): no browser, no local web server — native window only.
Requires Ollama running separately (same machine is fine).
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from youtube_clickbait.ollama_client import DEFAULT_MODEL, DEFAULT_OLLAMA_HOST, ollama_list_models
from youtube_clickbait.pipeline import markdown_to_plain, run_pipeline


def main() -> None:
    root = tk.Tk()
    root.title("YouTube clickbait check")
    root.minsize(560, 520)
    root.geometry("720x600")

    host_default = os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
    model_default = os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)

    pad = {"padx": 10, "pady": 4}

    frm = ttk.Frame(root, padding=12)
    frm.grid(row=0, column=0, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    frm.columnconfigure(1, weight=1)

    r = 0
    ttk.Label(frm, text="YouTube URL").grid(row=r, column=0, sticky="w", **pad)
    url_var = tk.StringVar()
    url_entry = ttk.Entry(frm, textvariable=url_var, width=64)
    url_entry.grid(row=r, column=1, sticky="ew", **pad)
    r += 1

    ttk.Label(frm, text="Ollama URL").grid(row=r, column=0, sticky="w", **pad)
    host_var = tk.StringVar(value=host_default)
    host_entry = ttk.Entry(frm, textvariable=host_var, width=48)
    host_entry.grid(row=r, column=1, sticky="ew", **pad)
    r += 1

    ttk.Label(frm, text="Model").grid(row=r, column=0, sticky="w", **pad)
    discovered = ollama_list_models(host_default)
    model_choices = discovered if discovered else [model_default]
    model_var = tk.StringVar(
        value=model_default if model_default in model_choices else model_choices[0]
    )
    model_combo = ttk.Combobox(
        frm,
        textvariable=model_var,
        values=model_choices,
        width=40,
    )
    model_combo.grid(row=r, column=1, sticky="w", **pad)
    r += 1

    ttk.Label(frm, text="Caption language").grid(row=r, column=0, sticky="w", **pad)
    lang_var = tk.StringVar(value="en")
    ttk.Entry(frm, textvariable=lang_var, width=8).grid(row=r, column=1, sticky="w", **pad)
    r += 1

    ttk.Label(frm, text="Max transcript chars").grid(row=r, column=0, sticky="w", **pad)
    max_var = tk.IntVar(value=28000)
    max_spin = ttk.Spinbox(
        frm,
        from_=8000,
        to=48000,
        increment=1000,
        textvariable=max_var,
        width=10,
    )
    max_spin.grid(row=r, column=1, sticky="w", **pad)
    r += 1

    btn = ttk.Button(frm, text="Analyze")
    btn.grid(row=r, column=1, sticky="w", **pad)
    r += 1

    ttk.Label(frm, text="Status").grid(row=r, column=0, sticky="nw", **pad)
    status_var = tk.StringVar(value="Paste a URL and click Analyze.")
    status_lbl = ttk.Label(frm, textvariable=status_var, wraplength=520, justify="left")
    status_lbl.grid(row=r, column=1, sticky="ew", **pad)
    r += 1

    ttk.Label(frm, text="Result").grid(row=r, column=0, sticky="nw", **pad)
    out = scrolledtext.ScrolledText(frm, height=18, wrap="word")
    out.grid(row=r, column=1, sticky="nsew", **pad)
    frm.rowconfigure(r, weight=1)

    hint = ttk.Label(
        frm,
        text="Uses captions only. Ollama must be running (e.g. ollama serve).",
        foreground="gray",
    )
    hint.grid(row=r + 1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))

    def refresh_models() -> None:
        h = host_var.get().strip() or host_default
        names = ollama_list_models(h)
        if names:
            model_combo["values"] = names
            if model_var.get() not in names:
                model_var.set(names[0])

    def on_analyze() -> None:
        btn.configure(state="disabled")
        status_var.set("Working…")
        out.delete("1.0", tk.END)
        root.update_idletasks()

        def work() -> None:
            try:
                md, st = run_pipeline(
                    url_var.get(),
                    host_var.get().strip(),
                    model_var.get().strip(),
                    lang_var.get().strip(),
                    int(max_var.get()),
                )

                def apply_ui() -> None:
                    btn.configure(state="normal")
                    status_var.set(st)
                    if md:
                        out.insert(tk.END, markdown_to_plain(md))
                    elif st:
                        messagebox.showwarning("YouTube clickbait check", st)

                root.after(0, apply_ui)
            except Exception as e:
                def err() -> None:
                    btn.configure(state="normal")
                    status_var.set(f"Error: {e}")
                    messagebox.showerror("Error", str(e))

                root.after(0, err)

        threading.Thread(target=work, daemon=True).start()

    btn.configure(command=on_analyze)
    host_entry.bind("<FocusOut>", lambda _: refresh_models())

    url_entry.focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()
