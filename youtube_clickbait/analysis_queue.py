"""
FIFO queue for analysis jobs. One worker processes one Ollama request at a time
so the server is never hit with overlapping generations.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Callable

from youtube_clickbait.pipeline import run_pipeline


@dataclass
class AnalyzeJob:
    seq: int
    url: str
    ollama_host: str
    model: str
    caption_lang: str
    max_transcript_chars: int


class AnalysisQueue:
    def __init__(
        self,
        *,
        on_status: Callable[[str], None],
        on_result: Callable[[AnalyzeJob, str, str, Exception | None], None],
    ) -> None:
        self._q: queue.Queue[AnalyzeJob] = queue.Queue()
        self._on_status = on_status
        self._on_result = on_result
        self._stop = threading.Event()
        self._seq = 0
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def next_seq(self) -> int:
        with self._lock:
            self._seq += 1
            return self._seq

    def submit(self, job: AnalyzeJob) -> int:
        self._q.put(job)
        n = self._q.qsize()
        self._on_status(
            f"Job #{job.seq} queued - {n} total in queue (one Ollama request at a time)."
        )
        return n

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                job = self._q.get(timeout=0.35)
            except queue.Empty:
                continue

            try:
                waiting = self._q.qsize()
                if waiting:
                    self._on_status(
                        f"Running job #{job.seq}... ({waiting} more in queue after this one.)"
                    )
                else:
                    self._on_status(
                        f"Running job #{job.seq}... (next request starts when this finishes.)"
                    )

                err: Exception | None = None
                md, st = "", ""
                try:
                    md, st = run_pipeline(
                        job.url,
                        job.ollama_host,
                        job.model,
                        job.caption_lang,
                        job.max_transcript_chars,
                    )
                except Exception as e:
                    err = e

                self._on_result(job, md, st, err)

                rest = self._q.qsize()
                if rest:
                    self._on_status(f"Finished #{job.seq}. {rest} job(s) left in queue.")
                else:
                    self._on_status("Queue idle - ready for the next Analyze.")
            finally:
                self._q.task_done()
