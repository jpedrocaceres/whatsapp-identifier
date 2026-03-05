param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$src = $PSScriptRoot

Write-Host "=== WhatsApp Identifier - Build Instalador ===" -ForegroundColor Cyan

# Verifica arquivos necessarios
$required = @("WhatsAppIdentifier.exe","settings_gui.py","blur_inject.py","blur_daemon.py","cdp_check.py","cdp_utils.py")
foreach ($f in $required) {
    if (!(Test-Path (Join-Path $src $f))) {
        Write-Host "ERRO: nao encontrado: $f" -ForegroundColor Red
        Read-Host "Enter para sair"
        exit 1
    }
}

# Pasta temporaria de trabalho
$tmp = Join-Path $env:TEMP ("WAI_build_" + [guid]::NewGuid().ToString("N"))
New-Item $tmp -ItemType Directory | Out-Null

try {
    # Copia arquivos para pasta temporaria
    Copy-Item (Join-Path $src "WhatsAppIdentifier.exe") $tmp
    Copy-Item (Join-Path $src "settings_gui.py")        $tmp
    Copy-Item (Join-Path $src "blur_inject.py")         $tmp
    Copy-Item (Join-Path $src "blur_daemon.py")         $tmp
    Copy-Item (Join-Path $src "cdp_check.py")           $tmp
    Copy-Item (Join-Path $src "cdp_utils.py")           $tmp

    # Script de instalacao que sera embutido
    $installCode = @'
param()
Add-Type -AssemblyName System.Windows.Forms

$installDir = "$env:LOCALAPPDATA\WhatsAppIdentifier"
if (!(Test-Path $installDir)) { New-Item $installDir -ItemType Directory | Out-Null }

# ── Log ────────────────────────────────────────────────────────────
$logFile = Join-Path $installDir "install.log"
function Log($msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

Log "========== INSTALACAO INICIADA =========="
Log "Windows: $([Environment]::OSVersion.VersionString)"
Log "Arch: $env:PROCESSOR_ARCHITECTURE"
Log "User: $env:USERNAME"
Log "InstallDir: $installDir"
Log "TempDir (src): $PSScriptRoot"

# ── Encerra instancia anterior ─────────────────────────────────────
Log "Encerrando WhatsAppIdentifier se estiver rodando..."
Stop-Process -Name "WhatsAppIdentifier" -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 800

# ── Copia arquivos ─────────────────────────────────────────────────
$src2 = $PSScriptRoot
try {
    Copy-Item (Join-Path $src2 "WhatsAppIdentifier.exe") $installDir -Force
    Log "Copiado: WhatsAppIdentifier.exe"
} catch {
    Log "ERRO ao copiar WhatsAppIdentifier.exe: $($_.Exception.Message)"
}
try {
    Copy-Item (Join-Path $src2 "settings_gui.py") $installDir -Force
    Log "Copiado: settings_gui.py"
} catch {
    Log "ERRO ao copiar settings_gui.py: $($_.Exception.Message)"
}
try {
    Copy-Item (Join-Path $src2 "blur_inject.py") $installDir -Force
    Log "Copiado: blur_inject.py"
} catch {
    Log "ERRO ao copiar blur_inject.py: $($_.Exception.Message)"
}
try {
    Copy-Item (Join-Path $src2 "blur_daemon.py") $installDir -Force
    Log "Copiado: blur_daemon.py"
} catch {
    Log "ERRO ao copiar blur_daemon.py: $($_.Exception.Message)"
}
try {
    Copy-Item (Join-Path $src2 "cdp_utils.py") $installDir -Force
    Log "Copiado: cdp_utils.py"
} catch {
    Log "ERRO ao copiar cdp_utils.py: $($_.Exception.Message)"
}

# ── Verifica arquivos copiados ─────────────────────────────────────
$exeExists    = Test-Path (Join-Path $installDir "WhatsAppIdentifier.exe")
$pyExists     = Test-Path (Join-Path $installDir "settings_gui.py")
$blurExists   = Test-Path (Join-Path $installDir "blur_inject.py")
$daemonExists = Test-Path (Join-Path $installDir "blur_daemon.py")
Log "Verificacao: WhatsAppIdentifier.exe=$exeExists, settings_gui.py=$pyExists, blur_inject.py=$blurExists, blur_daemon.py=$daemonExists"

# ── Python ─────────────────────────────────────────────────────────
# Nota: Windows 11 tem alias fake "python" que redireciona para Microsoft Store
# e retorna mensagem de erro sem lancar excecao. Precisamos validar a saida.
Log "Verificando Python..."
$pyFound = $false
try {
    $pyVer = & pythonw --version 2>&1 | Out-String
    if ($pyVer -match "Python \d+\.\d+") {
        $pyFound = $true
        Log "Python encontrado (pythonw): $($pyVer.Trim())"
    } else {
        Log "pythonw retornou saida invalida: $($pyVer.Trim())"
    }
} catch {
    Log "pythonw nao encontrado: $($_.Exception.Message)"
}
if (!$pyFound) {
    try {
        $pyVer = & python --version 2>&1 | Out-String
        if ($pyVer -match "Python \d+\.\d+") {
            $pyFound = $true
            Log "Python encontrado (python): $($pyVer.Trim())"
        } else {
            Log "python retornou saida invalida (alias Microsoft Store?): $($pyVer.Trim())"
        }
    } catch {
        Log "python nao encontrado: $($_.Exception.Message)"
    }
}

if (!$pyFound) {
    $pyUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    $pyInstaller = Join-Path $env:TEMP "python_installer.exe"
    Log "Python nao instalado. Iniciando download: $pyUrl"

    [System.Windows.Forms.MessageBox]::Show(
        "Instalando componente necessario (Python)...`nIsso pode levar alguns minutos.`n`nClique OK e aguarde.",
        "WhatsApp Identifier",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    )

    $downloaded = $false

    # Tentativa 1: WebClient (mais compativel)
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Log "Baixando Python via WebClient..."
        $wc = New-Object System.Net.WebClient
        $wc.DownloadFile($pyUrl, $pyInstaller)
        $wc.Dispose()
        $fileSize = (Get-Item $pyInstaller).Length
        Log "Download concluido (WebClient). Tamanho: $fileSize bytes"
        $downloaded = $true
    } catch {
        Log "WebClient falhou: $($_.Exception.Message)"
    }

    # Tentativa 2: Invoke-WebRequest (fallback)
    if (!$downloaded) {
        try {
            Log "Baixando Python via Invoke-WebRequest..."
            Invoke-WebRequest -Uri $pyUrl -OutFile $pyInstaller -UseBasicParsing
            $fileSize = (Get-Item $pyInstaller).Length
            Log "Download concluido (Invoke-WebRequest). Tamanho: $fileSize bytes"
            $downloaded = $true
        } catch {
            Log "Invoke-WebRequest falhou: $($_.Exception.Message)"
        }
    }

    # Tentativa 3: BITS (Background Intelligent Transfer Service)
    if (!$downloaded) {
        try {
            Log "Baixando Python via BITS..."
            Start-BitsTransfer -Source $pyUrl -Destination $pyInstaller -ErrorAction Stop
            $fileSize = (Get-Item $pyInstaller).Length
            Log "Download concluido (BITS). Tamanho: $fileSize bytes"
            $downloaded = $true
        } catch {
            Log "BITS falhou: $($_.Exception.Message)"
        }
    }

    if ($downloaded) {
        try {
            Log "Executando instalador Python silencioso..."
            $proc = Start-Process $pyInstaller -ArgumentList '/quiet','InstallAllUsers=0','PrependPath=1','Include_pip=1','Include_doc=0','Include_test=0','Include_dev=0','Include_launcher=0','Include_tcltk=1' -Wait -PassThru
            Log "Instalador Python finalizado. ExitCode: $($proc.ExitCode)"

            Remove-Item $pyInstaller -Force -ErrorAction SilentlyContinue

            # Atualiza PATH da sessao atual
            $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
            $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
            $env:Path = "$userPath;$machinePath"
            Log "PATH atualizado: $env:Path"

            # Verifica se Python agora esta disponivel
            $pyOk = $false
            try {
                $pyVerNew = & pythonw --version 2>&1 | Out-String
                if ($pyVerNew -match "Python \d+\.\d+") {
                    Log "Python pos-instalacao OK (pythonw): $($pyVerNew.Trim())"
                    $pyOk = $true
                }
            } catch {}
            if (!$pyOk) {
                try {
                    $pyVerNew = & python --version 2>&1 | Out-String
                    if ($pyVerNew -match "Python \d+\.\d+") {
                        Log "Python pos-instalacao OK (python): $($pyVerNew.Trim())"
                        $pyOk = $true
                    }
                } catch {}
            }
            if (!$pyOk) {
                Log "AVISO: Python instalado mas nao encontrado no PATH desta sessao. Funcionara apos reiniciar."
            }
        } catch {
            Log "ERRO ao executar instalador Python: $($_.Exception.Message)"
            [System.Windows.Forms.MessageBox]::Show(
                "Erro ao instalar Python: $($_.Exception.Message)`n`nLog salvo em:`n$logFile",
                "WhatsApp Identifier - Erro",
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Error
            )
        }
    } else {
        Log "ERRO: todas as tentativas de download falharam"
        $resp = [System.Windows.Forms.MessageBox]::Show(
            "Nao foi possivel baixar o Python automaticamente.`nDeseja abrir o site para instalar manualmente?`n`nApos instalar, execute este instalador novamente.`n`nLog salvo em:`n$logFile",
            "WhatsApp Identifier - Erro",
            [System.Windows.Forms.MessageBoxButtons]::YesNo,
            [System.Windows.Forms.MessageBoxIcon]::Error
        )
        if ($resp -eq [System.Windows.Forms.DialogResult]::Yes) {
            Start-Process "https://www.python.org/downloads/"
        }
    }
} else {
    Log "Python ja estava instalado, prosseguindo"
}

# ── Instalar modulo websockets (necessario para blur CSS) ─────────
Log "Verificando/instalando modulo websockets..."
$wsInstalled = $false

# Tenta com pythonw primeiro, depois python
foreach ($pyCmd in @("pythonw", "python")) {
    try {
        $pipCheck = & $pyCmd -c "import websockets; print('ok')" 2>&1 | Out-String
        if ($pipCheck -match "ok") {
            Log "websockets ja instalado (via $pyCmd)"
            $wsInstalled = $true
            break
        }
    } catch {}
}

if (!$wsInstalled) {
    Log "websockets nao encontrado, instalando..."
    # Tenta pip install com ambos os comandos
    foreach ($pyCmd in @("pythonw", "python")) {
        try {
            $pipOut = & $pyCmd -m pip install websockets --quiet 2>&1 | Out-String
            Log "pip install websockets ($pyCmd): $($pipOut.Trim())"
            # Verifica se instalou
            $check2 = & $pyCmd -c "import websockets; print('ok')" 2>&1 | Out-String
            if ($check2 -match "ok") {
                Log "websockets instalado com sucesso via $pyCmd"
                $wsInstalled = $true
                break
            }
        } catch {
            Log "pip install via $pyCmd falhou: $($_.Exception.Message)"
        }
    }
    if (!$wsInstalled) {
        Log "AVISO: nao foi possivel instalar websockets com nenhum comando Python"
    }
}

# ── Configurar WebView2 debug port (necessario para blur CSS) ─────
Log "Configurando WebView2 debug port..."
try {
    $envName = "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"
    [Environment]::SetEnvironmentVariable($envName, "--remote-debugging-port=9251", "User")
    Log "WebView2 debug port configurado: --remote-debugging-port=9251"
} catch {
    Log "AVISO: nao foi possivel configurar WebView2 debug port: $($_.Exception.Message)"
}

# ── Registro: Startup ──────────────────────────────────────────────
try {
    $regRun = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    Set-ItemProperty $regRun -Name "WhatsApp Identifier" -Value "`"$installDir\WhatsAppIdentifier.exe`""
    Log "Registro autostart configurado"
} catch {
    Log "ERRO ao configurar autostart: $($_.Exception.Message)"
}

# ── Registro: Painel de Controle ───────────────────────────────────
try {
    $regUni = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\WhatsAppIdentifier"
    if (!(Test-Path $regUni)) { New-Item $regUni -Force | Out-Null }
    Set-ItemProperty $regUni "DisplayName"     "WhatsApp Identifier"
    Set-ItemProperty $regUni "DisplayVersion"  "3.5.1"
    Set-ItemProperty $regUni "Publisher"       "JoaoPedro"
    Set-ItemProperty $regUni "InstallLocation" $installDir
    Set-ItemProperty $regUni "NoModify"        1 -Type DWord
    Set-ItemProperty $regUni "NoRepair"        1 -Type DWord
    Log "Registro uninstall configurado"
} catch {
    Log "ERRO ao configurar registro uninstall: $($_.Exception.Message)"
}

# ── Inicia o app ───────────────────────────────────────────────────
try {
    Start-Process (Join-Path $installDir "WhatsAppIdentifier.exe")
    Log "App iniciado com sucesso"
} catch {
    Log "ERRO ao iniciar app: $($_.Exception.Message)"
}

Log "========== INSTALACAO FINALIZADA =========="

[System.Windows.Forms.MessageBox]::Show(
    "Instalacao concluida!`n`nO WhatsApp Identifier esta ativo na bandeja do sistema.`nIniciara automaticamente com o Windows.`n`nIMPORTANTE: Para o blur de privacidade funcionar,`nfeche e reabra o WhatsApp Desktop uma vez.`n`nLog salvo em:`n$logFile",
    "WhatsApp Identifier",
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Information
)
'@
    $installCode | Set-Content (Join-Path $tmp "Install.ps1") -Encoding UTF8

    # Cria ZIP com todos os arquivos
    $zipPath = Join-Path $src "WAI_temp.zip"
    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($tmp, $zipPath)

    # Le o ZIP e converte para base64
    $zipBytes  = [System.IO.File]::ReadAllBytes($zipPath)
    $zipBase64 = [Convert]::ToBase64String($zipBytes)
    Remove-Item $zipPath -Force

    # Gera o script PS1 auto-extraivel (SFX)
    $sfxLines = @()
    $sfxLines += 'Add-Type -AssemblyName System.IO.Compression.FileSystem'
    $sfxLines += 'Add-Type -AssemblyName System.Windows.Forms'
    $sfxLines += '$b64 = "' + $zipBase64 + '"'
    $sfxLines += '$tmpDir = Join-Path $env:TEMP ("WAI_" + [guid]::NewGuid().ToString("N"))'
    $sfxLines += 'New-Item $tmpDir -ItemType Directory | Out-Null'
    $sfxLines += 'try {'
    $sfxLines += '  $zp = Join-Path $tmpDir "f.zip"'
    $sfxLines += '  [System.IO.File]::WriteAllBytes($zp, [Convert]::FromBase64String($b64))'
    $sfxLines += '  [System.IO.Compression.ZipFile]::ExtractToDirectory($zp, $tmpDir)'
    $sfxLines += '  & powershell.exe -ExecutionPolicy Bypass -File (Join-Path $tmpDir "Install.ps1")'
    $sfxLines += '} catch {'
    $sfxLines += '  [System.Windows.Forms.MessageBox]::Show("Erro: " + $_.Exception.Message)'
    $sfxLines += '} finally {'
    $sfxLines += '  Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue'
    $sfxLines += '}'

    $sfxPs1 = Join-Path $src "WhatsAppIdentifier_Setup.ps1"
    $sfxLines | Set-Content $sfxPs1 -Encoding UTF8

    Write-Host "Script de instalacao gerado: WhatsAppIdentifier_Setup.ps1" -ForegroundColor Green

    # Tenta instalar ps2exe e converter para .exe
    $setupExe = Join-Path $src "WAIdentifier_Setup_v3.5.1.exe"
    $converted = $false

    try {
        Write-Host "Tentando instalar ps2exe para gerar .exe..." -ForegroundColor Yellow
        if (!(Get-Module -ListAvailable -Name ps2exe)) {
            Install-PackageProvider NuGet -MinimumVersion 2.8.5.201 -Force -Scope CurrentUser -ErrorAction Stop | Out-Null
            Install-Module ps2exe -Force -Scope CurrentUser -ErrorAction Stop | Out-Null
        }
        Import-Module ps2exe -ErrorAction Stop
        Invoke-ps2exe -inputFile $sfxPs1 -outputFile $setupExe -noConsole -title "WhatsApp Identifier Setup" -ErrorAction Stop
        $converted = $true
        Remove-Item $sfxPs1 -Force -ErrorAction SilentlyContinue
        Write-Host ""
        Write-Host "INSTALADOR GERADO:" -ForegroundColor Green
        Write-Host "  $setupExe" -ForegroundColor Cyan
    } catch {
        Write-Host "ps2exe nao disponivel. Gerando instalador .bat..." -ForegroundColor Yellow
        $batPath = Join-Path $src "WhatsAppIdentifier_Setup.bat"
        $batContent = "@echo off`r`ntitle WhatsApp Identifier - Instalador`r`npowershell.exe -ExecutionPolicy Bypass -File `"%~dp0WhatsAppIdentifier_Setup.ps1`"`r`n"
        [System.IO.File]::WriteAllText($batPath, $batContent, [System.Text.Encoding]::ASCII)
        Write-Host ""
        Write-Host "INSTALADOR GERADO (.bat):" -ForegroundColor Green
        Write-Host "  $batPath" -ForegroundColor Cyan
        Write-Host "  $sfxPs1" -ForegroundColor Cyan
        Write-Host "(distribua os 2 arquivos juntos)" -ForegroundColor Yellow
    }

} finally {
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Read-Host "Pressione Enter para sair"
