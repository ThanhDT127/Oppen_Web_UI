"""
title: Xuất PDF (Wizard + chuẩn hoá Markdown → PDF)
author: Thanh + AI
version: 1.0.0
required_open_webui_version: 0.6.0
requirements: fpdf2,requests
"""

import asyncio
import base64
import datetime
import io
import logging
import re
from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel, Field

from fpdf import FPDF

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MarkdownPDF(FPDF):
    """Custom FPDF subclass for rendering Markdown to PDF."""

    def __init__(self, font_name="DejaVu", font_size=11, margin=15):
        super().__init__()
        self._font_name = font_name
        self._font_size = font_size
        self.set_auto_page_break(auto=True, margin=margin)
        self.set_margins(margin, margin, margin)

        # Register Unicode font
        # fpdf2 ships DejaVuSans built-in via add_font with uni=True
        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf", uni=True)
        self.add_font("DejaVu", "I", "DejaVuSans-Oblique.ttf", uni=True)
        self.add_font("DejaVu", "BI", "DejaVuSans-BoldOblique.ttf", uni=True)

    def header(self):
        pass

    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f"Trang {self.page_no()}/{{nb}}", align="C")


class Action:
    class Valves(BaseModel):
        # ---- UX ----
        show_status: bool = Field(default=True, description="Hiển thị status")
        show_confirmation: bool = Field(default=False, description="Hỏi xác nhận")
        min_wizard_seconds: float = Field(default=1.5, description="Giữ wizard tối thiểu (giây)")

        # ---- OpenWebUI ----
        openwebui_base_url: str = Field(
            default="", description="Base URL Open WebUI. Để trống = tự suy."
        )
        openwebui_chat_completions_path: str = Field(
            default="/api/chat/completions", description="Path chat completions"
        )
        timeout_sec: int = Field(default=120, description="Timeout gọi API")

        # ---- Normalize scope ----
        normalize_mode: str = Field(
            default="conversation_window",
            description="assistant_only | conversation_window",
        )
        context_window_messages: int = Field(default=14, description="Số messages gần nhất")
        drop_file_like_content: bool = Field(
            default=True, description="Loại base64/data URL"
        )

        # ---- Normalize prompt ----
        normalize_with_llm: bool = Field(default=True, description="Gọi LLM chuẩn hoá")
        normalize_instructions_vi: str = Field(
            default=(
                "Bạn là trợ lý chuẩn hoá nội dung.\n"
                "Nhiệm vụ: chuyển hội thoại thành VĂN BẢN Markdown chuẩn để xuất PDF.\n\n"
                "YÊU CẦU BẮT BUỘC:\n"
                "1) Trả về Markdown chuẩn, KHÔNG bọc trong ```.\n"
                "2) Dùng # cho tiêu đề chính, ## cho tiêu đề phụ.\n"
                "3) Dùng **bold**, *italic* cho nhấn mạnh.\n"
                "4) Dùng - hoặc * cho danh sách.\n"
                "5) Dùng bảng Markdown |col1|col2| nếu dữ liệu dạng bảng.\n"
                "6) Dùng > cho trích dẫn.\n"
                "7) Cấu trúc rõ ràng, chuyên nghiệp.\n"
                "8) Nếu người dùng yêu cầu cụ thể thì tuân thủ.\n"
            ),
            description="System prompt chuẩn hoá (VI)",
        )

        # ---- PDF output ----
        base_filename: str = Field(default="van_ban.pdf", description="Tên file")
        font_size_body: int = Field(default=11, description="Cỡ chữ body (pt)")
        font_size_h1: int = Field(default=18, description="Cỡ H1")
        font_size_h2: int = Field(default=15, description="Cỡ H2")
        font_size_h3: int = Field(default=13, description="Cỡ H3")
        page_margin: int = Field(default=15, description="Margin trang (mm)")

    def __init__(self):
        self.valves = self.Valves()

    # =========================================================
    # UI MODAL
    # =========================================================

    async def _ui_modal_open(self, __event_call__=None):
        if not __event_call__:
            return
        js = """
(() => {
  const ID = "owui_export_pdf_modal";
  if (document.getElementById(ID)) return;
  const overlay = document.createElement("div");
  overlay.id = ID;
  overlay.style.cssText = `
    position: fixed; inset: 0; z-index: 999999;
    background: rgba(0,0,0,0.45);
    display: flex; align-items: center; justify-content: center;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
  `;
  overlay.innerHTML = `
    <div style="width: min(620px, 94vw); background: #fff; border-radius: 14px;
      box-shadow: 0 16px 60px rgba(0,0,0,.25); padding: 18px;">
      <div style="display:flex; gap:12px; align-items:flex-start;">
        <div id="owui_pdf_spinner" style="width:34px;height:34px;border-radius:999px;
          border:3px solid #d1d5db;border-top-color:#dc2626;
          animation:spin 0.9s linear infinite;margin-top:2px;"></div>
        <div style="flex:1">
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
            <div>
              <div style="font-size:16px;font-weight:700;color:#111827;" id="owui_pdf_title">Đang xuất PDF</div>
              <div style="font-size:13px;color:#4b5563;margin-top:4px;" id="owui_pdf_subtitle">Khởi động...</div>
            </div>
            <div style="font-size:12px;color:#6b7280;margin-top:2px;"><span id="owui_pdf_timer">0</span>s</div>
          </div>
          <div style="margin-top:12px;padding:10px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;">
            <div style="font-size:12px;color:#374151;font-weight:600;margin-bottom:6px;">Tiến trình</div>
            <ol style="margin:0;padding-left:18px;font-size:12.5px;color:#111827;line-height:1.65" id="owui_pdf_steps">
              <li>Khởi tạo</li>
            </ol>
          </div>
          <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:14px;">
            <button id="owui_pdf_close" disabled
              style="opacity:.6;cursor:not-allowed;padding:8px 12px;border-radius:10px;border:1px solid #e5e7eb;background:#fff;">
              Đóng
            </button>
          </div>
          <div style="font-size:11px;color:#6b7280;margin-top:10px;">
            Thao tác có thể mất 10–60 giây.
          </div>
        </div>
      </div>
    </div>
  `;
  const style = document.createElement("style");
  style.textContent = \`@keyframes spin { to { transform: rotate(360deg); } }\`;
  overlay.appendChild(style);
  let sec = 0;
  const timerEl = overlay.querySelector("#owui_pdf_timer");
  const t = setInterval(() => { sec++; if(timerEl) timerEl.textContent = String(sec); }, 1000);
  overlay.dataset.timer = String(t);
  document.body.appendChild(overlay);
})();
"""
        await __event_call__({"type": "execute", "data": {"code": js}})

    async def _ui_modal_update(self, __event_call__=None, title=None, subtitle=None,
                                steps=None, done_ok=None, error_text=None):
        if not __event_call__:
            return

        def _js(s):
            return s.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")

        steps_js = "null"
        if isinstance(steps, list):
            steps_js = "[" + ",".join([f"`{_js(x)}`" for x in steps]) + "]"
        t_js = f"`{_js(title)}`" if title else "null"
        st_js = f"`{_js(subtitle)}`" if subtitle else "null"
        e_js = f"`{_js(error_text)}`" if error_text else "null"
        d_js = "true" if done_ok is True else ("false" if done_ok is False else "null")

        js = f"""
(() => {{
  const o = document.getElementById("owui_export_pdf_modal");
  if (!o) return;
  const t={t_js}, st={st_js}, steps={steps_js}, done={d_js}, err={e_js};
  if(t) o.querySelector("#owui_pdf_title").textContent=t;
  if(st) o.querySelector("#owui_pdf_subtitle").textContent=st;
  if(Array.isArray(steps)) o.querySelector("#owui_pdf_steps").innerHTML=steps.map(s=>`<li>${{s}}</li>`).join("");
  if(done!==null) {{
    const tid=o.dataset.timer; if(tid) try{{clearInterval(Number(tid));}}catch(e){{}}
    const btn=o.querySelector("#owui_pdf_close");
    btn.disabled=false;btn.style.opacity="1";btn.style.cursor="pointer";
    btn.onclick=()=>o.remove();
    const sp=o.querySelector("#owui_pdf_spinner");
    if(sp){{sp.style.animation="none";
      sp.style.borderTopColor=done?"#16a34a":"#dc2626";
      sp.style.borderColor=done?"#86efac":"#fecaca";
      sp.style.background=done?"#dcfce7":"#fee2e2";}}
    if(done===true){{o.querySelector("#owui_pdf_title").textContent="Xuất PDF thành công";
      o.querySelector("#owui_pdf_subtitle").textContent="File đang tải xuống.";}}
    else{{o.querySelector("#owui_pdf_title").textContent="Xuất PDF thất bại";
      o.querySelector("#owui_pdf_subtitle").textContent=err||"Có lỗi xảy ra.";}}
  }}
}})();
"""
        await __event_call__({"type": "execute", "data": {"code": js}})

    # =========================================================
    # Context helpers
    # =========================================================

    def _get_current_model_id(self, body, __model__=None):
        m = body.get("model")
        if isinstance(m, str) and m.strip():
            return m.strip()
        if isinstance(__model__, dict):
            for k in ("id", "model", "name"):
                v = __model__.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
        return None

    def _get_messages_window(self, body):
        msgs = body.get("messages", [])
        if not isinstance(msgs, list):
            return []
        n = int(self.valves.context_window_messages) if self.valves.context_window_messages else 0
        return msgs[-n:] if n > 0 else msgs

    def _sanitize_message_content(self, content):
        if content is None:
            return ""
        s = content if isinstance(content, str) else str(content)
        if self.valves.drop_file_like_content:
            if "data:" in s and "base64" in s:
                s = re.sub(r"data:[^\s]+;base64,[A-Za-z0-9+/=]+", "[DATA_URL_REMOVED]", s)
            s = re.sub(r"[A-Za-z0-9+/=]{1500,}", "[BASE64_REMOVED]", s)
        if len(s) > 6000:
            s = s[:6000] + "...[TRUNCATED]"
        return s

    def _build_normalize_user_prompt(self, body):
        mode = (self.valves.normalize_mode or "conversation_window").strip()
        if mode == "assistant_only":
            last_assistant = ""
            for m in reversed(body.get("messages", [])):
                if isinstance(m, dict) and m.get("role") == "assistant":
                    last_assistant = self._sanitize_message_content(m.get("content"))
                    if last_assistant.strip():
                        break
            return (
                "Chuẩn hoá nội dung trả lời dưới đây thành Markdown đẹp.\n\n"
                f"BOT:\n{last_assistant}"
            )
        window = self._get_messages_window(body)
        lines = []
        for m in window:
            if not isinstance(m, dict):
                continue
            role = m.get("role", "")
            c = self._sanitize_message_content(m.get("content"))
            if not c.strip():
                continue
            lines.append(f"[{role.upper()}]\n{c}")
        return (
            "Dưới đây là hội thoại. Tạo văn bản Markdown chuyên nghiệp từ nội dung.\n\n"
            + "\n\n".join(lines)
        )

    # =========================================================
    # OpenWebUI API
    # =========================================================

    def _resolve_base_url(self, __request__=None):
        if self.valves.openwebui_base_url.strip():
            return self.valves.openwebui_base_url.strip().rstrip("/")
        if __request__:
            try:
                base = str(__request__.base_url).rstrip("/")
                if base:
                    return base
            except Exception:
                pass
            try:
                origin = __request__.headers.get("origin")
                if origin:
                    return origin.rstrip("/")
                host = __request__.headers.get("host")
                proto = __request__.headers.get("x-forwarded-proto", "http")
                if host:
                    return f"{proto}://{host}".rstrip("/")
            except Exception:
                pass
        return None

    def _auth_headers(self, __request__=None):
        h = {"Content-Type": "application/json"}
        if not __request__:
            return h
        try:
            auth = __request__.headers.get("authorization")
            if auth:
                h["Authorization"] = auth
        except Exception:
            pass
        try:
            cookie = __request__.headers.get("cookie")
            if cookie and "Authorization" not in h:
                h["Cookie"] = cookie
        except Exception:
            pass
        return h

    async def _call_llm(self, body, __model__=None, __request__=None):
        base = self._resolve_base_url(__request__)
        if not base:
            raise ValueError("Không xác định được Open WebUI base_url.")
        url = base + self.valves.openwebui_chat_completions_path
        headers = self._auth_headers(__request__)
        model_id = self._get_current_model_id(body, __model__)
        if not model_id:
            raise ValueError("Không xác định được model.")
        user_prompt = self._build_normalize_user_prompt(body)
        messages = [
            {"role": "system", "content": self.valves.normalize_instructions_vi},
            {"role": "user", "content": user_prompt},
        ]
        payload = {"model": model_id, "messages": messages, "stream": False}

        def _do():
            return requests.post(url, headers=headers, json=payload,
                                 timeout=int(self.valves.timeout_sec))
        resp = await asyncio.to_thread(_do)
        if resp.status_code >= 400:
            raise ValueError(f"LLM failed: HTTP {resp.status_code}")
        data = resp.json()
        content = None
        try:
            content = data["choices"][0]["message"]["content"]
        except Exception:
            pass
        if not content:
            content = data.get("message", {}).get("content") or ""
        if not content.strip():
            raise ValueError("LLM không trả về nội dung.")
        return content

    # =========================================================
    # Markdown helpers
    # =========================================================

    def _is_table_line(self, line):
        return line.count("|") >= 2 and len(line.strip()) >= 3

    def _is_separator_line(self, line):
        s = line.strip().strip("|").strip()
        return bool(s) and all(ch in "-: |" for ch in line.strip()) and "-" in line

    def _split_row(self, line):
        return [c.strip() for c in line.strip().strip("|").split("|")]

    # =========================================================
    # Markdown → PDF builder
    # =========================================================

    def _render_inline_text(self, pdf, text):
        """Parse and render inline Markdown (bold, italic, code) using write()."""
        # Simple inline parser
        parts = []
        pattern = re.compile(
            r'(\*\*\*(.+?)\*\*\*)'
            r'|(\*\*(.+?)\*\*)'
            r'|(\*(.+?)\*)'
            r'|(`([^`]+)`)'
            r'|([^*`]+)'
        )
        for m in pattern.finditer(text):
            if m.group(2):
                parts.append(("BI", m.group(2)))
            elif m.group(4):
                parts.append(("B", m.group(4)))
            elif m.group(6):
                parts.append(("I", m.group(6)))
            elif m.group(8):
                parts.append(("CODE", m.group(8)))
            elif m.group(9):
                parts.append(("", m.group(9)))

        for style, txt in parts:
            if style == "CODE":
                pdf.set_font("DejaVu", "", self.valves.font_size_body - 1)
                pdf.set_text_color(199, 37, 78)
                pdf.write(5, txt)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("DejaVu", "", self.valves.font_size_body)
            else:
                pdf.set_font("DejaVu", style, self.valves.font_size_body)
                pdf.write(5, txt)
                pdf.set_font("DejaVu", "", self.valves.font_size_body)

    def _build_pdf_bytes(self, markdown_text: str) -> bytes:
        pdf = MarkdownPDF(
            font_size=self.valves.font_size_body,
            margin=self.valves.page_margin,
        )
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_font("DejaVu", "", self.valves.font_size_body)

        lines = markdown_text.splitlines()
        i = 0
        n = len(lines)
        in_code_block = False
        code_lines = []

        while i < n:
            line = lines[i]
            stripped = line.strip()

            # Code block
            if stripped.startswith("```"):
                if in_code_block:
                    # Render code block
                    pdf.set_fill_color(245, 245, 245)
                    pdf.set_font("DejaVu", "", 9)
                    pdf.set_text_color(30, 30, 30)
                    code_text = "\n".join(code_lines)
                    # Calculate height
                    x = pdf.get_x()
                    w = pdf.w - pdf.l_margin - pdf.r_margin
                    pdf.multi_cell(w, 4.5, code_text, border=1, fill=True)
                    pdf.set_font("DejaVu", "", self.valves.font_size_body)
                    pdf.set_text_color(0, 0, 0)
                    pdf.ln(3)
                    code_lines = []
                    in_code_block = False
                else:
                    in_code_block = True
                    code_lines = []
                i += 1
                continue

            if in_code_block:
                code_lines.append(line)
                i += 1
                continue

            # Empty line
            if not stripped:
                pdf.ln(3)
                i += 1
                continue

            # Headings
            if stripped.startswith("### "):
                pdf.ln(4)
                pdf.set_font("DejaVu", "B", self.valves.font_size_h3)
                pdf.set_text_color(31, 78, 121)
                pdf.multi_cell(0, 7, stripped[4:])
                pdf.set_font("DejaVu", "", self.valves.font_size_body)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(2)
                i += 1
                continue

            if stripped.startswith("## "):
                pdf.ln(5)
                pdf.set_font("DejaVu", "B", self.valves.font_size_h2)
                pdf.set_text_color(31, 78, 121)
                pdf.multi_cell(0, 7, stripped[3:])
                pdf.set_font("DejaVu", "", self.valves.font_size_body)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(2)
                i += 1
                continue

            if stripped.startswith("# "):
                pdf.ln(6)
                pdf.set_font("DejaVu", "B", self.valves.font_size_h1)
                pdf.set_text_color(13, 55, 107)
                pdf.multi_cell(0, 9, stripped[2:])
                pdf.set_font("DejaVu", "", self.valves.font_size_body)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(3)
                i += 1
                continue

            # Blockquote
            if stripped.startswith("> "):
                pdf.set_text_color(85, 85, 85)
                pdf.set_font("DejaVu", "I", self.valves.font_size_body)
                pdf.set_x(pdf.l_margin + 10)
                pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 10, 5, stripped[2:])
                pdf.set_font("DejaVu", "", self.valves.font_size_body)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(2)
                i += 1
                continue

            # Horizontal rule
            if stripped in ("---", "***", "___"):
                y = pdf.get_y()
                pdf.set_draw_color(200, 200, 200)
                pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
                pdf.ln(5)
                i += 1
                continue

            # Table
            if (self._is_table_line(stripped)
                    and i + 1 < n
                    and self._is_separator_line(lines[i + 1].strip())):
                headers = self._split_row(stripped)
                i += 2
                data_rows = []
                while i < n and self._is_table_line(lines[i].strip()):
                    data_rows.append(self._split_row(lines[i].strip()))
                    i += 1

                num_cols = len(headers)
                if num_cols == 0:
                    continue

                # Calculate column widths
                avail_w = pdf.w - pdf.l_margin - pdf.r_margin
                col_w = avail_w / num_cols

                # Header
                pdf.set_font("DejaVu", "B", self.valves.font_size_body)
                pdf.set_fill_color(31, 78, 121)
                pdf.set_text_color(255, 255, 255)
                for ci, h in enumerate(headers):
                    pdf.cell(col_w, 7, h[:30], border=1, fill=True, align="C")
                pdf.ln()

                # Data
                pdf.set_font("DejaVu", "", self.valves.font_size_body)
                pdf.set_text_color(0, 0, 0)
                for ri, row in enumerate(data_rows):
                    if ri % 2 == 0:
                        pdf.set_fill_color(242, 247, 251)
                    else:
                        pdf.set_fill_color(255, 255, 255)
                    for ci in range(num_cols):
                        val = row[ci] if ci < len(row) else ""
                        pdf.cell(col_w, 6, val[:40], border=1, fill=True)
                    pdf.ln()

                pdf.ln(3)
                continue

            # Unordered list
            if re.match(r'^[\-\*\+]\s', stripped):
                text = re.sub(r'^[\-\*\+]\s+', '', stripped)
                pdf.set_x(pdf.l_margin + 5)
                pdf.write(5, "• ")
                self._render_inline_text(pdf, text)
                pdf.ln(6)
                i += 1
                continue

            # Ordered list
            ol_match = re.match(r'^(\d+)\.\s+(.+)', stripped)
            if ol_match:
                num = ol_match.group(1)
                text = ol_match.group(2)
                pdf.set_x(pdf.l_margin + 5)
                pdf.write(5, f"{num}. ")
                self._render_inline_text(pdf, text)
                pdf.ln(6)
                i += 1
                continue

            # Regular paragraph
            self._render_inline_text(pdf, stripped)
            pdf.ln(6)
            i += 1

        # Footer timestamp
        pdf.ln(10)
        pdf.set_font("DejaVu", "I", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 5,
                 f"Tạo lúc: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                 align="R")

        return pdf.output()

    # =========================================================
    # Main action
    # =========================================================

    async def action(self, body, __user__=None, __event_emitter__=None,
                     __event_call__=None, __model__=None, __request__=None, __id__=None):
        wizard_start = asyncio.get_event_loop().time()
        steps = [
            "1) Chuẩn hoá nội dung thành Markdown",
            "2) Chuyển Markdown → PDF",
            "3) Tải file xuống trình duyệt",
        ]

        try:
            if self.valves.show_confirmation and __event_call__:
                ok = await __event_call__({
                    "type": "confirmation",
                    "data": {"title": "Xuất PDF", "message": "Bắt đầu xuất PDF?"},
                })
                if not ok:
                    if __event_emitter__:
                        await __event_emitter__({"type": "notification",
                            "data": {"type": "info", "content": "Đã huỷ xuất PDF."}})
                    return body

            await self._ui_modal_open(__event_call__)
            await self._ui_modal_update(__event_call__, subtitle="Đang khởi tạo...", steps=steps)

            if __event_emitter__ and self.valves.show_status:
                await __event_emitter__({"type": "status",
                    "data": {"description": "Đang xuất PDF...", "done": False}})

            # Step 1: Normalize
            await self._ui_modal_update(__event_call__,
                subtitle="Bước 1/3: Chuẩn hoá nội dung...", steps=steps)
            if self.valves.normalize_with_llm:
                markdown_text = await self._call_llm(body, __model__, __request__)
            else:
                markdown_text = ""
                for m in reversed(body.get("messages", [])):
                    if isinstance(m, dict) and m.get("role") == "assistant":
                        markdown_text = m.get("content", "")
                        if markdown_text.strip():
                            break

            # Step 2: Build PDF
            await self._ui_modal_update(__event_call__,
                subtitle="Bước 2/3: Đang tạo PDF...", steps=steps)
            pdf_bytes = self._build_pdf_bytes(markdown_text)

            # Step 3: Download
            await self._ui_modal_update(__event_call__,
                subtitle="Bước 3/3: Đang tải file xuống...", steps=steps)

            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{ts}_{self.valves.base_filename}"
            b64 = base64.b64encode(pdf_bytes).decode("utf-8")

            js = f"""
try {{
  const b = atob("{b64}");
  const bytes = new Uint8Array(b.length);
  for(let i=0;i<b.length;i++) bytes[i]=b.charCodeAt(i);
  const blob = new Blob([bytes],{{type:"application/pdf"}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href=url; a.download="{filename}";
  document.body.appendChild(a); a.click();
  URL.revokeObjectURL(url); a.remove();
}} catch(e) {{ console.error("Download PDF failed",e); }}
"""
            if __event_call__:
                await __event_call__({"type": "execute", "data": {"code": js}})

            elapsed = asyncio.get_event_loop().time() - wizard_start
            if elapsed < self.valves.min_wizard_seconds:
                await asyncio.sleep(self.valves.min_wizard_seconds - elapsed)

            await self._ui_modal_update(__event_call__, done_ok=True, steps=steps)

            if __event_emitter__ and self.valves.show_status:
                await __event_emitter__({"type": "status",
                    "data": {"description": "Hoàn tất xuất PDF.", "done": True}})
                await __event_emitter__({"type": "notification",
                    "data": {"type": "success", "content": "Đã xuất PDF thành công."}})
            return body

        except Exception as e:
            logger.exception("Lỗi xuất PDF: %s", str(e))
            elapsed = asyncio.get_event_loop().time() - wizard_start
            if elapsed < self.valves.min_wizard_seconds:
                await asyncio.sleep(self.valves.min_wizard_seconds - elapsed)
            await self._ui_modal_update(__event_call__, done_ok=False,
                error_text=str(e), steps=steps)
            if __event_emitter__:
                await __event_emitter__({"type": "status",
                    "data": {"description": f"Lỗi: {e}", "done": True}})
                await __event_emitter__({"type": "notification",
                    "data": {"type": "error", "content": f"Lỗi xuất PDF: {e}"}})
            return None
