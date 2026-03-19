"""
WhatsApp Identifier — Settings GUI (Python tkinter) v4.0
Janela de configuração para o WhatsApp Identifier Desktop.
Lê e escreve config.ini, compartilhado com o script AHK.
"""

import tkinter as tk
import configparser
import ctypes
import os
import sys

# ── DPI awareness (Windows 10+) ──────────────────────────────────────
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# ── Design Tokens ────────────────────────────────────────────────────
WIDTH = 380
HEIGHT = 480

# Surface
BG_PRIMARY    = "#111B21"
BG_SECONDARY  = "#1A2730"
BG_TERTIARY   = "#0B141A"
BG_ELEVATED   = "#233040"

# Brand
GREEN_PRIMARY = "#00A884"
GREEN_HOVER   = "#00C49A"
GREEN_DARK    = "#007A63"
GREEN_BUBBLE  = "#005C4B"

# Text
TEXT_PRIMARY   = "#E9EDEF"
TEXT_SECONDARY = "#8696A0"
TEXT_MUTED     = "#54697A"

# Border
BORDER_COLOR  = "#2A3942"

# Feedback
ERROR_BG = "#3A1A1A"
ERROR_FG = "#FF6B6B"

# Shape
CARD_RADIUS   = 12
BUTTON_RADIUS = 12

FONT_FAMILY = "Segoe UI"
MAX_NAME_LEN = 30

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "config.ini")


# ── Config I/O ────────────────────────────────────────────────────────
def read_config():
    config = configparser.ConfigParser()
    for enc in ("utf-16", "utf-8", "mbcs"):
        try:
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE, encoding=enc)
            if config.has_section("Settings"):
                break
        except (UnicodeDecodeError, UnicodeError, configparser.Error):
            config = configparser.ConfigParser()

    name = config.get("Settings", "Name", fallback="")
    active = config.get("Settings", "Active", fallback="0") == "1"

    # Privacy
    priv_enabled = config.get("Privacy", "PrivacyEnabled", fallback="0") == "1"
    blur_intensity = int(config.get("Privacy", "BlurIntensity", fallback="8"))
    overlay_opacity = int(config.get("Privacy", "OverlayOpacity", fallback="200"))
    raw_color = config.get("Privacy", "OverlayColor", fallback="1A1A2E")
    overlay_color = "#" + raw_color.lstrip("#")
    hide_on_hover = config.get("Privacy", "HideOnHover", fallback="1") == "1"
    hide_on_focus = config.get("Privacy", "HideOnFocus", fallback="1") == "1"
    idle_enabled = config.get("Privacy", "IdleBlurEnabled", fallback="0") == "1"
    idle_seconds = int(config.get("Privacy", "IdleBlurSeconds", fallback="30"))
    debug_port = int(config.get("Privacy", "DebugPort", fallback="9351"))

    return {
        "name": name, "active": active,
        "priv_enabled": priv_enabled, "blur_intensity": blur_intensity,
        "overlay_opacity": overlay_opacity,
        "overlay_color": overlay_color, "hide_on_hover": hide_on_hover,
        "hide_on_focus": hide_on_focus, "idle_enabled": idle_enabled,
        "idle_seconds": idle_seconds, "debug_port": debug_port,
    }


def write_config(cfg: dict):
    config = configparser.ConfigParser()
    config["Settings"] = {
        "Name": cfg["name"],
        "Active": "1" if cfg["active"] else "0",
    }
    with open(CONFIG_FILE, "w", encoding="utf-16") as f:
        config.write(f)


# ── Posição do work area (sem taskbar) ────────────────────────────────
def get_work_area():
    try:
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
        return rect.right, rect.bottom
    except Exception:
        return None, None


# ── Rounded rectangle helper ──────────────────────────────────────────
def rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def create_rounded_card(parent, width, height, radius=CARD_RADIUS, bg=BG_SECONDARY, border_color=BORDER_COLOR):
    canvas = tk.Canvas(parent, width=width, height=height,
                       bg=BG_PRIMARY, highlightthickness=0, bd=0)
    rounded_rect(canvas, 0, 0, width, height, radius, fill=border_color, outline="")
    rounded_rect(canvas, 1, 1, width - 1, height - 1, radius - 1, fill=bg, outline="")
    return canvas


# ══════════════════════════════════════════════════════════════════════
class SettingsWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WA Identificador")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG_PRIMARY)
        self.root.resizable(False, False)

        # State
        cfg = read_config()
        self.name = cfg["name"]
        self.active = cfg["active"]

        self._drag_x = 0
        self._drag_y = 0

        # Position
        self._position_window()

        # Build UI
        self._build_header()
        self._build_content()
        self._build_footer()

        # Bordas arredondadas
        self.root.after(10, self._apply_rounded_window)
        self.root.after(100, lambda: (self.root.focus_force(), self.name_entry.focus_set()))

    # ── Bordas arredondadas da janela ─────────────────────────────────
    def _apply_rounded_window(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, WIDTH + 1, HEIGHT + 1, 20, 20)
            ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)
        except Exception:
            pass

    # ── Posicionamento ────────────────────────────────────────────────
    def _position_window(self):
        wa_right, wa_bottom = get_work_area()
        if wa_right and wa_bottom:
            x = wa_right - WIDTH - 12
            y = wa_bottom - HEIGHT - 12
        else:
            x = self.root.winfo_screenwidth() - WIDTH - 12
            y = self.root.winfo_screenheight() - HEIGHT - 60
        self.root.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")

    # ── Header ────────────────────────────────────────────────────────
    def _build_header(self):
        header_h = 90
        header = tk.Canvas(self.root, width=WIDTH, height=header_h,
                           highlightthickness=0, bg=BG_PRIMARY)
        header.pack(fill="x")

        # Green gradient background with rounded top corners
        r = 16
        pts = [0 + r, 0, WIDTH - r, 0, WIDTH, 0, WIDTH, 0 + r,
               WIDTH, header_h, WIDTH, header_h, 0, header_h, 0, header_h,
               0, 0 + r, 0, 0]
        header.create_polygon(pts, smooth=True, fill=GREEN_PRIMARY, outline="")

        # Subtle gradient overlay (right side darker)
        header.create_rectangle(WIDTH // 2, 0, WIDTH, header_h, fill=GREEN_DARK,
                                outline="", stipple="gray25")

        # Decorative circles
        header.create_oval(WIDTH - 50, -30, WIDTH + 40, 65,
                           fill="#FFFFFF", outline="", stipple="gray12")
        header.create_oval(WIDTH - 80, 40, WIDTH - 10, 115,
                           fill="#FFFFFF", outline="", stipple="gray12")

        # App icon — WhatsApp logo from extension icons
        icon_x, icon_y = 20, 18
        icon_size = 44
        rounded_rect(header, icon_x, icon_y, icon_x + icon_size, icon_y + icon_size,
                      10, fill="#33997F", outline="")
        icon_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                                  "icon.png")
        try:
            self._header_icon = tk.PhotoImage(file=icon_path)
            # Subsample to ~24px (48/2)
            self._header_icon = self._header_icon.subsample(2, 2)
            header.create_image(icon_x + icon_size // 2, icon_y + icon_size // 2,
                                image=self._header_icon)
        except Exception:
            # Fallback to text if icon not found
            header.create_text(icon_x + icon_size // 2, icon_y + icon_size // 2,
                               text="WA", font=(FONT_FAMILY, 12, "bold"), fill="white")

        # Title + subtitle
        tx = icon_x + icon_size + 14
        header.create_text(tx, 32, text="WA Identificador", anchor="w",
                           font=(FONT_FAMILY, 15, "bold"), fill="white")
        header.create_text(tx, 54, text="Identifique suas mensagens", anchor="w",
                           font=(FONT_FAMILY, 9), fill="#B8E8D8")

        # Status badge
        badge_y = 72
        badge_text = "Ativo" if self.active else "Inativo"
        self._badge_bg = rounded_rect(header, 20, badge_y - 9, 90, badge_y + 9,
                                       9, fill="#2D8C73", outline="")
        # Dot indicator
        dot_color = "#4ADE80" if self.active else TEXT_SECONDARY
        self._badge_dot = header.create_oval(28, badge_y - 3, 34, badge_y + 3,
                                              fill=dot_color, outline="")
        self._badge_label = header.create_text(38, badge_y, text=badge_text,
                                                anchor="w", font=(FONT_FAMILY, 9, "bold"),
                                                fill="white")

        # Close button
        close_bg = rounded_rect(header, WIDTH - 44, 22, WIDTH - 14, 52, 8,
                                fill="#33997F", outline="")
        close_text = header.create_text(WIDTH - 29, 37, text="\u2715",
                                         font=(FONT_FAMILY, 10), fill="white")

        for item in (close_bg, close_text):
            header.tag_bind(item, "<Enter>",
                            lambda e: header.itemconfig(close_bg, fill="#4DB89E"))
            header.tag_bind(item, "<Leave>",
                            lambda e: header.itemconfig(close_bg, fill="#33997F"))
            header.tag_bind(item, "<Button-1>", lambda e: self.root.destroy())

        header.bind("<ButtonPress-1>", self._start_drag)
        header.bind("<B1-Motion>", self._on_drag)
        self._header = header

    def _update_badge(self):
        h = self._header
        badge_text = "Ativo" if self.active else "Inativo"
        dot_color = "#4ADE80" if self.active else TEXT_SECONDARY
        h.itemconfig(self._badge_label, text=badge_text)
        h.itemconfig(self._badge_dot, fill=dot_color)

    def _start_drag(self, event):
        if event.x > WIDTH - 48:
            return
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        if event.x > WIDTH - 48:
            return
        x = self.root.winfo_x() + event.x - self._drag_x
        y = self.root.winfo_y() + event.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # ── Content ──────────────────────────────────────────────────────
    def _build_content(self):
        inner = tk.Frame(self.root, bg=BG_PRIMARY)
        inner.pack(fill="both", expand=True, padx=16, pady=(16, 12))

        self._build_name_field(inner)
        self._build_toggle(inner)
        self._build_preview(inner)
        self._build_save_button(inner)
        self._build_status(inner)

    # ── Campo de nome ─────────────────────────────────────────────────
    def _build_name_field(self, parent):
        card_w = WIDTH - 46

        lbl_frame = tk.Frame(parent, bg=BG_PRIMARY)
        lbl_frame.pack(fill="x", pady=(0, 6))
        tk.Label(lbl_frame, text="\u2022  NOME IDENTIFICADOR",
                 font=(FONT_FAMILY, 8, "bold"), fg=TEXT_SECONDARY,
                 bg=BG_PRIMARY).pack(side="left")

        card_canvas = create_rounded_card(parent, card_w, 50, radius=CARD_RADIUS)
        card_canvas.pack(fill="x", pady=(0, 12))

        self.name_entry = tk.Entry(card_canvas, font=(FONT_FAMILY, 13),
                                    bg=BG_SECONDARY, fg=TEXT_PRIMARY,
                                    insertbackground=GREEN_PRIMARY,
                                    relief="flat", bd=0)
        card_canvas.create_window(14, 25, window=self.name_entry,
                                   anchor="w", width=card_w - 80)
        self.name_entry.insert(0, self.name)

        self.char_label = tk.Label(card_canvas, text=f"{len(self.name)}/{MAX_NAME_LEN}",
                                    font=(FONT_FAMILY, 8), fg=TEXT_MUTED, bg=BG_SECONDARY)
        card_canvas.create_window(card_w - 14, 25, window=self.char_label, anchor="e")

        self.name_entry.bind("<KeyRelease>", self._on_name_change)
        self.name_entry.bind("<Return>", lambda e: self._save())

        sv = tk.StringVar()
        sv.trace_add("write", lambda *_: self._enforce_max_length(sv))
        self.name_entry.configure(textvariable=sv)
        sv.set(self.name)
        self._name_var = sv

    def _enforce_max_length(self, sv):
        val = sv.get()
        if len(val) > MAX_NAME_LEN:
            sv.set(val[:MAX_NAME_LEN])

    def _on_name_change(self, event=None):
        length = len(self.name_entry.get())
        self.char_label.configure(
            text=f"{length}/{MAX_NAME_LEN}",
            fg="#F59E0B" if length > 24 else TEXT_MUTED)
        self._update_preview()

    # ── Toggle ────────────────────────────────────────────────────────
    def _build_toggle(self, parent):
        card_w = WIDTH - 46
        card_h = 58

        card_canvas = create_rounded_card(parent, card_w, card_h, radius=CARD_RADIUS)
        card_canvas.pack(fill="x", pady=(0, 12))

        left = tk.Frame(card_canvas, bg=BG_SECONDARY)
        card_canvas.create_window(16, card_h // 2, window=left, anchor="w")

        tk.Label(left, text="Identificador", font=(FONT_FAMILY, 13),
                 fg=TEXT_PRIMARY, bg=BG_SECONDARY).pack(anchor="w")
        self.toggle_subtitle = tk.Label(
            left, text="Ativo" if self.active else "Inativo",
            font=(FONT_FAMILY, 9, "bold"),
            fg=GREEN_PRIMARY if self.active else TEXT_SECONDARY,
            bg=BG_SECONDARY)
        self.toggle_subtitle.pack(anchor="w")

        self.toggle_canvas = tk.Canvas(card_canvas, width=48, height=28,
                                        bg=BG_SECONDARY, highlightthickness=0,
                                        cursor="hand2")
        card_canvas.create_window(card_w - 20, card_h // 2,
                                   window=self.toggle_canvas, anchor="e")
        self.toggle_canvas.bind("<Button-1>", self._toggle_active)
        self._draw_toggle()

    def _draw_toggle(self):
        c = self.toggle_canvas
        c.delete("all")
        bg = GREEN_PRIMARY if self.active else "#3B4A54"
        knob_cx = 35 if self.active else 13
        # Track
        c.create_oval(0, 0, 28, 28, fill=bg, outline="")
        c.create_oval(20, 0, 48, 28, fill=bg, outline="")
        c.create_rectangle(14, 0, 34, 28, fill=bg, outline="")
        # Knob
        c.create_oval(knob_cx - 11, 3, knob_cx + 11, 25, fill="#E9EDEF", outline="")

    def _toggle_active(self, event=None):
        self.active = not self.active
        self._draw_toggle()
        self.toggle_subtitle.configure(
            text="Ativo" if self.active else "Inativo",
            fg=GREEN_PRIMARY if self.active else TEXT_SECONDARY)
        self._update_preview()
        self._update_badge()

    # ── Preview ───────────────────────────────────────────────────────
    def _build_preview(self, parent):
        card_w = WIDTH - 46
        card_h = 105

        card_canvas = create_rounded_card(parent, card_w, card_h, radius=CARD_RADIUS)
        card_canvas.pack(fill="x", pady=(0, 14))

        # Header area
        card_canvas.create_text(14, 16, text="\u2022  PREVIEW DA MENSAGEM", anchor="w",
                                font=(FONT_FAMILY, 8, "bold"), fill=TEXT_SECONDARY)
        card_canvas.create_line(10, 32, card_w - 10, 32, fill=BORDER_COLOR)

        self.preview_canvas = tk.Canvas(card_canvas, width=card_w - 8, height=66,
                                         bg=BG_TERTIARY, highlightthickness=0)
        card_canvas.create_window(card_w // 2, 68, window=self.preview_canvas, anchor="center")
        self._update_preview()

    def _update_preview(self):
        c = self.preview_canvas
        c.delete("all")
        cw = int(c.cget("width"))
        name = self.name_entry.get().strip() or "Nome"

        if self.active:
            bx1, by1, bx2, by2 = cw - 215, 4, cw - 8, 62
            rounded_rect(c, bx1, by1, bx2, by2, 8, fill=GREEN_BUBBLE)
            c.create_polygon(bx2, by1, bx2 + 7, by1, bx2, by1 + 9,
                             fill=GREEN_BUBBLE, outline="")
            c.create_text(bx1 + 10, by1 + 15, text=f"{name}:", anchor="w",
                          font=(FONT_FAMILY, 10, "bold"), fill=TEXT_PRIMARY)
            c.create_text(bx1 + 10, by1 + 35, text="Sua mensagem aqui...", anchor="w",
                          font=(FONT_FAMILY, 10), fill=TEXT_PRIMARY)
            c.create_text(bx2 - 6, by2 - 8, text="agora \u2713\u2713", anchor="e",
                          font=(FONT_FAMILY, 7), fill=TEXT_MUTED)
        else:
            bx1, by1, bx2, by2 = cw - 195, 6, cw - 8, 60
            rounded_rect(c, bx1, by1, bx2, by2, 8, fill="#1A2E28")
            c.create_text(bx1 + 10, (by1 + by2) // 2, text="Sua mensagem aqui...",
                          anchor="w", font=(FONT_FAMILY, 10), fill=TEXT_MUTED)

    # ── Botão Salvar ──────────────────────────────────────────────────
    def _build_save_button(self, parent):
        card_w = WIDTH - 46
        btn_h = 46

        self.save_canvas = tk.Canvas(parent, width=card_w, height=btn_h,
                                      bg=BG_PRIMARY, highlightthickness=0, cursor="hand2")
        self.save_canvas.pack(fill="x")

        self._save_bg = rounded_rect(self.save_canvas, 0, 0, card_w, btn_h,
                                      BUTTON_RADIUS, fill=GREEN_PRIMARY, outline="")
        self._save_text = self.save_canvas.create_text(
            card_w // 2, btn_h // 2,
            text="\u2713  Salvar",
            font=(FONT_FAMILY, 13, "bold"), fill="white")

        self.save_canvas.bind("<Button-1>", lambda e: self._save())
        self.save_canvas.bind("<Enter>", lambda e: self.save_canvas.itemconfig(
            self._save_bg, fill=GREEN_HOVER))
        self.save_canvas.bind("<Leave>", lambda e: self.save_canvas.itemconfig(
            self._save_bg, fill=GREEN_PRIMARY))

    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            self._show_status("Digite um nome!", error=True)
            self.name_entry.focus_set()
            return

        write_config({"name": name, "active": self.active})

        self.save_canvas.itemconfig(self._save_text, text="\u2713  Salvo com sucesso!")
        self.save_canvas.itemconfig(self._save_bg, fill=GREEN_DARK)
        self.save_canvas.unbind("<Button-1>")
        self.save_canvas.unbind("<Enter>")
        self.save_canvas.unbind("<Leave>")
        self.root.after(1500, self.root.destroy)

    # ── Status ────────────────────────────────────────────────────────
    def _build_status(self, parent):
        self.status_label = tk.Label(parent, text="", font=(FONT_FAMILY, 10),
                                      bg=BG_PRIMARY, fg=GREEN_PRIMARY, pady=4)
        self.status_label.pack(fill="x", pady=(8, 0))

    def _show_status(self, message, error=False):
        self.status_label.configure(
            text=message,
            fg=ERROR_FG if error else GREEN_PRIMARY,
            bg=ERROR_BG if error else BG_PRIMARY)
        self.root.after(2500, lambda: self.status_label.configure(text="", bg=BG_PRIMARY))

    # ── Footer ────────────────────────────────────────────────────────
    def _build_footer(self):
        tk.Label(self.root, text="v4.0 \u00B7 WhatsApp Desktop",
                 font=(FONT_FAMILY, 8), fg=TEXT_MUTED,
                 bg=BG_PRIMARY).pack(pady=(0, 10))

    # ── Run ───────────────────────────────────────────────────────────
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    import ctypes.wintypes  # noqa: F811
    app = SettingsWindow()
    app.run()
