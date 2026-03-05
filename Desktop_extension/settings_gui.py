"""
WhatsApp Identifier — Settings GUI (Python tkinter)
Janela de configuração para o WhatsApp Identifier Desktop.
Lê e escreve config.ini, compartilhado com o script AHK.
"""

import tkinter as tk
import tkinter.colorchooser as cc
import configparser
import ctypes
import os
import sys

# ── DPI awareness (Windows 10+) ──────────────────────────────────────
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# ── Constantes ────────────────────────────────────────────────────────
WIDTH = 370
HEIGHT = 740

BG_DARK       = "#0B141A"
BG_CARD       = "#1B2831"
BORDER_COLOR  = "#233340"
TEXT_PRIMARY   = "#E9EDEF"
TEXT_SECONDARY = "#8696A0"
TEXT_MUTED     = "#4A5E6A"
GREEN_PRIMARY  = "#00A884"
GREEN_DARK     = "#00856B"
GREEN_BUBBLE   = "#005C4B"
GREEN_HEADER_2 = "#008F6F"
ERROR_BG       = "#3A1A1A"
ERROR_FG       = "#FF6B6B"
SUCCESS_BG     = "#075E54"
SLIDER_TROUGH  = "#233340"

CARD_RADIUS    = 12
BUTTON_RADIUS  = 10

FONT_FAMILY = "Segoe UI"
MAX_NAME_LEN = 30

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "config.ini")

COLOR_PRESETS = [
    ("#1A1A2E", "Azul escuro"),
    ("#0B141A", "WhatsApp"),
    ("#1A0B0B", "Vermelho"),
    ("#0D0D0D", "Preto"),
]


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
    debug_port = int(config.get("Privacy", "DebugPort", fallback="9251"))

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
    config["Privacy"] = {
        "PrivacyEnabled": "1" if cfg["priv_enabled"] else "0",
        "BlurIntensity": str(cfg["blur_intensity"]),
        "OverlayOpacity": str(cfg["overlay_opacity"]),
        "OverlayColor": cfg["overlay_color"].lstrip("#"),
        "HideOnHover": "1" if cfg["hide_on_hover"] else "0",
        "HideOnFocus": "1" if cfg["hide_on_focus"] else "0",
        "IdleBlurEnabled": "1" if cfg["idle_enabled"] else "0",
        "IdleBlurSeconds": str(cfg["idle_seconds"]),
        "DebugPort": str(cfg["debug_port"]),
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


def create_rounded_card(parent, width, height, radius=CARD_RADIUS, bg=BG_CARD, border_color=BORDER_COLOR):
    canvas = tk.Canvas(parent, width=width, height=height,
                       bg=BG_DARK, highlightthickness=0, bd=0)
    rounded_rect(canvas, 0, 0, width, height, radius, fill=border_color, outline="")
    rounded_rect(canvas, 1, 1, width - 1, height - 1, radius - 1, fill=bg, outline="")
    return canvas


# ══════════════════════════════════════════════════════════════════════
class SettingsWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WA Identifier")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG_DARK)
        self.root.resizable(False, False)

        # State
        cfg = read_config()
        self.name = cfg["name"]
        self.active = cfg["active"]
        self._priv_enabled = tk.BooleanVar(value=cfg["priv_enabled"])
        self._blur_intensity = tk.IntVar(value=cfg["blur_intensity"])
        self._overlay_opacity = tk.IntVar(value=cfg["overlay_opacity"])
        self._overlay_color = tk.StringVar(value=cfg["overlay_color"])
        self._hide_on_hover = tk.BooleanVar(value=cfg["hide_on_hover"])
        self._hide_on_focus = tk.BooleanVar(value=cfg["hide_on_focus"])
        self._idle_enabled = tk.BooleanVar(value=cfg["idle_enabled"])
        self._idle_seconds = tk.IntVar(value=cfg["idle_seconds"])
        self._debug_port = tk.IntVar(value=cfg["debug_port"])

        self._drag_x = 0
        self._drag_y = 0

        # Position
        self._position_window()

        # Build UI
        self._build_header()
        self._build_scrollable_content()
        self._build_footer()

        # Bordas arredondadas
        self.root.after(10, self._apply_rounded_window)
        self.root.after(100, lambda: (self.root.focus_force(), self.name_entry.focus_set()))

    # ── Bordas arredondadas da janela ─────────────────────────────────
    def _apply_rounded_window(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, WIDTH + 1, HEIGHT + 1, 18, 18)
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
        header = tk.Canvas(self.root, width=WIDTH, height=80, highlightthickness=0, bg=BG_DARK)
        header.pack(fill="x")

        r = 14
        pts = [0 + r, 0, WIDTH - r, 0, WIDTH, 0, WIDTH, 0 + r,
               WIDTH, 80, WIDTH, 80, 0, 80, 0, 80, 0, 0 + r, 0, 0]
        header.create_polygon(pts, smooth=True, fill=GREEN_PRIMARY, outline="")
        header.create_rectangle(WIDTH // 2, 0, WIDTH, 80, fill=GREEN_HEADER_2,
                                outline="", stipple="gray25")

        header.create_oval(WIDTH - 40, -25, WIDTH + 30, 55, fill="#FFFFFF",
                           outline="", stipple="gray12")
        header.create_oval(WIDTH - 70, 35, WIDTH - 5, 105, fill="#FFFFFF",
                           outline="", stipple="gray12")

        header.create_oval(21, 19, 61, 59, fill="#009970", outline="")
        header.create_oval(20, 18, 60, 58, fill="#33C49A", outline="")
        header.create_text(40, 38, text="\u260E", font=(FONT_FAMILY, 15), fill="white")

        header.create_text(74, 30, text="WA Identifier", anchor="w",
                           font=(FONT_FAMILY, 14, "bold"), fill="white")
        header.create_text(74, 52, text="Identifique suas mensagens", anchor="w",
                           font=(FONT_FAMILY, 9), fill="#C8F5E8")

        close_bg = rounded_rect(header, WIDTH - 42, 24, WIDTH - 14, 52, 8,
                                fill="#33997F", outline="")
        close_text = header.create_text(WIDTH - 28, 38, text="\u2715",
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

    def _start_drag(self, event):
        if event.x > WIDTH - 45:
            return
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        if event.x > WIDTH - 45:
            return
        x = self.root.winfo_x() + event.x - self._drag_x
        y = self.root.winfo_y() + event.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # ── Scrollable Content ───────────────────────────────────────────
    def _build_scrollable_content(self):
        container = tk.Frame(self.root, bg=BG_DARK)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg=BG_DARK, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        content = tk.Frame(canvas, bg=BG_DARK)
        content_window = canvas.create_window((0, 0), window=content, anchor="nw",
                                               width=WIDTH - 14)

        def on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        content.bind("<Configure>", on_configure)

        # Mouse wheel scroll
        def on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        self._scroll_canvas = canvas

        # Build all sections inside content
        inner = tk.Frame(content, bg=BG_DARK)
        inner.pack(fill="both", expand=True, padx=16, pady=(16, 12))

        self._build_name_field(inner)
        self._build_toggle(inner)
        self._build_preview(inner)
        self._build_privacy_section(inner)
        self._build_save_button(inner)
        self._build_status(inner)

    # ── Campo de nome ─────────────────────────────────────────────────
    def _build_name_field(self, parent):
        card_w = WIDTH - 46

        lbl_frame = tk.Frame(parent, bg=BG_DARK)
        lbl_frame.pack(fill="x", pady=(0, 7))
        tk.Label(lbl_frame, text="\u2022  NOME IDENTIFICADOR",
                 font=(FONT_FAMILY, 8, "bold"), fg=TEXT_SECONDARY,
                 bg=BG_DARK).pack(side="left")

        card_canvas = create_rounded_card(parent, card_w, 48, radius=CARD_RADIUS)
        card_canvas.pack(fill="x", pady=(0, 12))

        self.name_entry = tk.Entry(card_canvas, font=(FONT_FAMILY, 13),
                                    bg=BG_CARD, fg=TEXT_PRIMARY,
                                    insertbackground=GREEN_PRIMARY,
                                    relief="flat", bd=0)
        card_canvas.create_window(14, 24, window=self.name_entry,
                                   anchor="w", width=card_w - 80)
        self.name_entry.insert(0, self.name)

        self.char_label = tk.Label(card_canvas, text=f"{len(self.name)}/{MAX_NAME_LEN}",
                                    font=(FONT_FAMILY, 8), fg=TEXT_MUTED, bg=BG_CARD)
        card_canvas.create_window(card_w - 14, 24, window=self.char_label, anchor="e")

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
            fg="#F0AD4E" if length > 24 else TEXT_MUTED)
        self._update_preview()

    # ── Toggle ────────────────────────────────────────────────────────
    def _build_toggle(self, parent):
        card_w = WIDTH - 46
        card_h = 56

        card_canvas = create_rounded_card(parent, card_w, card_h, radius=CARD_RADIUS)
        card_canvas.pack(fill="x", pady=(0, 12))

        left = tk.Frame(card_canvas, bg=BG_CARD)
        card_canvas.create_window(16, card_h // 2, window=left, anchor="w")

        tk.Label(left, text="Identificador", font=(FONT_FAMILY, 13),
                 fg=TEXT_PRIMARY, bg=BG_CARD).pack(anchor="w")
        self.toggle_subtitle = tk.Label(
            left, text="Ativo" if self.active else "Inativo",
            font=(FONT_FAMILY, 9),
            fg=GREEN_PRIMARY if self.active else TEXT_SECONDARY,
            bg=BG_CARD)
        self.toggle_subtitle.pack(anchor="w")

        self.toggle_canvas = tk.Canvas(card_canvas, width=46, height=26,
                                        bg=BG_CARD, highlightthickness=0,
                                        cursor="hand2")
        card_canvas.create_window(card_w - 20, card_h // 2,
                                   window=self.toggle_canvas, anchor="e")
        self.toggle_canvas.bind("<Button-1>", self._toggle_active)
        self._draw_toggle()

    def _draw_toggle(self):
        c = self.toggle_canvas
        c.delete("all")
        bg = GREEN_PRIMARY if self.active else "#3B4A54"
        knob_cx = 33 if self.active else 13
        c.create_oval(0, 0, 26, 26, fill=bg, outline="")
        c.create_oval(20, 0, 46, 26, fill=bg, outline="")
        c.create_rectangle(13, 0, 33, 26, fill=bg, outline="")
        c.create_oval(knob_cx - 10, 3, knob_cx + 10, 23, fill="#E9EDEF", outline="")

    def _toggle_active(self, event=None):
        self.active = not self.active
        self._draw_toggle()
        self.toggle_subtitle.configure(
            text="Ativo" if self.active else "Inativo",
            fg=GREEN_PRIMARY if self.active else TEXT_SECONDARY)
        self._update_preview()

    # ── Preview ───────────────────────────────────────────────────────
    def _build_preview(self, parent):
        card_w = WIDTH - 46
        card_h = 100

        card_canvas = create_rounded_card(parent, card_w, card_h, radius=CARD_RADIUS)
        card_canvas.pack(fill="x", pady=(0, 14))

        card_canvas.create_text(14, 16, text="\u2022  PREVIEW DA MENSAGEM", anchor="w",
                                font=(FONT_FAMILY, 8, "bold"), fill=TEXT_SECONDARY)
        card_canvas.create_line(10, 30, card_w - 10, 30, fill=BORDER_COLOR)

        self.preview_canvas = tk.Canvas(card_canvas, width=card_w - 8, height=62,
                                         bg=BG_DARK, highlightthickness=0)
        card_canvas.create_window(card_w // 2, 65, window=self.preview_canvas, anchor="center")
        self._update_preview()

    def _update_preview(self):
        c = self.preview_canvas
        c.delete("all")
        cw = int(c.cget("width"))
        name = self.name_entry.get().strip() or "Nome"

        if self.active:
            bx1, by1, bx2, by2 = cw - 210, 6, cw - 8, 60
            rounded_rect(c, bx1, by1, bx2, by2, 8, fill=GREEN_BUBBLE)
            c.create_polygon(bx2, by1, bx2 + 7, by1, bx2, by1 + 9,
                             fill=GREEN_BUBBLE, outline="")
            c.create_text(bx1 + 10, by1 + 14, text=f"{name}:", anchor="w",
                          font=(FONT_FAMILY, 10, "bold"), fill=TEXT_PRIMARY)
            c.create_text(bx1 + 10, by1 + 34, text="Sua mensagem aqui...", anchor="w",
                          font=(FONT_FAMILY, 10), fill=TEXT_PRIMARY)
            c.create_text(bx2 - 6, by2 - 8, text="agora \u2713\u2713", anchor="e",
                          font=(FONT_FAMILY, 7), fill=TEXT_MUTED)
        else:
            bx1, by1, bx2, by2 = cw - 190, 6, cw - 8, 60
            rounded_rect(c, bx1, by1, bx2, by2, 8, fill="#1A2E28")
            c.create_text(bx1 + 10, (by1 + by2) // 2, text="Sua mensagem aqui...",
                          anchor="w", font=(FONT_FAMILY, 10), fill=TEXT_MUTED)

    # ══════════════════════════════════════════════════════════════════
    # ── SEÇÃO DE PRIVACIDADE ──────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════

    def _build_privacy_section(self, parent):
        card_w = WIDTH - 46

        # Section label
        lbl = tk.Frame(parent, bg=BG_DARK)
        lbl.pack(fill="x", pady=(0, 7))
        tk.Label(lbl, text="\u2022  PRIVACIDADE (CSS Blur)",
                 font=(FONT_FAMILY, 8, "bold"), fg=TEXT_SECONDARY,
                 bg=BG_DARK).pack(side="left")

        # Master toggle
        self._build_toggle_row(parent, card_w,
            label="Modo Privacidade", var=self._priv_enabled,
            sub_on="Blur ativo nas mensagens",
            sub_off="Sem blur de privacidade")

        # Hide on hover
        self._build_toggle_row(parent, card_w,
            label="Revelar ao hover", var=self._hide_on_hover,
            sub_on="Blur some ao passar o mouse",
            sub_off="Hover n\u00e3o remove o blur")

        # Hide on focus
        self._build_toggle_row(parent, card_w,
            label="Revelar ao focar", var=self._hide_on_focus,
            sub_on="Blur some ao clicar no WA",
            sub_off="Foco n\u00e3o remove o blur")

        # Idle blur
        self._build_toggle_row(parent, card_w,
            label="Blur por inatividade", var=self._idle_enabled,
            sub_on="Blur ap\u00f3s X seg sem mover mouse",
            sub_off="Sem blur autom\u00e1tico por tempo",
            on_toggle=self._on_idle_toggle)

        # Idle seconds slider
        self._idle_slider_frame = tk.Frame(parent, bg=BG_DARK)
        if self._idle_enabled.get():
            self._idle_slider_frame.pack(fill="x", pady=(0, 6))
        self._build_slider(self._idle_slider_frame, card_w,
            label="Tempo de inatividade", var=self._idle_seconds,
            from_=5, to=120, suffix="s", label_var_name="_idle_val_label")

        # Blur intensity slider
        self._blur_frame = tk.Frame(parent, bg=BG_DARK)
        self._blur_frame.pack(fill="x", pady=(0, 6))
        self._build_slider(self._blur_frame, card_w,
            label="Intensidade do blur", var=self._blur_intensity,
            from_=2, to=20, suffix="px", label_var_name="_blur_val_label")

        # CDP port detection button
        cdp_card_h = 52
        cdp_card = create_rounded_card(parent, card_w, cdp_card_h, radius=CARD_RADIUS)
        cdp_card.pack(fill="x", pady=(0, 6))

        cdp_left = tk.Frame(cdp_card, bg=BG_CARD)
        cdp_card.create_window(16, cdp_card_h // 2, window=cdp_left, anchor="w")
        tk.Label(cdp_left, text="Porta CDP", font=(FONT_FAMILY, 11),
                 fg=TEXT_PRIMARY, bg=BG_CARD).pack(anchor="w")
        self._cdp_status = tk.Label(cdp_left, text=f"Porta: {self._debug_port.get()}",
                                     font=(FONT_FAMILY, 8), fg=TEXT_SECONDARY, bg=BG_CARD)
        self._cdp_status.pack(anchor="w")

        detect_btn = tk.Canvas(cdp_card, width=80, height=28,
                               bg=BG_CARD, highlightthickness=0, cursor="hand2")
        cdp_card.create_window(card_w - 20, cdp_card_h // 2, window=detect_btn, anchor="e")
        detect_btn.create_rectangle(0, 0, 80, 28, fill=GREEN_PRIMARY, outline="")
        detect_btn.create_text(40, 14, text="Detectar", fill="white",
                               font=(FONT_FAMILY, 9, "bold"))
        detect_btn.bind("<Button-1>", lambda e: self._detect_cdp_port())

    def _build_toggle_row(self, parent, card_w, label, var, sub_on, sub_off,
                           on_toggle=None):
        card_h = 52
        card_canvas = create_rounded_card(parent, card_w, card_h, radius=CARD_RADIUS)
        card_canvas.pack(fill="x", pady=(0, 6))

        left = tk.Frame(card_canvas, bg=BG_CARD)
        card_canvas.create_window(16, card_h // 2, window=left, anchor="w")

        tk.Label(left, text=label, font=(FONT_FAMILY, 11),
                 fg=TEXT_PRIMARY, bg=BG_CARD).pack(anchor="w")
        sub = tk.Label(left, text=sub_on if var.get() else sub_off,
                       font=(FONT_FAMILY, 8),
                       fg=GREEN_PRIMARY if var.get() else TEXT_SECONDARY,
                       bg=BG_CARD)
        sub.pack(anchor="w")

        toggle_c = tk.Canvas(card_canvas, width=46, height=26,
                              bg=BG_CARD, highlightthickness=0, cursor="hand2")
        card_canvas.create_window(card_w - 20, card_h // 2,
                                   window=toggle_c, anchor="e")

        def draw():
            toggle_c.delete("all")
            on = var.get()
            bg_col = GREEN_PRIMARY if on else "#3B4A54"
            cx = 33 if on else 13
            toggle_c.create_oval(0, 0, 26, 26, fill=bg_col, outline="")
            toggle_c.create_oval(20, 0, 46, 26, fill=bg_col, outline="")
            toggle_c.create_rectangle(13, 0, 33, 26, fill=bg_col, outline="")
            toggle_c.create_oval(cx - 10, 3, cx + 10, 23, fill="#E9EDEF", outline="")
            sub.configure(
                text=sub_on if on else sub_off,
                fg=GREEN_PRIMARY if on else TEXT_SECONDARY)

        def click(e=None):
            var.set(not var.get())
            draw()
            if on_toggle:
                on_toggle()

        toggle_c.bind("<Button-1>", click)
        draw()

    def _on_idle_toggle(self):
        if self._idle_enabled.get():
            self._idle_slider_frame.pack(fill="x", pady=(0, 6),
                                          before=self._opacity_frame)
        else:
            self._idle_slider_frame.pack_forget()

    def _build_slider(self, parent, card_w, label, var, from_, to, suffix,
                       label_var_name):
        card_canvas = create_rounded_card(parent, card_w, 60, radius=CARD_RADIUS)
        card_canvas.pack(fill="x")

        card_canvas.create_text(16, 16, text=label, anchor="w",
                                font=(FONT_FAMILY, 10), fill=TEXT_PRIMARY)

        val_label = tk.Label(card_canvas, text=f"{var.get()}{suffix}",
                              font=(FONT_FAMILY, 9), fg=GREEN_PRIMARY, bg=BG_CARD)
        card_canvas.create_window(card_w - 16, 16, window=val_label, anchor="e")
        setattr(self, label_var_name, val_label)

        slider = tk.Scale(card_canvas, from_=from_, to=to, orient="horizontal",
                           variable=var, length=card_w - 32,
                           bg=BG_CARD, fg=TEXT_PRIMARY, troughcolor=SLIDER_TROUGH,
                           highlightthickness=0, bd=0, showvalue=False,
                           activebackground=GREEN_PRIMARY,
                           command=lambda v, lbl=val_label, s=suffix:
                               lbl.configure(text=f"{int(float(v))}{s}"))
        card_canvas.create_window(card_w // 2, 42, window=slider, anchor="center")

    def _build_color_picker(self, parent, card_w):
        card_h = 56
        card_canvas = create_rounded_card(parent, card_w, card_h, radius=CARD_RADIUS)
        card_canvas.pack(fill="x", pady=(0, 12))

        card_canvas.create_text(16, 14, text="Cor do overlay", anchor="w",
                                font=(FONT_FAMILY, 10), fill=TEXT_PRIMARY)

        self._swatch_items = []
        x_offset = 16
        for color, tip in COLOR_PRESETS:
            swatch = tk.Canvas(card_canvas, width=24, height=24,
                                bg=BG_CARD, highlightthickness=0, cursor="hand2")
            outline = GREEN_PRIMARY if self._overlay_color.get() == color else BORDER_COLOR
            oval_id = swatch.create_oval(2, 2, 22, 22, fill=color,
                                          outline=outline, width=2)
            card_canvas.create_window(x_offset + 12, 38, window=swatch)
            self._swatch_items.append((swatch, oval_id, color))

            swatch.bind("<Button-1>",
                         lambda e, c=color: self._select_color(c))
            x_offset += 32

        # Custom color button
        custom_btn = tk.Label(card_canvas, text="+ Cor",
                               font=(FONT_FAMILY, 8), fg=TEXT_SECONDARY,
                               bg=BG_CARD, cursor="hand2")
        card_canvas.create_window(x_offset + 20, 38, window=custom_btn)
        custom_btn.bind("<Button-1>", self._open_color_dialog)

    def _select_color(self, color):
        self._overlay_color.set(color)
        for swatch, oval_id, c in self._swatch_items:
            outline = GREEN_PRIMARY if c == color else BORDER_COLOR
            swatch.itemconfig(oval_id, outline=outline)

    def _open_color_dialog(self, event=None):
        result = cc.askcolor(color=self._overlay_color.get(),
                              title="Escolher cor do overlay")
        if result and result[1]:
            self._overlay_color.set(result[1])
            for swatch, oval_id, c in self._swatch_items:
                swatch.itemconfig(oval_id, outline=BORDER_COLOR)

    # ── Detectar porta CDP ─────────────────────────────────────────────
    def _detect_cdp_port(self):
        from cdp_utils import find_whatsapp_port
        self._cdp_status.configure(text="Procurando...", fg="#FFCC00")
        self.root.update()
        found_port, _ = find_whatsapp_port(self._debug_port.get())
        if found_port:
            self._debug_port.set(found_port)
            self._cdp_status.configure(text=f"WhatsApp na porta {found_port}!", fg=GREEN_PRIMARY)
            # Tell daemon to reconnect (it will find WhatsApp and auto-inject)
            cmd_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blur_cmd.txt")
            try:
                with open(cmd_file, "w") as f:
                    f.write("reconnect")
            except Exception:
                pass
        else:
            self._cdp_status.configure(text="WhatsApp CDP nao encontrado", fg=ERROR_FG)

    # ── Botão Salvar ──────────────────────────────────────────────────
    def _build_save_button(self, parent):
        card_w = WIDTH - 46
        btn_h = 44

        self.save_canvas = tk.Canvas(parent, width=card_w, height=btn_h,
                                      bg=BG_DARK, highlightthickness=0, cursor="hand2")
        self.save_canvas.pack(fill="x")

        self._save_bg = rounded_rect(self.save_canvas, 0, 0, card_w, btn_h,
                                      BUTTON_RADIUS, fill=GREEN_PRIMARY, outline="")
        self._save_text = self.save_canvas.create_text(
            card_w // 2, btn_h // 2,
            text="\U0001F4BE  Salvar configura\u00E7\u00E3o",
            font=(FONT_FAMILY, 12, "bold"), fill="white")

        self.save_canvas.bind("<Button-1>", lambda e: self._save())
        self.save_canvas.bind("<Enter>", lambda e: self.save_canvas.itemconfig(
            self._save_bg, fill=GREEN_DARK))
        self.save_canvas.bind("<Leave>", lambda e: self.save_canvas.itemconfig(
            self._save_bg, fill=GREEN_PRIMARY))

    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            self._show_status("Digite um nome!", error=True)
            self.name_entry.focus_set()
            return

        write_config({
            "name": name,
            "active": self.active,
            "priv_enabled": self._priv_enabled.get(),
            "blur_intensity": self._blur_intensity.get(),
            "overlay_opacity": self._overlay_opacity.get(),
            "overlay_color": self._overlay_color.get(),
            "hide_on_hover": self._hide_on_hover.get(),
            "hide_on_focus": self._hide_on_focus.get(),
            "idle_enabled": self._idle_enabled.get(),
            "idle_seconds": self._idle_seconds.get(),
            "debug_port": self._debug_port.get(),
        })

        self.save_canvas.itemconfig(self._save_text, text="\u2713  Salvo com sucesso!")
        self.save_canvas.itemconfig(self._save_bg, fill=SUCCESS_BG)
        self.save_canvas.unbind("<Button-1>")
        self.save_canvas.unbind("<Enter>")
        self.save_canvas.unbind("<Leave>")
        self.root.after(1500, self.root.destroy)

    # ── Status ────────────────────────────────────────────────────────
    def _build_status(self, parent):
        self.status_label = tk.Label(parent, text="", font=(FONT_FAMILY, 10),
                                      bg=BG_DARK, fg=GREEN_PRIMARY, pady=4)
        self.status_label.pack(fill="x", pady=(8, 0))

    def _show_status(self, message, error=False):
        self.status_label.configure(
            text=message,
            fg=ERROR_FG if error else GREEN_PRIMARY,
            bg=ERROR_BG if error else BG_DARK)
        self.root.after(2500, lambda: self.status_label.configure(text="", bg=BG_DARK))

    # ── Footer ────────────────────────────────────────────────────────
    def _build_footer(self):
        tk.Label(self.root, text="v3.5.1 \u00B7 WhatsApp Desktop",
                 font=(FONT_FAMILY, 8), fg=BORDER_COLOR,
                 bg=BG_DARK).pack(pady=(0, 10))

    # ── Run ───────────────────────────────────────────────────────────
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    import ctypes.wintypes  # noqa: F811
    app = SettingsWindow()
    app.run()
