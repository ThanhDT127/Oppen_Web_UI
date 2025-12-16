import io
import json
import os
import struct
import wave
from pathlib import Path

import httpx

MW = os.getenv("MW_BASE_URL", "http://127.0.0.1:5000")
SUBKEY = os.getenv("MW_SUBKEY", "").strip()
USER_ID = os.getenv("MW_USER_ID", "user1")

HEADERS = {"Authorization": f"Bearer {SUBKEY}"} if SUBKEY else {}
USERS_PATH = Path(__file__).with_name("users.json")


def snap(user_id: str = USER_ID) -> dict | None:
    if not USERS_PATH.exists():
        return None
    users = json.loads(USERS_PATH.read_text(encoding="utf-8-sig"))
    u = next((x for x in users if x.get("user_id") == user_id), None)
    if not u:
        return None
    q = u.get("quota", {})
    return {
        "used_tokens": int(q.get("used_tokens", 0) or 0),
        "used_cost_usd": float(q.get("used_cost_usd", 0.0) or 0.0),
        "used_image_requests": int(q.get("used_image_requests", 0) or 0),
        "used_tts_requests": int(q.get("used_tts_requests", 0) or 0),
        "used_tts_chars": int(q.get("used_tts_chars", 0) or 0),
        "used_stt_requests": int(q.get("used_stt_requests", 0) or 0),
        "used_video_requests": int(q.get("used_video_requests", 0) or 0),
        "used_video_seconds": float(q.get("used_video_seconds", 0.0) or 0.0),
    }


def diff(a: dict | None, b: dict | None) -> dict:
    if not a or not b:
        return {}
    out = {}
    for k, av in a.items():
        bv = b.get(k)
        if isinstance(av, (int, float)) and isinstance(bv, (int, float)):
            d = bv - av
            if abs(d) > 1e-12:
                out[k] = d
    return out


def make_silence_wav_bytes(seconds: float = 1.0, rate: int = 16000) -> bytes:
    frames = int(seconds * rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"".join(struct.pack("<h", 0) for _ in range(frames)))
    return buf.getvalue()


def main() -> int:
    print("MW", MW)
    if not SUBKEY:
        print("Missing MW_SUBKEY environment variable.")
        print("Example:")
        print('  $env:MW_SUBKEY = "<YOUR_SUBKEY>"')
        print("Optional:")
        print('  $env:MW_BASE_URL = "http://127.0.0.1:5000"')
        print('  $env:MW_USER_ID  = "user1"')
        return 2
    s0 = snap()
    print("SNAP0", s0)

    with httpx.Client(timeout=120) as c:
        body = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 32}
        r = c.post(
            f"{MW}/v1/chat/completions", headers={**HEADERS, "Content-Type": "application/json"}, json=body
        )
        print("chat", r.status_code)
        if r.status_code == 200:
            j = r.json()
            print("  mw_added_cost", j.get("_mw_added_cost_usd"))
        else:
            print("  err", r.text[:200])

    s1 = snap()
    print("SNAP1", s1, "DIFF", diff(s0, s1))

    with httpx.Client(timeout=300) as c:
        img = {
            "model": "gemini-2.5-flash-image",
            "prompt": "test",
            "n": 1,
        }
        r = c.post(
            f"{MW}/v1/images/generations", headers={**HEADERS, "Content-Type": "application/json"}, json=img
        )
        print("images", r.status_code)
        if r.status_code == 200:
            j = r.json()
            print("  mw_added_cost", j.get("_mw_added_cost_usd"), "data_len", len(j.get("data", []) or []))
        else:
            print("  err", r.text[:200])

    s2 = snap()
    print("SNAP2", s2, "DIFF", diff(s1, s2))

    with httpx.Client(timeout=300) as c:
        tts = {"model": "gpt-4o-mini-tts", "input": "hi", "voice": "alloy", "format": "mp3"}
        with c.stream(
            "POST",
            f"{MW}/v1/audio/speech",
            headers={**HEADERS, "Content-Type": "application/json"},
            json=tts,
        ) as r:
            print("tts", r.status_code, "content-type", r.headers.get("content-type"))
            if r.status_code == 200:
                # Consume the stream fully to avoid client-abort errors on the server.
                data = r.read()
                print("  got_bytes", len(data))
            else:
                print("  err", r.text[:200])

    s3 = snap()
    print("SNAP3", s3, "DIFF", diff(s2, s3))

    wav_bytes = make_silence_wav_bytes(seconds=1.0)
    with httpx.Client(timeout=600) as c:
        files = {"file": ("silence.wav", wav_bytes, "audio/wav")}
        data = {"model": "gpt-4o-mini-transcribe"}
        r = c.post(f"{MW}/v1/audio/transcriptions", headers=HEADERS, data=data, files=files)
        print("stt", r.status_code)
        if r.status_code == 200:
            j = r.json()
            print("  keys", list(j.keys())[:10], "mw_added_cost", j.get("_mw_added_cost_usd"))
        else:
            print("  err", r.text[:200])

    s4 = snap()
    print("SNAP4", s4, "DIFF", diff(s3, s4))

    with httpx.Client(timeout=900) as c:
        vid = {"model": "sora-2", "prompt": "test", "duration_seconds": 4}
        r = c.post(
            f"{MW}/v1/video/generations", headers={**HEADERS, "Content-Type": "application/json"}, json=vid
        )
        print("video", r.status_code)
        if r.status_code == 200:
            j = r.json()
            print("  mw_added_cost", j.get("_mw_added_cost_usd"))
        else:
            print("  err", r.text[:200])

    s5 = snap()
    print("SNAP5", s5, "DIFF", diff(s4, s5))

    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
