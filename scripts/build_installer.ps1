[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$python = Join-Path $root ".venv\Scripts\python.exe"
$spec = Join-Path $root "packaging\nexor_simulador.spec"
$iss = Join-Path $root "packaging\Instalar_Nexor_Simulador.iss"
$output = Join-Path $root "release\Instalar_Nexor_Simulador.exe"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Remove-BuildDirectory([string]$Name) {
    $target = [System.IO.Path]::GetFullPath((Join-Path $root $Name))
    $rootPrefix = $root.TrimEnd('\') + '\'
    if (-not $target.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Diretório de build fora do workspace: $target"
    }
    if (Test-Path -LiteralPath $target) {
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}

if (-not (Test-Path -LiteralPath $python)) {
    throw "Ambiente virtual não encontrado. Execute ABRIR_SIMULADOR.bat primeiro."
}

$isccCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
)
$iscc = $isccCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if (-not $iscc) {
    $isccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($isccCommand) {
        $iscc = $isccCommand.Source
    }
}
if (-not $iscc) {
    throw "Inno Setup 6 não encontrado. Instale JRSoftware.InnoSetup antes do build."
}

Write-Step "Validando testes"
Push-Location $root
try {
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw "Os testes falharam. O instalador não será gerado."
    }

    Write-Step "Limpando artefatos anteriores"
    Remove-BuildDirectory "build"
    Remove-BuildDirectory "dist"
    Remove-BuildDirectory "release"

    Write-Step "Gerando aplicação autocontida com PyInstaller"
    & $python -m PyInstaller --noconfirm --clean --workpath (Join-Path $root "build") --distpath (Join-Path $root "dist") $spec
    if ($LASTEXITCODE -ne 0) {
        throw "O PyInstaller falhou."
    }

    Write-Step "Compilando instalador Windows"
    & $iscc $iss
    if ($LASTEXITCODE -ne 0) {
        throw "O Inno Setup falhou."
    }
}
finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $output)) {
    throw "Instalador não encontrado após o build: $output"
}

$hash = (Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash
$sizeMb = [math]::Round((Get-Item -LiteralPath $output).Length / 1MB, 2)
Write-Host ""
Write-Host "Instalador gerado com sucesso:" -ForegroundColor Green
Write-Host $output
Write-Host "Tamanho: $sizeMb MB"
Write-Host "SHA-256: $hash"
