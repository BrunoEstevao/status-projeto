# Acha o Python 3 (3.8+) que houver nesta máquina. Usado por hooks/tempo.sh e bin/status-projeto (bash: Linux,
# macOS e Git Bash no Windows). Ordem: python3, python, "py -3" e, se nenhum estiver no PATH, as pastas onde os
# instaladores costumam pôr (o terminal aberto antes da instalação ainda não vê o PATH novo).
# Resultado em SP_PY (array com o comando e os argumentos). Nada aqui precisa de Python.

SP_LOCAIS_PADRAO='$LOCALAPPDATA/Programs/Python/Python3*/python.exe|$PROGRAMFILES/Python3*/python.exe|/c/Program Files/Python3*/python.exe|/opt/homebrew/bin/python3|/usr/local/bin/python3|/usr/bin/python3'

sp_unix() {  # C:\Users\x → /c/Users/x (Git Bash); nos outros sistemas só troca a barra invertida
  if command -v cygpath >/dev/null 2>&1; then cygpath -u "$1" 2>/dev/null && return; fi
  printf '%s' "${1//\\//}"
}

sp_testa() {  # sp_testa CMD [ARGS] → 0 se for Python 3.8+ (o atalho da Microsoft Store e o Python 2 falham)
  "$@" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1 </dev/null
}

sp_locais() {  # uma linha por python.exe/python3 achado nas pastas conhecidas
  local lista="${STATUS_PROJETO_LOCAIS_PYTHON-$SP_LOCAIS_PADRAO}" padrao var val
  local IFS='|'
  for padrao in $lista; do
    [ -n "$padrao" ] || continue
    if [[ "$padrao" == \$* ]]; then          # $VAR/resto: VAR do Windows (com barra invertida)
      var="${padrao%%/*}"; var="${var#\$}"; val="${!var:-}"
      [ -n "$val" ] || continue
      padrao="$(sp_unix "$val")/${padrao#*/}"
    fi
    compgen -G "$padrao" | sort -r
  done
}

SP_RECUSADOS=()
sp_procurar() {  # procura sem usar o cache
  SP_PY=(); SP_RECUSADOS=()
  local cand
  for cand in python3 python "py -3"; do
    # shellcheck disable=SC2086
    set -- $cand
    command -v "$1" >/dev/null 2>&1 || continue
    if sp_testa "$@"; then SP_PY=("$@"); return 0; fi
    SP_RECUSADOS+=("$cand")
  done
  while IFS= read -r cand; do
    [ -n "$cand" ] && [ -x "$cand" ] || continue
    if sp_testa "$cand"; then SP_PY=("$cand"); return 0; fi
    SP_RECUSADOS+=("$cand")
  done < <(sp_locais)
  return 1
}

sp_cache() { [ -n "${HOME:-}" ] && printf '%s' "$HOME/.claude/status-projeto/python.txt"; }

sp_achar_python() {  # com cache (os hooks rodam a cada ferramenta): só confere se o comando guardado ainda existe
  local arq; arq="$(sp_cache)"
  if [ -n "$arq" ] && [ -f "$arq" ]; then
    SP_PY=(); local l
    while IFS= read -r l; do [ -n "$l" ] && SP_PY+=("$l"); done < "$arq"   # sem mapfile: o bash do macOS é o 3.2
    if [ "${#SP_PY[@]}" -gt 0 ] && command -v "${SP_PY[0]}" >/dev/null 2>&1; then return 0; fi
  fi
  sp_procurar || return 1
  if [ -n "$arq" ]; then
    mkdir -p "${arq%/*}" 2>/dev/null && printf '%s\n' "${SP_PY[@]}" > "$arq" 2>/dev/null
  fi
  return 0
}

sp_limpar_cache() { local arq; arq="$(sp_cache)"; [ -n "$arq" ] && rm -f "$arq"; }

# Saída em UTF-8 no Windows também (o console usa cp1252 e quebraria nos emojis e acentos).
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
