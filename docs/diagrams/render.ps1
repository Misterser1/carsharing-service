# Рендер всех диаграмм в PNG и SVG через публичный сервис https://kroki.io (Windows PowerShell)
# Использование: powershell -ExecutionPolicy Bypass -File docs\diagrams\render.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Render($engine, $src, $out) {
    foreach ($fmt in @('png', 'svg')) {
        $body = [System.IO.File]::ReadAllBytes($src)
        Invoke-WebRequest -Uri "https://kroki.io/$engine/$fmt" -Method Post -ContentType 'text/plain' `
            -Body $body -OutFile "$out.$fmt" -UseBasicParsing | Out-Null
        Write-Host "OK   $src -> $out.$fmt"
    }
}

Render 'plantuml' 'c4-context.puml'    'c4-context'
Render 'plantuml' 'c4-container.puml'  'c4-container'
Render 'plantuml' 'use-cases.puml'     'use-cases'
Render 'mermaid'  'erd.mmd'            'erd'
Render 'mermaid'  'rental-flow.mmd'    'rental-flow'
Render 'mermaid'  'vehicle-states.mmd' 'vehicle-states'
Render 'mermaid'  'rental-states.mmd'  'rental-states'
