param(
    [Parameter(Mandatory = $true)]
    [string]$Pptx,
    [string]$OutputDir = "rendered\slides"
)

$ErrorActionPreference = "Stop"
$PptxPath = (Resolve-Path -LiteralPath $Pptx).Path
if ([System.IO.Path]::GetExtension($PptxPath).ToLowerInvariant() -ne ".pptx") {
    throw "Input must be a .pptx file"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$OutputPath = (Resolve-Path -LiteralPath $OutputDir).Path
Get-ChildItem -LiteralPath $OutputPath -Filter "slide_*.png" -File |
    Remove-Item -Force

$ppt = $null
$presentation = $null
try {
    $ppt = New-Object -ComObject PowerPoint.Application
    $presentation = $ppt.Presentations.Open($PptxPath, $true, $true, $false)

    $slideWidth = [double]$presentation.PageSetup.SlideWidth
    $slideHeight = [double]$presentation.PageSetup.SlideHeight
    if ($slideWidth -le 0 -or $slideHeight -le 0) {
        throw "PowerPoint returned invalid slide dimensions"
    }

    $ratio = $slideWidth / $slideHeight
    if ($ratio -ge 1.0) {
        $width = 1920
        $height = [int][Math]::Round($width / $ratio)
    }
    else {
        $height = 1080
        $width = [int][Math]::Round($height * $ratio)
    }

    $presentation.Export($OutputPath, "PNG", $width, $height)

    $files = Get-ChildItem -LiteralPath $OutputPath -File |
        Where-Object { $_.Name -match '^(?i)slide(\d+)\.png$' } |
        Sort-Object { [int]([regex]::Match($_.Name, '\d+').Value) }

    if ($files.Count -ne $presentation.Slides.Count) {
        throw "Exported $($files.Count) slide images, expected $($presentation.Slides.Count)"
    }

    $index = 1
    foreach ($file in $files) {
        $target = Join-Path $OutputPath ("slide_{0:D3}.png" -f $index)
        Move-Item -LiteralPath $file.FullName -Destination $target -Force
        $index++
    }

    Write-Host "Rendered $($files.Count) slides to $OutputPath ($($width)x$($height), source aspect ratio preserved)." -ForegroundColor Green
}
finally {
    if ($presentation -ne $null) {
        $presentation.Close()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($presentation)
    }
    if ($ppt -ne $null) {
        $ppt.Quit()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
