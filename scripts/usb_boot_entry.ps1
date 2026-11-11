<#
.SYNOPSIS
  Register (or remove) a firmware boot entry for the plug-and-unlock USB stick.

.DESCRIPTION
  Puts a firmware entry for the stick ahead of Windows Boot Manager, so that:
    stick plugged in  -> firmware boots the stick, the image unlocks, Windows starts
    stick removed     -> firmware falls back to Windows Boot Manager

  Default is a dry run. Nothing changes until -Apply is given.

  The entry points at \EFI\BOOT\BOOTX64.EFI on the stick. Only the automatic
  image is accepted, and only when its SHA-256 matches the released image.

.PARAMETER VolumeLabel
  Volume label of the stick. Default: GPUAUTO2820

.PARAMETER Apply
  Actually create the entry and change the firmware boot order.

.PARAMETER Remove
  Delete the entry recorded by a previous -Apply and restore the boot order.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\usb_boot_entry.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\usb_boot_entry.ps1 -Apply
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\usb_boot_entry.ps1 -Remove -Apply
#>
[CmdletBinding()]
param(
    [string]$VolumeLabel = 'GPUAUTO2820',
    [string]$Description = 'RTX 4070 Laptop unlock (USB)',
    [switch]$Apply,
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$AutoImageSha256 = '58085A8D9F9DCE0D36D01114FC5E87208639A1F2CFDD179658BA5D15E3154986'
$RecordDir = Join-Path $env:ProgramData 'Rtx4070Unlock'
$RecordPath = Join-Path $RecordDir 'usb-entry.json'
$EfiPath = '\EFI\BOOT\BOOTX64.EFI'

function Step($text) {
    if ($Apply) { Write-Host "[do]   $text" } else { Write-Host "[plan] $text" }
}

function Get-FirmwareOrder {
    $out = & bcdedit /enum '{fwbootmgr}' 2>$null
    foreach ($line in $out) {
        if ($line -match '^displayorder\s+(.*)$') {
            return @([regex]::Matches($Matches[1], '\{[0-9a-fA-F-]{36}\}') |
                     ForEach-Object { $_.Value.ToLower() })
        }
    }
    return @()
}

function Get-EntryValue($id, $name) {
    $out = & bcdedit /enum $id 2>$null
    foreach ($line in $out) {
        if ($line -match "^\s*$name\s+(.+?)\s*$") { return $Matches[1] }
    }
    return $null
}

# ---------------------------------------------------------------- preflight
try { $secureBoot = Confirm-SecureBootUEFI } catch { $secureBoot = $null }
if ($null -eq $secureBoot) { throw 'This PC is not booted in UEFI mode; the stick cannot be a UEFI boot entry.' }
if ($secureBoot) { throw 'Secure Boot is ON. The images are unsigned: turn Secure Boot off first.' }
Write-Host 'Secure Boot: off'

$power = 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power'
$fastStartup = (Get-ItemProperty -Path $power -Name HiberbootEnabled -ErrorAction SilentlyContinue).HiberbootEnabled
if ($fastStartup -eq 1) {
    Write-Warning 'Fast Startup is ON. A Windows "shut down" may skip the firmware boot path, so the stick would not run. Turn it off: powercfg /h off'
}

if ($Remove) {
    if (-not (Test-Path $RecordPath)) {
        throw "No install record at $RecordPath; nothing to remove. If an entry was created by hand, delete it with: bcdedit /enum firmware"
    }
    $rec = Get-Content $RecordPath -Raw | ConvertFrom-Json
    Step "delete firmware entry $($rec.entry) '$($rec.description)'"
    if ($Apply) {
        & bcdedit /delete $rec.entry | Out-Null
        $order = Get-FirmwareOrder
        if ($order -contains $rec.entry.ToLower()) {
            $rest = $order | Where-Object { $_ -ne $rec.entry.ToLower() }
            & bcdedit /set '{fwbootmgr}' displayorder @rest | Out-Null
        }
        Remove-Item $RecordPath -Force
        Write-Host "Firmware boot order: $((Get-FirmwareOrder) -join ', ')"
    }
    return
}

# ---------------------------------------------------------------- the stick
$vol = Get-Volume | Where-Object { $_.FileSystemLabel -eq $VolumeLabel } | Select-Object -First 1
if (-not $vol) { throw "No volume labelled '$VolumeLabel'. Plug the stick in, or pass -VolumeLabel." }
if ($vol.FileSystem -ne 'FAT32') { throw "$VolumeLabel is $($vol.FileSystem), not FAT32." }
if ($vol.DriveType -ne 'Removable') { throw "$VolumeLabel is not a removable volume; refusing." }
$root = "$($vol.DriveLetter):\"
Write-Host "Stick: $root  $($vol.FileSystemLabel)  $([math]::Round($vol.Size / 1GB, 2)) GB"

$efi = Join-Path $root $EfiPath.TrimStart('\')
if (-not (Test-Path $efi)) { throw "Missing $EfiPath on $root" }
$hash = (Get-FileHash $efi -Algorithm SHA256).Hash
if ($hash -ne $AutoImageSha256) {
    throw "The stick's boot image is not the automatic image ($hash). Rebuild it with: python scripts/make_stick.py --layout auto"
}
Write-Host 'Boot image: automatic unlock image, hash verified'

if (Test-Path $RecordPath) {
    throw "A boot entry is already recorded at $RecordPath. Remove it first with -Remove -Apply."
}

$order = Get-FirmwareOrder
Write-Host "Firmware boot order: $($order -join ', ')"

# ---------------------------------------------------------------- the entry
Step "create firmware entry '$Description' pointing at $EfiPath on $root"
Step 'put it first in the firmware boot order; Windows Boot Manager stays as the fallback'
if (-not $Apply) {
    Write-Host ''
    Write-Host 'Dry run. Re-run with -Apply to make these changes.'
    return
}

$out = & bcdedit /copy '{bootmgr}' /d $Description
$entry = [regex]::Match(($out -join ' '), '\{[0-9a-fA-F-]{36}\}').Value
if (-not $entry) { throw "bcdedit did not return an entry id: $out" }

$record = [ordered]@{
    entry       = $entry
    description = $Description
    volumeLabel = $VolumeLabel
    driveLetter = $vol.DriveLetter
    imageSha256 = $hash
    createdAt   = (Get-Date).ToString('o')
}
New-Item -ItemType Directory -Force $RecordDir | Out-Null
$record | ConvertTo-Json | Set-Content -Path $RecordPath -Encoding utf8

& bcdedit /set $entry path $EfiPath | Out-Null
if ($LASTEXITCODE) { throw 'bcdedit set path failed' }
& bcdedit /set $entry device "partition=$($vol.DriveLetter):" | Out-Null
if ($LASTEXITCODE) { throw 'bcdedit set device failed' }
& bcdedit /set '{fwbootmgr}' displayorder $entry /addfirst | Out-Null
if ($LASTEXITCODE) { throw 'bcdedit displayorder failed' }

# Read the result back instead of trusting exit codes.
$order = Get-FirmwareOrder
if ($order.Count -eq 0 -or $order[0] -ne $entry.ToLower()) {
    throw "The new entry $entry is not first in the firmware boot order: $($order -join ', ')"
}
if ((Get-EntryValue $entry 'path') -ne $EfiPath) { throw "The new entry does not point at $EfiPath" }

Write-Host "Firmware boot order: $($order -join ', ')"
Write-Host ''
Write-Host 'Done. Cold boot with the stick plugged in to unlock; remove it to boot Windows stock.'
Write-Host "Undo with: powershell -File scripts\usb_boot_entry.ps1 -Remove -Apply"
