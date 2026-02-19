param(
    [string]$DefsPath = "docs/diagrams/diagram_definitions.json",
    [string]$OutDir = "docs/diagrams"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing

function Get-Center($node) {
    return @{
        X = [double]$node.x + ([double]$node.w / 2.0)
        Y = [double]$node.y + ([double]$node.h / 2.0)
    }
}

function Draw-ArrowLine {
    param(
        [System.Drawing.Graphics]$G,
        [double]$x1,
        [double]$y1,
        [double]$x2,
        [double]$y2
    )
    $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(68,68,68), 2)
    $cap = New-Object System.Drawing.Drawing2D.AdjustableArrowCap(4, 6, $true)
    $pen.CustomEndCap = $cap
    $G.DrawLine($pen, [float]$x1, [float]$y1, [float]$x2, [float]$y2)
    $cap.Dispose()
    $pen.Dispose()
}

if (!(Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

$defs = Get-Content $DefsPath -Raw | ConvertFrom-Json

foreach ($diagram in $defs.diagrams) {
    $width = [int]$diagram.width
    $height = [int]$diagram.height
    $bmp = New-Object System.Drawing.Bitmap($width, $height)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.Clear([System.Drawing.Color]::White)

    $titleFont = New-Object System.Drawing.Font("Segoe UI", 20, [System.Drawing.FontStyle]::Bold)
    $nodeFont = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
    $edgeFont = New-Object System.Drawing.Font("Segoe UI", 9)
    $textBrush = [System.Drawing.Brushes]::Black
    $edgeBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(55,55,55))
    $borderPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(47,47,47), 1.2)

    $g.DrawString([string]$diagram.title, $titleFont, $textBrush, 30, 14)

    $nodeMap = @{}
    foreach ($node in $diagram.nodes) {
        $nodeMap[[string]$node.id] = $node
    }

    foreach ($edge in $diagram.edges) {
        $s = $nodeMap[[string]$edge.source]
        $t = $nodeMap[[string]$edge.target]
        $sc = Get-Center $s
        $tc = Get-Center $t
        Draw-ArrowLine -G $g -x1 $sc.X -y1 $sc.Y -x2 $tc.X -y2 $tc.Y

        if ($edge.PSObject.Properties.Name -contains "label" -and [string]$edge.label -ne "") {
            $mx = ($sc.X + $tc.X) / 2.0
            $my = (($sc.Y + $tc.Y) / 2.0) - 8.0
            $size = $g.MeasureString([string]$edge.label, $edgeFont)
            $g.FillRectangle([System.Drawing.Brushes]::White, [float]($mx - ($size.Width/2) - 2), [float]($my - $size.Height + 2), [float]($size.Width + 4), [float]($size.Height))
            $g.DrawString([string]$edge.label, $edgeFont, $edgeBrush, [float]($mx - ($size.Width/2)), [float]($my - $size.Height + 2))
        }
    }

    foreach ($node in $diagram.nodes) {
        $fillColor = [System.Drawing.ColorTranslator]::FromHtml([string]$node.fill)
        $fillBrush = New-Object System.Drawing.SolidBrush($fillColor)
        $rect = New-Object System.Drawing.RectangleF([float]$node.x, [float]$node.y, [float]$node.w, [float]$node.h)
        $g.FillRectangle($fillBrush, $rect)
        $g.DrawRectangle($borderPen, [float]$node.x, [float]$node.y, [float]$node.w, [float]$node.h)

        $sf = New-Object System.Drawing.StringFormat
        $sf.Alignment = [System.Drawing.StringAlignment]::Center
        $sf.LineAlignment = [System.Drawing.StringAlignment]::Center
        $g.DrawString([string]$node.label, $nodeFont, $textBrush, $rect, $sf)
        $sf.Dispose()
        $fillBrush.Dispose()
    }

    $outPath = Join-Path $OutDir "$($diagram.id).png"
    $bmp.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)

    $borderPen.Dispose()
    $titleFont.Dispose()
    $nodeFont.Dispose()
    $edgeFont.Dispose()
    $edgeBrush.Dispose()
    $g.Dispose()
    $bmp.Dispose()
}

Write-Output "Generated PNG files in $OutDir"
