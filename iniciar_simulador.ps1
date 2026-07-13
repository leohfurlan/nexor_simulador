[CmdletBinding()]
param(
    [switch]$SemNavegador,
    [switch]$SomenteVerificar
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-RepositoryUrl([string]$LauncherDirectory) {
    if ($env:NEXOR_SIMULADOR_REPO_URL) {
        return $env:NEXOR_SIMULADOR_REPO_URL.Trim()
    }

    $configPath = Join-Path $LauncherDirectory "repositorio_git.txt"
    if (-not (Test-Path -LiteralPath $configPath)) {
        return $null
    }

    $line = Get-Content -LiteralPath $configPath -Encoding UTF8 |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ -and -not $_.StartsWith("#") } |
        Select-Object -First 1

    if ($line -and $line -match "^(https?://|ssh://|git@)") {
        return $line
    }
    return $null
}

function Test-GitRepository([string]$Directory) {
    if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) {
        return $false
    }
    if (-not (Test-Path -LiteralPath $Directory)) {
        return $false
    }

    # Evita chamar o Git para pastas .git vazias ou incompletas, como pode
    # acontecer em pacotes copiados fora de um clone real.
    $gitMarker = Join-Path $Directory ".git"
    if (-not (Test-Path -LiteralPath $gitMarker)) {
        return $false
    }
    if ((Get-Item -LiteralPath $gitMarker).PSIsContainer -and
        -not (Test-Path -LiteralPath (Join-Path $gitMarker "HEAD"))) {
        return $false
    }

    & git.exe -C $Directory rev-parse --is-inside-work-tree *> $null
    return $LASTEXITCODE -eq 0
}

function Test-GitRemote([string]$Directory) {
    if (-not (Test-GitRepository $Directory)) {
        return $false
    }

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $remoteUrl = & git.exe -C $Directory config --get remote.origin.url 2>$null
        return $LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($remoteUrl)
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Update-GitRepository([string]$Directory) {
    Write-Step "Procurando atualizacoes do simulador"
    & git.exe -C $Directory pull --ff-only
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Nao foi possivel atualizar agora. A versao instalada sera utilizada."
    }
}

function Get-PythonLauncher {
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        return @{ Command = $python.Source; Arguments = @() }
    }

    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        return @{ Command = $py.Source; Arguments = @("-3") }
    }

    throw "Python 3 nao foi encontrado. Instale pelo site https://www.python.org/downloads/ e marque a opcao 'Add Python to PATH'."
}

function Test-NexorRunning([int]$Port) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/empresas" -TimeoutSec 1
        return $response.StatusCode -eq 200 -and $response.Content -match "Nexor"
    }
    catch {
        return $false
    }
}

function Get-FreePort {
    foreach ($port in 8000..8010) {
        $listener = $null
        try {
            $listener = [System.Net.Sockets.TcpListener]::new(
                [System.Net.IPAddress]::Loopback,
                $port
            )
            $listener.Start()
            return $port
        }
        catch {
            continue
        }
        finally {
            if ($listener) {
                $listener.Stop()
            }
        }
    }
    throw "Nenhuma porta livre foi encontrada entre 8000 e 8010."
}

try {
    $launcherDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
    $projectDirectory = $launcherDirectory
    $repositoryUrl = Get-RepositoryUrl $launcherDirectory
    $gitAvailable = [bool](Get-Command git.exe -ErrorAction SilentlyContinue)

    Write-Host "===============================================" -ForegroundColor DarkCyan
    Write-Host "       NEXOR - SIMULADOR TRIBUTARIO" -ForegroundColor White
    Write-Host "===============================================" -ForegroundColor DarkCyan

    if ((Test-GitRepository $launcherDirectory) -and (Test-GitRemote $launcherDirectory)) {
        Update-GitRepository $launcherDirectory
    }
    elseif ($repositoryUrl) {
        if (-not $gitAvailable) {
            if (Test-Path -LiteralPath (Join-Path $launcherDirectory "app\main.py")) {
                Write-Warning "Git nao foi encontrado. A copia local enviada sera utilizada sem atualizacao automatica."
            }
            else {
                throw "Git nao foi encontrado. Instale pelo site https://git-scm.com/download/win para baixar ou atualizar o simulador."
            }
        }
        else {
            $installDirectory = Join-Path $env:LOCALAPPDATA "NexorSimulador"
            if (Test-GitRepository $installDirectory) {
                $projectDirectory = $installDirectory
                Update-GitRepository $projectDirectory
            }
            elseif (Test-Path -LiteralPath $installDirectory) {
                if (Test-Path -LiteralPath (Join-Path $launcherDirectory "app\main.py")) {
                    Write-Warning "A instalacao automatica existente nao e valida. A copia local enviada sera utilizada."
                }
                else {
                    throw "A pasta $installDirectory ja existe, mas nao e um repositorio Git valido. Renomeie ou remova essa pasta e tente novamente."
                }
            }
            else {
                Write-Step "Baixando o simulador pela primeira vez"
                & git.exe clone $repositoryUrl $installDirectory
                if ($LASTEXITCODE -eq 0) {
                    $projectDirectory = $installDirectory
                }
                elseif (Test-Path -LiteralPath (Join-Path $launcherDirectory "app\main.py")) {
                    Write-Warning "Nao foi possivel acessar o repositorio privado. A copia local enviada sera utilizada."
                }
                else {
                    throw "O download do repositorio falhou. Verifique a internet e o acesso ao repositorio."
                }
            }
        }
    }
    elseif (-not (Test-Path -LiteralPath (Join-Path $projectDirectory "app\main.py"))) {
        throw "Os arquivos da aplicacao nao foram encontrados e repositorio_git.txt nao possui uma URL valida."
    }
    else {
        Write-Host "Usando a copia local enviada pelo responsavel." -ForegroundColor DarkGray
    }

    $mainFile = Join-Path $projectDirectory "app\main.py"
    $requirementsFile = Join-Path $projectDirectory "requirements.txt"
    if (-not (Test-Path -LiteralPath $mainFile)) {
        throw "Arquivo principal nao encontrado: $mainFile"
    }
    if (-not (Test-Path -LiteralPath $requirementsFile)) {
        throw "Arquivo de dependencias nao encontrado: $requirementsFile"
    }

    $pythonLauncher = Get-PythonLauncher
    Write-Step "Python encontrado"
    & $pythonLauncher.Command @($pythonLauncher.Arguments) --version
    if ($LASTEXITCODE -ne 0) {
        throw "O Python foi encontrado, mas nao conseguiu iniciar."
    }

    if ($SomenteVerificar) {
        Write-Host ""
        Write-Host "Verificacao concluida. O inicializador esta configurado corretamente." -ForegroundColor Green
        exit 0
    }

    $venvDirectory = Join-Path $projectDirectory ".venv"
    $venvPython = Join-Path $venvDirectory "Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-Step "Preparando o ambiente do simulador"
        & $pythonLauncher.Command @($pythonLauncher.Arguments) -m venv $venvDirectory
        if ($LASTEXITCODE -ne 0) {
            throw "Nao foi possivel criar o ambiente virtual Python."
        }
    }

    $venvPip = Join-Path $venvDirectory "Scripts\pip.exe"
    if (-not (Test-Path -LiteralPath $venvPip)) {
        Write-Step "Preparando o instalador de componentes Python"
        & $venvPython -m ensurepip --upgrade
        if ($LASTEXITCODE -ne 0) {
            throw "Nao foi possivel habilitar o pip no ambiente virtual."
        }
    }

    Write-Step "Instalando ou atualizando os componentes necessarios"
    & $venvPython -m pip install --disable-pip-version-check -r $requirementsFile
    if ($LASTEXITCODE -ne 0) {
        throw "A instalacao das dependencias falhou. Verifique a conexao com a internet."
    }

    Write-Step "Preparando o banco de dados"
    Push-Location $projectDirectory
    try {
        & $venvPython -m app.seeds
        if ($LASTEXITCODE -ne 0) {
            throw "Nao foi possivel preparar o banco de dados."
        }
    }
    finally {
        Pop-Location
    }

    foreach ($candidatePort in 8000..8010) {
        if (Test-NexorRunning $candidatePort) {
            $runningUrl = "http://127.0.0.1:$candidatePort/"
            Write-Host "O simulador ja esta aberto em $runningUrl" -ForegroundColor Green
            if (-not $SemNavegador) {
                Start-Process $runningUrl
            }
            exit 0
        }
    }

    $port = Get-FreePort
    $url = "http://127.0.0.1:$port/"

    Write-Step "Iniciando o simulador"
    Write-Host "Endereco: $url" -ForegroundColor Green
    Write-Host "Mantenha esta janela aberta enquanto estiver usando o sistema." -ForegroundColor Yellow
    Write-Host "Para encerrar, feche esta janela ou pressione Ctrl+C." -ForegroundColor Yellow

    $browserJob = $null
    if (-not $SemNavegador) {
        $browserJob = Start-Job -ScriptBlock {
            param($ApplicationUrl)
            foreach ($attempt in 1..30) {
                try {
                    $response = Invoke-WebRequest -UseBasicParsing -Uri $ApplicationUrl -TimeoutSec 2
                    if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                        Start-Process $ApplicationUrl
                        return
                    }
                }
                catch {
                    Start-Sleep -Seconds 1
                }
            }
        } -ArgumentList $url
    }

    Push-Location $projectDirectory
    try {
        & $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port $port
        exit $LASTEXITCODE
    }
    finally {
        Pop-Location
        if ($browserJob) {
            Remove-Job -Job $browserJob -Force -ErrorAction SilentlyContinue
        }
    }
}
catch {
    Write-Host ""
    Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
