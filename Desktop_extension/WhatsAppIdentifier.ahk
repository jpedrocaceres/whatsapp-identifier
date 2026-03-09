;@Ahk2Exe-SetProductVersion 3.6.0
;@Ahk2Exe-SetFileVersion 3.6.0
;@Ahk2Exe-SetProductName WhatsApp Identifier
;@Ahk2Exe-SetDescription WhatsApp Identifier - Desktop

/**
 * WhatsApp Identifier - Desktop (AutoHotkey v2)
 *
 * Mesma função da extensão Chrome, mas para o WhatsApp Desktop.
 * Intercepta Enter e adiciona *Nome:* antes de cada mensagem.
 * Inclui Privacy Overlay: cobre a janela quando perde o foco.
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

; ─── Privacy Blur globals ─────────────────────────────────────────────
global g_privEnabled    := false
global g_blurIntensity  := 8
global g_hideOnHover    := true
global g_hideOnFocus    := true
global g_idleEnabled    := false
global g_idleSeconds    := 30
global g_blurActive     := false
global g_lastMouseMove  := A_TickCount
global g_debugPort      := 9351
global g_cdpWsUrl       := ""
global g_overlayOpacity := 200
global g_overlayColor   := "1A1A2E"
global g_daemonPID      := 0

CoordMode("Mouse", "Screen")
ReadPrivacyConfig()
LaunchWhatsAppWithCDP()
StartDaemon()

OnExit(OnAppExit)

; ─── Tray ────────────────────────────────────────────────────────────
A_TrayMenu.Delete()
A_TrayMenu.Add("Configurar...",      ShowConfig)
A_TrayMenu.Add("Ativar/Desativar",   ToggleActive)
A_TrayMenu.Add("Privacidade On/Off", TogglePrivacy)
A_TrayMenu.Add()
A_TrayMenu.Add("Sair", (*) => ExitApp())
A_TrayMenu.Default := "Configurar..."
UpdateTray()

; ─── Privacy Timer ──────────────────────────────────────────────────
SetTimer(PrivacyTimerProc, 250)

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
    MsgBox("Não foi possível inserir o prefixo. Tente novamente.", "WhatsApp Identifier", 48)
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
            MsgBox("Python não encontrado.`n`nInstale Python 3 em python.org e reinicie o programa.", "WhatsApp Identifier", 48)
            return
        }
    }

    SetTimer(CheckPyExit, 500)
}

CheckPyExit() {
    global g_pyPID, g_name, g_active, CFG_FILE
    global g_blurActive, g_blurIntensity, g_debugPort

    if ProcessExist(g_pyPID)
        return

    SetTimer(CheckPyExit, 0)
    g_pyPID := 0

    g_name   := IniRead(CFG_FILE, "Settings", "Name",   "")
    g_active := IniRead(CFG_FILE, "Settings", "Active", "0") = "1"

    ; Recarrega config de privacidade; se port ou blur mudou, reiniciar daemon
    oldIntensity := g_blurIntensity
    oldPort := g_debugPort
    ReadPrivacyConfig()

    if (oldPort != g_debugPort) {
        ; Port changed — restart daemon with new port
        StopDaemon()
        StartDaemon()
        g_blurActive := false
        InjectBlur()
    } else if (g_blurActive && oldIntensity != g_blurIntensity) {
        g_blurActive := false  ; Forçar re-injeção com nova intensidade
        InjectBlur()
    }

    UpdateTray()
}

; ─── Toggle via tray ─────────────────────────────────────────────────
ToggleActive(*) {
    global g_active, CFG_FILE
    g_active := !g_active
    IniWrite(g_active ? "1" : "0", CFG_FILE, "Settings", "Active")
    UpdateTray()
    ToolTip("WhatsApp Identifier: " (g_active ? "✓ Ativado" : "✗ Desativado"))
    SetTimer(() => ToolTip(), -2000)
}

TogglePrivacy(*) {
    global g_privEnabled, CFG_FILE
    g_privEnabled := !g_privEnabled
    IniWrite(g_privEnabled ? "1" : "0", CFG_FILE, "Privacy", "PrivacyEnabled")
    if (!g_privEnabled)
        RemoveBlur()
    ToolTip("Privacidade: " (g_privEnabled ? "✓ Ativa" : "✗ Inativa"))
    SetTimer(() => ToolTip(), -2000)
}

; ─── Atualiza ícone e tooltip da tray ────────────────────────────────
UpdateTray() {
    global g_active, g_name
    status   := g_active ? "Ativo" : "Inativo"
    nameInfo := g_name != "" ? " | " g_name : " | (sem nome)"
    A_IconTip := "WhatsApp Identifier — " status nameInfo
    try TraySetIcon("shell32.dll", g_active ? 296 : 131)
}

; ═══════════════════════════════════════════════════════════════════════
; ─── PRIVACY BLUR (CSS Injection via CDP) ────────────────────────────
; ═══════════════════════════════════════════════════════════════════════

ReadPrivacyConfig() {
    global CFG_FILE, g_privEnabled, g_blurIntensity, g_overlayOpacity, g_overlayColor
    global g_hideOnHover, g_hideOnFocus, g_idleEnabled, g_idleSeconds, g_debugPort

    g_privEnabled    := IniRead(CFG_FILE, "Privacy", "PrivacyEnabled",  "0") = "1"
    g_blurIntensity  := Integer(IniRead(CFG_FILE, "Privacy", "BlurIntensity", "8"))
    g_overlayOpacity := Integer(IniRead(CFG_FILE, "Privacy", "OverlayOpacity", "200"))
    g_overlayColor   := IniRead(CFG_FILE, "Privacy", "OverlayColor",   "1A1A2E")
    g_hideOnHover    := IniRead(CFG_FILE, "Privacy", "HideOnHover",    "1") = "1"
    g_hideOnFocus    := IniRead(CFG_FILE, "Privacy", "HideOnFocus",    "1") = "1"
    g_idleEnabled    := IniRead(CFG_FILE, "Privacy", "IdleBlurEnabled", "0") = "1"
    g_idleSeconds    := Integer(IniRead(CFG_FILE, "Privacy", "IdleBlurSeconds", "30"))
    g_debugPort      := Integer(IniRead(CFG_FILE, "Privacy", "DebugPort", "9351"))
}

; ─── Launch WhatsApp if not running ────────────────────────────────
LaunchWhatsAppWithCDP() {
    global g_debugPort, g_privEnabled

    envVal := "--remote-debugging-port=" g_debugPort

    if (g_privEnabled) {
        ; Set env var for this process (affects child processes)
        EnvSet("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", envVal)

        ; Also persist in user registry so it works on autostart
        try RunWait('reg add "HKCU\Environment" /v WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS /t REG_SZ /d "' envVal '" /f',, "Hide")
    }

    wasRunning := WinExist("ahk_exe WhatsApp.Root.exe")

    if (wasRunning && g_privEnabled) {
        ; WhatsApp is running — check if CDP is active on our port
        cdpOk := CheckCDPActive()

        if (!cdpOk) {
            ; WhatsApp running without CDP — need to restart it
            ToolTip("Reiniciando WhatsApp com debug ativo...")
            WinClose("ahk_exe WhatsApp.Root.exe")
            WinWaitClose("ahk_exe WhatsApp.Root.exe",, 10)
            Sleep 2000
            try Run("explorer.exe shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App")
            WinWait("ahk_exe WhatsApp.Root.exe",, 20)
            Sleep 5000
            SetTimer(() => ToolTip(), -1000)
        }
    } else if (!wasRunning) {
        ; WhatsApp not running — launch it
        try Run("explorer.exe shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App")
        WinWait("ahk_exe WhatsApp.Root.exe",, 20)
        Sleep 5000

        ; Clear the env var so it doesn't leak to other apps
        if (g_privEnabled)
            EnvSet("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "")
    }
}

; ─── Check if WhatsApp CDP is active ──────────────────────────────
CheckCDPActive() {
    global g_debugPort
    pyCheck := A_ScriptDir "\cdp_check.py"
    try {
        exitCode := RunWait("python " '"' pyCheck '" ' g_debugPort, A_ScriptDir, "Hide")
        if (exitCode = 0)
            return true
    }
    try {
        exitCode := RunWait("pythonw " '"' pyCheck '" ' g_debugPort, A_ScriptDir, "Hide")
        if (exitCode = 0)
            return true
    }
    return false
}

; ─── Daemon management ──────────────────────────────────────────────
StartDaemon() {
    global g_daemonPID, g_debugPort
    if (g_daemonPID && ProcessExist(g_daemonPID))
        return
    pyScript := A_ScriptDir "\blur_daemon.py"
    try {
        Run("pythonw " '"' pyScript '" ' g_debugPort, A_ScriptDir, "Hide", &g_daemonPID)
    } catch {
        try {
            Run("python " '"' pyScript '" ' g_debugPort, A_ScriptDir, "Hide", &g_daemonPID)
        } catch {
            g_daemonPID := 0
        }
    }
    ; Check if daemon died immediately (e.g. missing websockets)
    if (g_daemonPID)
        SetTimer(CheckDaemonAlive, -3000)
}

CheckDaemonAlive() {
    global g_daemonPID
    if (g_daemonPID && !ProcessExist(g_daemonPID)) {
        g_daemonPID := 0
        ; Check status file for specific error
        statusFile := A_ScriptDir "\blur_status.txt"
        status := ""
        try status := FileRead(statusFile)
        if (InStr(status, "error_no_websockets")) {
            MsgBox("O blur de privacidade nao pode iniciar porque o modulo 'websockets' nao esta instalado.`n`nAbra o terminal e execute:`npython -m pip install websockets`n`nDepois reinicie o WhatsApp Identifier.", "WhatsApp Identifier - Erro", 48)
        }
    }
}

StopDaemon() {
    global g_daemonPID
    ; Send exit command via file
    cmdFile := A_ScriptDir "\blur_cmd.txt"
    try {
        f := FileOpen(cmdFile, "w")
        f.Write("exit")
        f.Close()
    }
    ; Wait briefly then force-kill if still running
    if (g_daemonPID && ProcessExist(g_daemonPID)) {
        Sleep 500
        if ProcessExist(g_daemonPID)
            ProcessClose(g_daemonPID)
    }
    g_daemonPID := 0
}

OnAppExit(reason, code) {
    StopDaemon()
}

SendBlurCommand(cmd) {
    global g_daemonPID
    ; Ensure daemon is running
    if (!g_daemonPID || !ProcessExist(g_daemonPID))
        StartDaemon()
    cmdFile := A_ScriptDir "\blur_cmd.txt"
    try {
        f := FileOpen(cmdFile, "w")
        f.Write(cmd)
        f.Close()
    }
}

InjectBlur() {
    global g_blurActive, g_blurIntensity
    if (g_blurActive)
        return
    g_blurActive := true
    SendBlurCommand("inject " g_blurIntensity)
}

RemoveBlur() {
    global g_blurActive
    if (!g_blurActive)
        return
    g_blurActive := false
    SendBlurCommand("remove")
}

PrivacyTimerProc() {
    global g_privEnabled, g_hideOnHover, g_hideOnFocus
    global g_idleEnabled, g_idleSeconds, g_lastMouseMove
    global g_blurActive

    ; Master toggle off → remover blur
    if (!g_privEnabled) {
        if (g_blurActive)
            RemoveBlur()
        return
    }

    ; WhatsApp não existe → remover blur
    if !WinExist("ahk_exe WhatsApp.Root.exe") {
        if (g_blurActive)
            RemoveBlur()
        return
    }

    isActive := WinActive("ahk_exe WhatsApp.Root.exe")

    ; WhatsApp em foco + HideOnFocus → remover blur
    if (g_hideOnFocus && isActive) {
        g_lastMouseMove := A_TickCount
        if (g_blurActive)
            RemoveBlur()
        return
    }

    ; Mouse sobre o WhatsApp + HideOnHover → remover blur
    if (g_hideOnHover && isActive) {
        try {
            WinGetPos(&wx, &wy, &ww, &wh, "ahk_exe WhatsApp.Root.exe")
            MouseGetPos(&mx, &my)
            if (mx >= wx && mx <= wx + ww && my >= wy && my <= wy + wh) {
                g_lastMouseMove := A_TickCount
                if (g_blurActive)
                    RemoveBlur()
                return
            }
        }
    }

    ; Idle blur: reativa blur após inatividade
    if (g_idleEnabled && isActive) {
        elapsed := (A_TickCount - g_lastMouseMove) / 1000
        if (elapsed < g_idleSeconds) {
            ; Still active, don't blur yet
            if (g_blurActive)
                RemoveBlur()
            return
        }
        ; Tempo expirado → cai no injetar blur abaixo
    }

    ; WhatsApp sem foco OU privacy sempre ligada → injetar blur
    if (!g_blurActive)
        InjectBlur()
}
