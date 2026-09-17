#!/usr/bin/env bash
# Рендер всех диаграмм в PNG и SVG через публичный сервис https://kroki.io
# Использование: bash docs/diagrams/render.sh   (нужны curl и доступ в интернет)
set -euo pipefail
cd "$(dirname "$0")"

render() {   # render <engine> <source-file> <output-basename>
  local engine="$1" src="$2" out="$3"
  for fmt in png svg; do
    code=$(curl -sS -o "$out.$fmt" -w '%{http_code}' -X POST "https://kroki.io/$engine/$fmt" \
           -H 'Content-Type: text/plain' --data-binary "@$src")
    if [ "$code" != "200" ]; then
      echo "FAIL $src -> $out.$fmt (HTTP $code)"; cat "$out.$fmt"; echo; rm -f "$out.$fmt"; return 1
    fi
    echo "OK   $src -> $out.$fmt"
  done
}

render plantuml c4-context.puml     c4-context
render plantuml c4-container.puml   c4-container
render plantuml use-cases.puml      use-cases
render mermaid  erd.mmd             erd
render mermaid  rental-flow.mmd     rental-flow
render mermaid  vehicle-states.mmd  vehicle-states
render mermaid  rental-states.mmd   rental-states
