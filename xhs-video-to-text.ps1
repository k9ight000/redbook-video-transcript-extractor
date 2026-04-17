param(
    [string]$Url,
    [string]$Model = "whisper-1",
    [string]$BaseUrl = "",
    [switch]$Local,
    [string]$LocalModel = "medium",
    [string]$LocalLanguage = "",
    [switch]$SetupOnly,
    [string]$DataRoot = "",
    [string]$DownloadRoot = "",
    [string]$OutputRoot = "",
    [string]$XhsRepo = "",
    [string]$ModelRoot = "",
    [string]$PythonHome = ""
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$env:PYTHONUTF8 = "1"

$ScriptRoot = $PSScriptRoot
if (-not $ScriptRoot) {
    $ScriptPath = $MyInvocation.MyCommand.Path
    if ($ScriptPath) {
        $ScriptRoot = Split-Path -Parent $ScriptPath
    }
}
if (-not $ScriptRoot) {
    $ScriptRoot = (Get-Location).Path
}

$RepoRoot = [System.IO.Path]::GetFullPath($ScriptRoot)
$ToolRoot = $RepoRoot
$Helper = Join-Path $RepoRoot "xhs_to_transcript.py"
if (-not (Test-Path $Helper)) {
    throw "Missing helper script: $Helper"
}

$UserHome = [Environment]::GetFolderPath("UserProfile")
if (-not $UserHome) {
    $UserHome = $env:USERPROFILE
}

function Resolve-ToolPath {
    param(
        [string]$Value,
        [string]$EnvName,
        [string]$Default
    )

    $candidate = $Value
    if (-not $candidate -and $EnvName -and (Test-Path "Env:$EnvName")) {
        $candidate = (Get-Item "Env:$EnvName").Value
    }
    if (-not $candidate) {
        $candidate = $Default
    }
    if ([System.IO.Path]::IsPathRooted($candidate)) {
        return [System.IO.Path]::GetFullPath($candidate)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $candidate))
}

$ThirdPartyRoot = Join-Path $RepoRoot "third_party"
$XhsRepo = Resolve-ToolPath $XhsRepo "XHS_DOWNLOADER_REPO" (Join-Path $ThirdPartyRoot "XHS-Downloader")
$PyHome = Resolve-ToolPath $PythonHome "XHS_TRANSCRIBER_PY_HOME" (Join-Path $RepoRoot "python312-embed")
$PyExe = Join-Path $PyHome "python.exe"
$PyZip = Join-Path $RepoRoot "python-3.12.10-embed-amd64.zip"
$DefaultDataRoot = Join-Path $UserHome "ai-media\xhs-video-transcriber"
$DataRoot = Resolve-ToolPath $DataRoot "XHS_TRANSCRIBER_DATA_ROOT" $DefaultDataRoot
$DownloadRoot = Resolve-ToolPath $DownloadRoot "XHS_TRANSCRIBER_DOWNLOAD_ROOT" (Join-Path $DataRoot "downloads")
$OutputRoot = Resolve-ToolPath $OutputRoot "XHS_TRANSCRIBER_OUTPUT_ROOT" (Join-Path $DataRoot "transcripts")
$UvCache = Resolve-ToolPath "" "XHS_TRANSCRIBER_UV_CACHE" (Join-Path $RepoRoot ".cache\uv")
$UvInstallDir = Resolve-ToolPath "" "XHS_TRANSCRIBER_UV_BIN" (Join-Path $RepoRoot ".cache\uv-bin")
$ModelRoot = Resolve-ToolPath $ModelRoot "XHS_TRANSCRIBER_MODEL_ROOT" (Join-Path $RepoRoot "models")
$HfHome = Resolve-ToolPath "" "HF_HOME" (Join-Path $RepoRoot ".cache\huggingface")
$Ct2Cache = Resolve-ToolPath "" "CT2_CACHE_DIR" (Join-Path $RepoRoot ".cache\ct2")

foreach ($dir in @($ToolRoot, $ThirdPartyRoot, $DataRoot, $DownloadRoot, $OutputRoot, $UvCache, $UvInstallDir, $ModelRoot, $HfHome, $Ct2Cache)) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
    }
}

if (-not (Test-Path $XhsRepo)) {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git is required to clone XHS-Downloader. Install Git for Windows or set XHS_DOWNLOADER_REPO to an existing local checkout."
    }
    git clone --depth 1 https://github.com/JoeanAmier/XHS-Downloader.git $XhsRepo
}

if (-not (Test-Path $PyExe)) {
    if (-not (Test-Path $PyZip)) {
        Write-Host "Downloading portable Python 3.12..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip" -OutFile $PyZip -UseBasicParsing
    }
    Expand-Archive -Path $PyZip -DestinationPath $PyHome -Force
}

$Pth = Join-Path $PyHome "python312._pth"
if (Test-Path $Pth) {
    $lineList = [System.Collections.Generic.List[string]]::new()
    Get-Content $Pth | ForEach-Object { [void]$lineList.Add($_) }
    if (-not $lineList.Contains($XhsRepo)) {
        $lineList.Insert([Math]::Min(2, $lineList.Count), $XhsRepo)
    }
    $lines = $lineList.ToArray() | ForEach-Object { if ($_ -eq "#import site") { "import site" } else { $_ } }
    Set-Content -Path $Pth -Value $lines -Encoding ASCII
}

function Get-UvExe {
    $existing = Get-Command uv -ErrorAction SilentlyContinue
    if ($existing) {
        return $existing.Source
    }

    $localUv = Join-Path $UvInstallDir "uv.exe"
    if (Test-Path $localUv) {
        return $localUv
    }

    Write-Host "Installing uv locally..."
    $previousInstallDir = $env:UV_INSTALL_DIR
    $previousNoModifyPath = $env:UV_NO_MODIFY_PATH
    $env:UV_INSTALL_DIR = $UvInstallDir
    $env:UV_NO_MODIFY_PATH = "1"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-Expression (Invoke-RestMethod "https://astral.sh/uv/install.ps1")
    } finally {
        $env:UV_INSTALL_DIR = $previousInstallDir
        $env:UV_NO_MODIFY_PATH = $previousNoModifyPath
    }

    if (-not (Test-Path $localUv)) {
        throw "uv installation failed. Install uv manually, then rerun this script."
    }
    return $localUv
}

$UvExe = Get-UvExe
$env:UV_CACHE_DIR = $UvCache
$env:HF_HOME = $HfHome
$env:HF_HUB_CACHE = Join-Path $env:HF_HOME "hub"
$env:CT2_CACHE_DIR = $Ct2Cache
& $UvExe pip install --python $PyExe -r (Join-Path $XhsRepo "requirements.txt") openai faster-whisper imageio-ffmpeg | Out-Host

if ($SetupOnly) {
    Write-Host "Setup complete."
    Write-Host "Repo root: $RepoRoot"
    Write-Host "XHS-Downloader: $XhsRepo"
    Write-Host "Output root: $OutputRoot"
    Write-Host "Local model root: $ModelRoot"
    return
}

if (-not $Url) {
    throw "Please pass -Url, for example: & `"$RepoRoot\xhs-video-to-text.ps1`" -Url `"https://xhslink.com/xxxx`" -Local"
}

if ($env:XHS_COOKIE -eq "你的小红书网页 Cookie") {
    $env:XHS_COOKIE = ""
}

$cmd = @($Helper, "--url", $Url, "--xhs-repo", $XhsRepo, "--download-root", $DownloadRoot, "--output-root", $OutputRoot, "--model-root", $ModelRoot)
if ($Local) {
    $cmd += @("--local", "--local-model", $LocalModel)
    if ($LocalLanguage) {
        $cmd += @("--local-language", $LocalLanguage)
    }
} else {
    if ($env:OPENAI_API_KEY -eq "你的key") {
        throw "OPENAI_API_KEY is still the placeholder text. Replace it with your real API key or use -Local."
    }
    if (-not $env:OPENAI_API_KEY) {
        throw "OPENAI_API_KEY is not set. Use -Local for offline transcription or set OPENAI_API_KEY for API transcription."
    }
    if (-not $BaseUrl -and $env:OPENAI_BASE_URL) {
        $BaseUrl = $env:OPENAI_BASE_URL
    }
    $cmd += @("--model", $Model)
    if ($BaseUrl) {
        $cmd += @("--base-url", $BaseUrl)
    }
}

& $PyExe @cmd
