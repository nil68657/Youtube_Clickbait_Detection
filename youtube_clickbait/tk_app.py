"""
Desktop UI (Tkinter): native window, no browser.
Ollama requests run one-at-a-time through a FIFO queue; a heartbeat shows when Ollama is reachable.
"""

from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from youtube_clickbait.analysis_queue import AnalysisQueue, AnalyzeJob
from youtube_clickbait.ollama_launcher import cleanup_ollama_child, ensure_ollama_running
from youtube_clickbait.pipeline import markdown_to_plain
from youtube_clickbait.ollama_client import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_HOST,
    merge_model_choices,
    normalize_ollama_base,
    ollama_list_models,
    probe_ollama,
)


def main() -> None:
    root = tk.Tk()
    root.title("YouTube clickbait check")
    root.minsize(560, 560)
    root.geometry("720x640")

    host_default = normalize_ollama_base(os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST))
    model_default = os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)

    root.title("Starting Ollama…")
    root.update_idletasks()
    ok_ollama, ollama_start_msg, _ollama_proc = ensure_ollama_running(host_default)
    root.title("YouTube clickbait check")
    if not ok_ollama:
        messagebox.showwarning(
            "Ollama",
            ollama_start_msg
            + "\n\nStart the Ollama app manually if needed, then use Test connection.",
        )

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
    host_row = ttk.Frame(frm)
    host_row.grid(row=r, column=1, sticky="ew", **pad)
    host_row.columnconfigure(0, weight=1)
    host_var = tk.StringVar(value=host_default)
    host_entry = ttk.Entry(host_row, textvariable=host_var, width=40)
    host_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

    def test_ollama_connection() -> None:
        def work() -> None:
            h = normalize_ollama_base(host_var.get().strip() or host_default)
            ok, working, msg = probe_ollama(h)

            def ui() -> None:
                if ok:
                    if working != h:
                        host_var.set(working)
                    refresh_models()
                    info = (
                        msg
                        if msg != "OK"
                        else f"Ollama at {working} is responding."
                    )
                    messagebox.showinfo("Ollama", info)
                else:
                    messagebox.showerror("Ollama not reachable", msg)

            root.after(0, ui)

        threading.Thread(target=work, daemon=True).start()

    ttk.Button(host_row, text="Test connection", command=test_ollama_connection).grid(
        row=0, column=1, sticky="e"
    )
    r += 1

    ollama_led_var = tk.StringVar(value="Checking Ollama...")
    ttk.Label(frm, text="Ollama status").grid(row=r, column=0, sticky="w", **pad)
    ollama_lbl = ttk.Label(frm, textvariable=ollama_led_var, foreground="gray")
    ollama_lbl.grid(row=r, column=1, sticky="w", **pad)
    r += 1

    ttk.Label(frm, text="Model").grid(row=r, column=0, sticky="w", **pad)
    discovered = ollama_list_models(host_default)
    model_choices = merge_model_choices(discovered)
    if model_default and model_default not in model_choices:
        model_choices = [model_default] + model_choices
    model_var = tk.StringVar(value=model_default)
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

    btn = ttk.Button(frm, text="Analyze (add to queue)")
    btn.grid(row=r, column=1, sticky="w", **pad)
    r += 1

    ttk.Label(frm, text="Status").grid(row=r, column=0, sticky="nw", **pad)
    status_var = tk.StringVar(value="Queue idle. Paste a URL and click Analyze.")
    status_lbl = ttk.Label(frm, textvariable=status_var, wraplength=520, justify="left")
    status_lbl.grid(row=r, column=1, sticky="ew", **pad)
    r += 1

    ttk.Label(frm, text="Result").grid(row=r, column=0, sticky="nw", **pad)
    out = scrolledtext.ScrolledText(frm, height=16, wrap="word")
    out.grid(row=r, column=1, sticky="nsew", **pad)
    frm.rowconfigure(r, weight=1)

    hint = ttk.Label(
        frm,
        text=(
            "Captions only. Requests are queued: one Ollama generation at a time. "
            "Keep Ollama running; models include gpt-oss:20b (pull first). "
            "URL may be http://127.0.0.1:11434 or 127.0.0.1:11434."
        ),
        foreground="gray",
    )
    hint.grid(row=r + 1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))

    def set_status(msg: str) -> None:
        status_var.set(msg)

    def ui_status(msg: str) -> None:
        root.after(0, lambda m=msg: set_status(m))

    def refresh_models() -> None:
        h = normalize_ollama_base(host_var.get().strip() or host_default)
        names = merge_model_choices(ollama_list_models(h))
        model_combo["values"] = names

    def update_ollama_indicator() -> None:
        h = normalize_ollama_base(host_var.get().strip() or host_default)
        ok, working, _msg = probe_ollama(h)
        if ok:
            if working != h:
                ollama_led_var.set(f"Reachable at {working} (field shows {h} - click Test to apply)")
            else:
                ollama_led_var.set(f"Reachable at {working}")
            ollama_lbl.configure(foreground="green")
        else:
            ollama_led_var.set("Not reachable - start Ollama or click Test connection")
            ollama_lbl.configure(foreground="darkred")

    def heartbeat_loop() -> None:
        while True:
            root.after(0, update_ollama_indicator)
            time.sleep(12.0)

    threading.Thread(target=heartbeat_loop, daemon=True).start()

    def append_result(job: AnalyzeJob, md: str, st: str) -> None:
        out.insert(tk.END, f"\n{'=' * 60}\nJob #{job.seq}  {job.url}\n{'=' * 60}\n\n")
        if md:
            out.insert(tk.END, markdown_to_plain(md) + "\n")
        elif st:
            out.insert(tk.END, st + "\n")

    def on_queue_result(job: AnalyzeJob, md: str, st: str, err: Exception | None) -> None:
        def _ui() -> None:
            if err is not None:
                messagebox.showerror("Analyze error", str(err))
                append_result(job, "", f"Error: {err}")
                return
            append_result(job, md, st)
            if not md and st:
                messagebox.showwarning("YouTube clickbait check", st)

        root.after(0, _ui)

    aq = AnalysisQueue(on_status=ui_status, on_result=on_queue_result)

    def on_analyze() -> None:
        try:
            max_chars = int(max_var.get())
        except (ValueError, tk.TclError):
            messagebox.showerror("Invalid value", "Max transcript chars must be a number.")
            return
        seq = aq.next_seq()
        job = AnalyzeJob(
            seq=seq,
            url=url_var.get(),
            ollama_host=normalize_ollama_base(host_var.get().strip() or host_default),
            model=model_var.get().strip(),
            caption_lang=lang_var.get().strip(),
            max_transcript_chars=max_chars,
        )
        aq.submit(job)

    btn.configure(command=on_analyze)
    host_entry.bind("<FocusOut>", lambda _: refresh_models())

    url_entry.focus_set()
    update_ollama_indicator()

    def on_close() -> None:
        cleanup_ollama_child()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
