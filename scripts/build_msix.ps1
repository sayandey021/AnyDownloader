# build_msix.ps1
# This script packages the Flet executable into an MSIX file and signs it with a self-signed certificate.

$IdentityName = "Saayan.AnyDownloader"
$AppName = "AnyDownloader"
$DisplayName = "Any Downloader"
$PublisherName = "CN=37E2AF47-D2FC-489C-BDC1-02C989A7B989"
$PublisherDisplayName = "Saayan"
$Version = "1.1.0.0"
$ExePath = "..\dist\AnyDownloaderApp.exe"
$MsixDir = "..\MsixTemp"
$MsixPath = "..\dist\AnyDownloader.msix"
$CertPath = "..\AnyDownloaderCert.pfx"
$CertPassword = "password123"

if (-not (Test-Path $ExePath)) {
    Write-Host "Error: Executable not found at $ExePath. Run 'flet pack' first." -ForegroundColor Red
    exit 1
}

# 1. Prepare Directory
Write-Host "Preparing MSIX Directory..."
if (Test-Path $MsixDir) { Remove-Item -Recurse -Force $MsixDir }
New-Item -ItemType Directory -Path $MsixDir | Out-Null
New-Item -ItemType Directory -Path "$MsixDir\assets" | Out-Null

Copy-Item $ExePath -Destination $MsixDir
if (Test-Path "..\assets") {
    Copy-Item "..\assets\*" -Destination "$MsixDir\assets" -Recurse
}

# 2. Generate AppxManifest.xml
Write-Host "Generating AppxManifest.xml..."
$Manifest = @"
<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities">
  <Identity Name="$IdentityName" ProcessorArchitecture="x64" Publisher="$PublisherName" Version="$Version" />
  <Properties>
    <DisplayName>$DisplayName</DisplayName>
    <PublisherDisplayName>$PublisherDisplayName</PublisherDisplayName>
    <Logo>assets\icon.png</Logo>
  </Properties>
  <Resources>
    <Resource Language="en-US" />
  </Resources>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.19041.0" />
  </Dependencies>
  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
    <Capability Name="internetClient" />
  </Capabilities>
  <Applications>
    <Application Id="$AppName" Executable="AnyDownloaderApp.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements DisplayName="$DisplayName" Description="A modern video and audio downloader" BackgroundColor="transparent" Square150x150Logo="assets\icon.png" Square44x44Logo="assets\icon.png">
      </uap:VisualElements>
    </Application>
  </Applications>
</Package>
"@
Set-Content -Path "$MsixDir\AppxManifest.xml" -Value $Manifest

# 3. Locate Windows SDK Tools
Write-Host "Locating Windows SDK Tools..."
$SdkPath = "C:\Program Files (x86)\Windows Kits\10\bin"
$MakeAppx = Get-ChildItem -Path $SdkPath -Filter "makeappx.exe" -Recurse | Where-Object { $_.DirectoryName -match "x64" } | Select-Object -First 1
$SignTool = Get-ChildItem -Path $SdkPath -Filter "signtool.exe" -Recurse | Where-Object { $_.DirectoryName -match "x64" } | Select-Object -First 1

if (-not $MakeAppx -or -not $SignTool) {
    Write-Host "Error: MakeAppx.exe or SignTool.exe not found. Please install the Windows 10/11 SDK." -ForegroundColor Red
    exit 1
}

# 4. Create MSIX
Write-Host "Packaging MSIX..."
if (Test-Path $MsixPath) { Remove-Item -Force $MsixPath }
& $MakeAppx.FullName pack /d $MsixDir /p $MsixPath

# 5. Generate Certificate if not exists
if (-not (Test-Path $CertPath)) {
    Write-Host "Generating Self-Signed Certificate..."
    Import-Module Microsoft.PowerShell.Security -ErrorAction SilentlyContinue
    Import-Module PKI -ErrorAction SilentlyContinue
    
    $Cert = New-SelfSignedCertificate -Type Custom -Subject $PublisherName -KeyUsage DigitalSignature -FriendlyName $AppName -CertStoreLocation "Cert:\CurrentUser\My" -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
    $SecurePassword = ConvertTo-SecureString -String $CertPassword -Force -AsPlainText
    Export-PfxCertificate -Cert "Cert:\CurrentUser\My\$($Cert.Thumbprint)" -FilePath $CertPath -Password $SecurePassword | Out-Null
}

# 6. Sign MSIX
Write-Host "Signing MSIX..."
& $SignTool.FullName sign /fd SHA256 /a /f $CertPath /p $CertPassword $MsixPath

Write-Host "Done! Your MSIX package is ready at: $MsixPath" -ForegroundColor Green
Write-Host "Note: You must install the $CertPath certificate to your 'Trusted Root Certification Authorities' before Windows will let you install the MSIX." -ForegroundColor Yellow
