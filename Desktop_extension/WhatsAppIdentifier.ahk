/**
 * WhatsApp Identificador - Desktop (AutoHotkey v2) v4.0
 *
 * Mesma função da extensão Chrome, mas para o WhatsApp Desktop.
 * Intercepta Enter e adiciona *Nome:* antes de cada mensagem.
 *
 * Requer: AutoHotkey v2.0+ (https://www.autohotkey.com/)
 *         Python 3 (para a GUI de configuração)
 */

#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent

; ─── Configuração ───────────────────────────────────────────────────
global CFG_FILE  := A_ScriptDir "\config.ini"
global g_name    := IniRead(CFG_FILE, "Settings", "Name",   "")
global g_active  := IniRead(CFG_FILE, "Settings", "Active", "0") = "1"
global g_busy    := false
global g_pyPID   := 0

; ─── Tray ────────────────────────────────────────────────────────────
A_TrayMenu.Delete()
A_TrayMenu.Add("Configurar...",    ShowConfig)
A_TrayMenu.Add("Ativar/Desativar", ToggleActive)
A_TrayMenu.Add()
A_TrayMenu.Add("Sair", (*) => ExitApp())
A_TrayMenu.Default := "Configurar..."
UpdateTray()

; ─── Hotkeys ─────────────────────────────────────────────────────────
#HotIf WinActive("ahk_exe WhatsApp.Root.exe") && !IsConfigVisible()
+Enter::      Send "+{Enter}"
+NumpadEnter::Send "+{Enter}"
Enter::       OnEnter()
NumpadEnter:: OnEnter()
#HotIf

IsConfigVisible() {
    global g_pyPID
    return g_pyPID && ProcessExist(g_pyPID)
}

; ─── Lógica principal ────────────────────────────────────────────────
OnEnter() {
    global g_active, g_name, g_busy

    if (!g_active || g_name = "" || g_busy) {
        Send "{Enter}"
        return
    }

    g_busy := true
    prefix := "*" g_name ":* "

    savedClip := ClipboardAll()
    A_Clipboard := ""

    Send "^a"
    Sleep 15
    Send "^c"

    if !ClipWait(0.5) {
        A_Clipboard := savedClip
        g_busy := false
        Send "{Enter}"
        return
    }

    currentText := Trim(A_Clipboard)

    if (currentText = "") {
        A_Clipboard := savedClip
        g_busy := false
        Send "{Enter}"
        return
    }

    if (SubStr(currentText, 1, StrLen(prefix)) = prefix) {
        A_Clipboard := savedClip
        g_busy := false
        Send "{Enter}"
        return
    }

    newText := prefix "`n" currentText
    A_Clipboard := newText

    if !ClipWait(0.3) {
        A_Clipboard := savedClip
        g_busy := false
        Send "{Enter}"
        return
    }

    Send "^a"
    Sleep 15
    Send "{Delete}"
    Sleep 30
    Send "^v"
    Sleep 60

    A_Clipboard := ""
    Send "^a"
    Sleep 15
    Send "^c"

    if ClipWait(0.3) {
        pastedText := Trim(A_Clipboard)
        if (SubStr(pastedText, 1, StrLen(prefix)) = prefix) {
            A_Clipboard := savedClip
            Send "{Enter}"
            Sleep 30
            SetTimer(() => (g_busy := false), -300)
            return
        }
    }

    A_Clipboard := currentText
    ClipWait(0.3)
    Send "^a"
    Sleep 15
    Send "{Delete}"
    Sleep 30
    Send "^v"
    Sleep 60

    A_Clipboard := savedClip
    g_busy := false
    MsgBox("Não foi possível inserir o prefixo. Tente novamente.", "WhatsApp Identificador", 48)
}

; ─── GUI de Configuração (Python) ──────────────────────────────────
ShowConfig(*) {
    global g_pyPID

    if (g_pyPID && ProcessExist(g_pyPID))
        return

    pyScript := A_ScriptDir "\settings_gui.py"

    try {
        Run("pythonw " '"' pyScript '"', A_ScriptDir, , &g_pyPID)
    } catch {
        try {
            Run("python " '"' pyScript '"', A_ScriptDir, "Hide", &g_pyPID)
        } catch {
            MsgBox("Python não encontrado.`n`nInstale Python 3 em python.org e reinicie o programa.", "WhatsApp Identificador", 48)
            return
        }
    }

    SetTimer(CheckPyExit, 500)
}

CheckPyExit() {
    global g_pyPID, g_name, g_active, CFG_FILE

    if ProcessExist(g_pyPID)
        return

    SetTimer(CheckPyExit, 0)
    g_pyPID := 0

    g_name   := IniRead(CFG_FILE, "Settings", "Name",   "")
    g_active := IniRead(CFG_FILE, "Settings", "Active", "0") = "1"

    UpdateTray()
}

; ─── Toggle via tray ─────────────────────────────────────────────────
ToggleActive(*) {
    global g_active, CFG_FILE
    g_active := !g_active
    IniWrite(g_active ? "1" : "0", CFG_FILE, "Settings", "Active")
    UpdateTray()
    ToolTip("WhatsApp Identificador: " (g_active ? "✓ Ativado" : "✗ Desativado"))
    SetTimer(() => ToolTip(), -2000)
}

; ─── Atualiza ícone e tooltip da tray ────────────────────────────────
UpdateTray() {
    global g_active, g_name
    status   := g_active ? "Ativo" : "Inativo"
    nameInfo := g_name != "" ? " | " g_name : " | (sem nome)"
    A_IconTip := "WhatsApp Identificador — " status nameInfo
    try TraySetIcon("shell32.dll", g_active ? 296 : 131)
}
