"""Host-owned, sample-and-hold playback for frozen motif scores.

No model or rendering runs here. ``prepare`` does expensive compilation outside
the controller lock; a fresh-time ``deliver_prepared`` atomically admits it.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import threading

from .dance_motif_score import compile_intent, verify_score
from .dance_motif_recovery import RECOVERY_MS, recover_frames, verify_recovery

FRAME_MS = 50
SECTION_MS = 4000
SCORE_MS = 16000
MAX_BUDGET_MS = 5000


def _millis(value: int, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer millisecond value")
    return value


def _encoded(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _pose(frame: dict) -> bytes:
    return _encoded({"joints": frame["joints"], "contacts": frame["contacts"]})


@dataclass(frozen=True, slots=True)
class PreparedScore:
    """Opaque immutable transport for a score compiled by one controller."""

    _owner: object
    _frames: tuple[bytes, ...]
    _digest: str
    _rest_pose: bytes


class MotifRuntime:
    """Serialize request admission, boundary switches, sampling, and stop."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._owner = object()
        base = compile_intent('{"motif":"sway","accents":["soft","soft","soft","soft"]}')
        verify_score(base)
        self._rest_frame = _encoded(base["sequence"]["frames"][0])
        self._rest_pose = _pose(base["sequence"]["frames"][0])
        self._active: PreparedScore | None = None
        self._epoch_ms: int | None = None
        self._queued: tuple[int, PreparedScore] | None = None
        self._pending: dict | None = None
        self._frozen_frame: bytes | None = None
        self._recovery_frames: tuple[bytes, ...] | None = None
        self._recovery_epoch_ms: int | None = None
        self._recovery_digest: str | None = None
        self._last_now_ms = 0
        self._revision = 0

    def prepare(self, raw: str) -> PreparedScore:
        """Compile and verify off-lock; no state is committed by this method."""
        compiled = compile_intent(raw)
        verify_score(compiled)
        frames = compiled["sequence"]["frames"]
        if len(frames) != 321 or any(_pose(frames[i]) != self._rest_pose
                                       for i in (0, 80, 160, 240, 320)):
            raise ValueError("score lacks exact shared rest boundaries")
        return PreparedScore(self._owner, tuple(_encoded(frame) for frame in frames),
                             compiled["receipt"]["sequence_sha256"], self._rest_pose)

    def _time(self, now_ms: int) -> None:
        now_ms = _millis(now_ms, "now_ms")
        if now_ms < self._last_now_ms:
            raise ValueError("clock moved backward")
        self._last_now_ms = now_ms
        if self._queued is not None and now_ms >= self._queued[0]:
            self._epoch_ms, self._active = self._queued
            self._queued = None
        if (self._recovery_frames is not None and self._frozen_frame is None
                and now_ms - self._recovery_epoch_ms >= RECOVERY_MS):
            self._frozen_frame = self._recovery_frames[-1]

    def _frame(self, now_ms: int) -> tuple[bytes, int | None, str]:
        if self._frozen_frame is not None:
            return self._frozen_frame, None, "frozen"
        if self._recovery_frames is not None:
            index = (now_ms - self._recovery_epoch_ms) // FRAME_MS
            return self._recovery_frames[index], None, "recovering"
        if self._active is None:
            return self._rest_frame, None, "idle"
        elapsed = min(now_ms - self._epoch_ms, SCORE_MS)
        index = elapsed // FRAME_MS
        return self._active._frames[index], index, (
            "holding_end" if elapsed == SCORE_MS else "playing")

    def _sample(self, now_ms: int) -> dict:
        encoded, index, status = self._frame(now_ms)
        frame = json.loads(encoded)
        recovery_index = ((now_ms - self._recovery_epoch_ms) // FRAME_MS
                          if status == "recovering" else None)
        return {"now_ms": now_ms, "status": status, "revision": self._revision,
                "frame": frame, "source_frame_index": index,
                "at_rest": _pose(frame) == self._rest_pose,
                "score_sha256": self._active._digest if self._active else None,
                "epoch_ms": self._epoch_ms,
                "recovery_sha256": self._recovery_digest,
                "recovery_epoch_ms": self._recovery_epoch_ms,
                "recovery_frame_index": recovery_index}

    def request(self, now_ms: int, budget_ms: int) -> dict:
        """Replace the pending request and any queued replacement."""
        if type(budget_ms) is not int or not 1 <= budget_ms <= MAX_BUDGET_MS:
            raise ValueError("budget_ms must be an integer from 1 to 5000")
        with self._lock:
            self._time(now_ms)
            if self._recovery_frames is not None and self._frozen_frame is None:
                raise ValueError("cannot request while recovering")
            self._revision += 1
            request_id = f"motif-{self._revision}"
            self._pending = {"request_id": request_id, "revision": self._revision,
                             "deadline_ms": now_ms + budget_ms}
            self._queued = None
            return dict(self._pending)

    def deliver_prepared(self, request_id: str, prepared: PreparedScore,
                         now_ms: int) -> dict:
        """Admit only the latest valid reply, using time sampled after preparation."""
        with self._lock:
            self._time(now_ms)
            pending = self._pending
            if (type(request_id) is not str or pending is None or
                    request_id != pending["request_id"]):
                return {"status": "rejected_stale", "revision": self._revision}
            if now_ms > pending["deadline_ms"]:
                self._pending = None
                return {"status": "rejected_deadline", "revision": self._revision}
            if (type(prepared) is not PreparedScore or prepared._owner is not self._owner
                    or len(prepared._frames) != 321 or prepared._rest_pose != self._rest_pose):
                self._pending = None
                return {"status": "rejected_invalid", "revision": self._revision}
            current, _, _ = self._frame(now_ms)
            if self._frozen_frame is not None:
                if _pose(json.loads(current)) != self._rest_pose:
                    self._pending = None
                    return {"status": "rejected_unsupported_restart",
                            "revision": self._revision}
                switch_ms = now_ms
            elif self._active is None:
                switch_ms = now_ms
            else:
                elapsed = now_ms - self._epoch_ms
                switch_ms = (now_ms if elapsed >= SCORE_MS else
                             self._epoch_ms + ((elapsed + SECTION_MS - 1) // SECTION_MS)
                             * SECTION_MS)
            self._pending = None
            if switch_ms == now_ms:
                if _pose(json.loads(current)) != self._rest_pose:
                    return {"status": "rejected_nonrest_boundary",
                            "revision": self._revision}
                self._active, self._epoch_ms = prepared, now_ms
                self._frozen_frame = None
                self._recovery_frames = None
                self._recovery_epoch_ms = None
                self._recovery_digest = None
                return {"status": "applied", "revision": self._revision,
                        "switch_at_ms": now_ms, "score_sha256": prepared._digest}
            self._queued = (switch_ms, prepared)
            return {"status": "queued", "revision": self._revision,
                    "switch_at_ms": switch_ms, "score_sha256": prepared._digest}

    def deliver(self, request_id: str, raw: str, now_ms: int) -> dict:
        """Offline convenience; live callers should prepare then pass a fresh time."""
        try:
            prepared = self.prepare(raw)
        except ValueError as exc:
            with self._lock:
                self._time(now_ms)
                pending = self._pending
                if pending is None or request_id != pending["request_id"]:
                    return {"status": "rejected_stale", "revision": self._revision}
                if now_ms > pending["deadline_ms"]:
                    self._pending = None
                    return {"status": "rejected_deadline", "revision": self._revision}
                self._pending = None
                return {"status": "rejected_invalid", "reason": str(exc),
                        "revision": self._revision}
        return self.deliver_prepared(request_id, prepared, now_ms)

    def sample(self, now_ms: int) -> dict:
        """Return a detached 20 fps source frame, held until the next sample."""
        with self._lock:
            self._time(now_ms)
            return self._sample(now_ms)

    def interrupt(self, now_ms: int) -> dict:
        """Freeze the exact currently sampled pose; revoke pending work."""
        with self._lock:
            self._time(now_ms)
            self._frozen_frame = self._frame(now_ms)[0]
            self._pending = None
            self._queued = None
            self._revision += 1
            return self._sample(now_ms)

    def recover_to_rest(self, now_ms: int) -> dict:
        """Explicitly recover a frozen planted pose over two seconds."""
        with self._lock:
            self._time(now_ms)
            if self._frozen_frame is None:
                raise ValueError("recovery requires a frozen pose")
            source = json.loads(self._frozen_frame)
            frames = recover_frames(source)
            report = verify_recovery(frames, source)
            self._revision += 1
            self._pending = None
            self._queued = None
            self._active = None
            self._epoch_ms = None
            self._recovery_frames = tuple(_encoded(frame) for frame in frames)
            self._recovery_epoch_ms = now_ms
            self._recovery_digest = report["frames_sha256"]
            self._frozen_frame = None
            return self._sample(now_ms)

    def snapshot(self) -> dict:
        """Return detached state as of the most recent accepted clock time."""
        with self._lock:
            state = self._sample(self._last_now_ms)
            state["pending"] = dict(self._pending) if self._pending else None
            state["queued_switch_ms"] = self._queued[0] if self._queued else None
            state["queued_score_sha256"] = self._queued[1]._digest if self._queued else None
            return state
