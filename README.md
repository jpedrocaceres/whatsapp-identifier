# WhatsApp Identifier

Adiciona automaticamente seu nome como identificador antes de cada mensagem enviada no WhatsApp. Disponivel como **extensao Chrome** (WhatsApp Web) e **app Desktop** (WhatsApp Desktop via AutoHotkey).

## Resultado

```
*Joao Pedro:*
Bom dia!
```

---

## Extensao Chrome (WhatsApp Web)

### Instalacao

1. Abra `chrome://extensions/`
2. Ative o **Modo do desenvolvedor**
3. Clique em **Carregar sem compactacao**
4. Selecione a pasta `extension/`

### Funcionalidades

- Prefixo automatico com nome em negrito
- Toggle ativar/desativar
- Preview em tempo real
- Deteccao anti-duplicacao (nao adiciona prefixo duas vezes)
- Interceptacao via Enter e botao de enviar
- **Privacy Blur**: desfoca mensagens, previews e midia com reveal por hover

### Estrutura

```
extension/
  manifest.json   - Manifest V3
  content.js      - Script injetado no WhatsApp Web
  content.css     - Estilos injetados
  popup.html/js/css - Interface de configuracao
  icons/          - Icones da extensao
```

---

## App Desktop (WhatsApp Desktop)

### Requisitos

- Windows 10/11
- [AutoHotkey v2](https://www.autohotkey.com/) (para desenvolvimento)
- Python 3 (para Privacy Blur e GUI de configuracoes)
- Pacote `websockets` (`pip install websockets`)

### Download

Baixe o instalador na pagina de [Releases](../../releases/latest).

### Instalacao

Execute o instalador `WAIdentifier_Setup_v*.exe` baixado da pagina de Releases.

O instalador:
- Copia os arquivos necessarios para `%LocalAppData%\WhatsAppIdentifier`
- Configura inicializacao automatica com Windows
- Instala Python e `websockets` se necessario
- Configura a variavel `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS` para habilitar o CDP (Chrome DevTools Protocol)

> **Importante:** Apos instalar, reinicie o WhatsApp Desktop para que o debug port seja ativado.

### Funcionalidades

- Prefixo automatico com nome em negrito (intercepta Enter)
- GUI de configuracao (nome, ativar/desativar, privacy blur)
- Tray icon com menu de acesso rapido
- **Privacy Blur**: blur via CSS injection pelo CDP, com reveal por hover
- Daemon persistente (`blur_daemon.py`) para blur instantaneo via WebSocket

### Estrutura

```
Desktop_extension/
  WhatsAppIdentifier.ahk   - Script principal (AutoHotkey v2)
  blur_daemon.py            - Daemon WebSocket para blur instantaneo
  blur_inject.py            - Script one-shot de blur (fallback)
  settings_gui.py           - GUI de configuracao (tkinter)
  Build-Installer.ps1       - Gera instalador .exe
```

### Arquitetura do Privacy Blur

1. O AHK inicia o `blur_daemon.py` como processo em background
2. O daemon mantém conexao WebSocket com o WhatsApp via CDP (porta 9250)
3. Comandos sao passados via arquivo `blur_cmd.txt` (inject/remove/exit)
4. O CSS injetado aplica `filter: blur()` nos elementos e usa `:hover` para revelar individualmente

---

## Desenvolvimento

### Extensao Chrome

1. Edite os arquivos em `extension/`
2. Em `chrome://extensions/`, clique em recarregar
3. Recarregue a aba do WhatsApp Web

### Desktop

1. Edite `WhatsAppIdentifier.ahk`
2. Compile com `Ahk2Exe.exe` ou rode diretamente com AutoHotkey v2
3. Para rebuild do instalador: `powershell -ExecutionPolicy Bypass -File Build-Installer.ps1`

## Notas Tecnicas

- WhatsApp Web usa React com `contenteditable` divs - a insercao de texto e feita via `ClipboardEvent('paste')`
- WhatsApp Desktop usa WebView2 - o CDP e habilitado via variavel de ambiente `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS`
- O processo do WhatsApp Desktop e `WhatsApp.Root.exe` (nao `WhatsApp.exe`)
- Porta CDP padrao: **9250** (evita conflito com Power BI e outros apps WebView2)

## Versoes

| Componente | Versao |
|---|---|
| Extensao Chrome | 7.1.0 |
| Desktop Installer | 3.3 |
