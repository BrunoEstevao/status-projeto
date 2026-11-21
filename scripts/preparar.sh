# Comandos do instalador que precisam funcionar SEM Python (bash puro), carregados por bin/status-projeto:
#   status-projeto preparar          JSON: sistema, Python, como instalar, git; código 0 se está tudo pronto, 5 se não
#   status-projeto git-init          git init na pasta atual (recusa a pasta pessoal)
#   status-projeto instalar-python   instala o Python 3 pelo gerenciador do sistema (winget, apt, dnf, pacman, brew)
# Códigos: 0 ok · 3 recusado · 4 sem gerenciador ou a instalação falhou (mostra o passo a passo) · 5 falta algo
#          · 6 precisa de senha (o usuário roda o comando) · 7 instalou, mas este terminal ainda não vê o Python

sp_json() {  # texto → "texto" em JSON
  local s="$1"
  s="${s//\\/\\\\}"; s="${s//\"/\\\"}"; s="${s//$'\t'/\\t}"; s="${s//$'\r'/}"; s="${s//$'\n'/\\n}"
  printf '"%s"' "$s"
}

sp_sistema() {
  if [ -n "${STATUS_PROJETO_SISTEMA:-}" ]; then echo "$STATUS_PROJETO_SISTEMA"; return; fi
  case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*|CYGWIN*) echo windows ;;
    Darwin) echo macos ;;
    *) if [ "${OS:-}" = "Windows_NT" ]; then echo windows; else echo linux; fi ;;
  esac
}

SP_GER=""; SP_CMD=""; SP_SUDO=0
sp_gerenciador() {  # preenche SP_GER (winget|apt|dnf|pacman|brew|nenhum), SP_CMD e SP_SUDO
  local sudo=""
  [ "$(id -u 2>/dev/null || echo 1)" = 0 ] || sudo="sudo "
  SP_GER=nenhum; SP_CMD=""; SP_SUDO=0
  case "$(sp_sistema)" in
    windows)
      if command -v winget >/dev/null 2>&1 || command -v winget.exe >/dev/null 2>&1; then
        SP_GER=winget
        SP_CMD='winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements --override "/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1"'
      fi ;;
    macos)
      if command -v brew >/dev/null 2>&1; then SP_GER=brew; SP_CMD="brew install python"; fi ;;
    *)
      if command -v apt-get >/dev/null 2>&1; then SP_GER=apt; SP_CMD="${sudo}apt-get install -y python3"
      elif command -v dnf >/dev/null 2>&1; then SP_GER=dnf; SP_CMD="${sudo}dnf install -y python3"
      elif command -v pacman >/dev/null 2>&1; then SP_GER=pacman; SP_CMD="${sudo}pacman -S --noconfirm python"
      fi
      [ -n "$sudo" ] && [ -n "$SP_CMD" ] && SP_SUDO=1 ;;
  esac
}

sp_passo_a_passo() {
  case "$(sp_sistema)" in
    windows) cat <<'TXT'
Instalar o Python 3 no Windows, à mão:
  1. Abra https://www.python.org/downloads/ e baixe o instalador do Python 3 (botão "Download Python 3.x").
  2. Rode o instalador. Na PRIMEIRA tela, marque "Add python.exe to PATH" (fica embaixo, desmarcado por padrão).
  3. Clique em "Install Now" e espere terminar.
  4. Feche o Claude Code e o terminal (todas as janelas) e abra de novo, para o PATH novo valer.
  5. Rode /instalar-status de novo: ele continua de onde parou.
Se já tinha instalado sem marcar o PATH: rode o instalador de novo, escolha "Modify" → "Next" e marque
"Add Python to environment variables".
TXT
    ;;
    macos) cat <<'TXT'
Instalar o Python 3 no macOS, à mão:
  1. Abra https://www.python.org/downloads/macos/ e baixe o instalador (.pkg) do Python 3.
  2. Rode o instalador até o fim (ele já põe o python3 no PATH).
     Outra forma: no Terminal, "xcode-select --install" instala as ferramentas de linha de comando com o python3.
  3. Feche e abra o terminal e o Claude Code, e rode /instalar-status de novo: ele continua de onde parou.
TXT
    ;;
    *) cat <<'TXT'
Instalar o Python 3 no Linux, à mão (no terminal, com a sua senha):
  Debian/Ubuntu: sudo apt-get install -y python3
  Fedora:        sudo dnf install -y python3
  Arch:          sudo pacman -S python
Depois rode /instalar-status de novo: ele continua de onde parou.
TXT
    ;;
  esac
}

sp_marca() { [ -n "${HOME:-}" ] && printf '%s' "$HOME/.claude/status-projeto/python-pendente.txt"; }

sp_mesma_pasta() {  # no Windows, maiúsculas e minúsculas são a mesma pasta
  if [ "$(sp_sistema)" = windows ]; then
    [ "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" = "$(printf '%s' "$2" | tr '[:upper:]' '[:lower:]')" ]
  else
    [ "$1" = "$2" ]
  fi
}

SP_GIT=""; SP_GIT_PASTA=""; SP_GIT_SAFE=""
sp_git() {  # SP_GIT: ok | sem_repo | pasta_pessoal | dono_diferente | sem_git
  local aqui casa top err
  aqui="$(pwd -P)"; casa="$(cd "${HOME:-/nao-existe}" 2>/dev/null && pwd -P)"
  SP_GIT_PASTA="$aqui"; SP_GIT_SAFE=""
  if ! command -v git >/dev/null 2>&1; then SP_GIT=sem_git; return; fi
  err="$(git rev-parse --show-toplevel 2>&1 >/dev/null)"
  if top="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    SP_GIT_PASTA="$top"
    top="$(cd "$top" 2>/dev/null && pwd -P)"
    if [ -n "$casa" ] && sp_mesma_pasta "$top" "$casa"; then SP_GIT=pasta_pessoal; else SP_GIT=ok; fi
  elif printf '%s' "$err" | grep -qi "dubious ownership\|safe.directory"; then
    # pasta de rede (ou de outro usuário): o git recusa até alguém marcar a pasta como segura
    SP_GIT=dono_diferente
    # o próprio git mostra o comando certo (no Windows, pasta de rede vira '%(prefix)///servidor/pasta')
    SP_GIT_SAFE="$(printf '%s\n' "$err" | grep -m1 'safe.directory' | grep 'git config' | sed 's/^[[:space:]]*//')"
    if [ -z "$SP_GIT_SAFE" ]; then
      local alvo; alvo="$(printf '%s' "$err" | sed -n "s/.*repository at '\(.*\)'.*/\1/p" | head -1)"
      SP_GIT_SAFE="git config --global --add safe.directory '${alvo:-$aqui}'"
    fi
  elif [ -n "$casa" ] && sp_mesma_pasta "$aqui" "$casa"; then
    SP_GIT=pasta_pessoal
  else
    SP_GIT=sem_repo
  fi
}

sp_cmd_preparar() {
  local py_ok=false py_cmd="" py_ver="" continuando=false pendente=null marca rec="" r
  marca="$(sp_marca)"
  sp_limpar_cache
  if sp_achar_python; then
    py_ok=true; py_cmd="${SP_PY[*]}"
    py_ver="$("${SP_PY[@]}" -c 'import platform; print(platform.python_version())' 2>/dev/null)"
    if [ -n "$marca" ] && [ -f "$marca" ]; then continuando=true; rm -f "$marca"; fi
  elif [ -n "$marca" ] && [ -f "$marca" ]; then
    pendente="{\"desde\": $(sp_json "$(head -1 "$marca")"), \"comando\": $(sp_json "$(sed -n 2p "$marca")")}"
  fi
  for r in "${SP_RECUSADOS[@]}"; do rec="${rec:+$rec, }$(sp_json "$r")"; done
  sp_gerenciador; sp_git
  local pronto=false
  [ "$py_ok" = true ] && [ "$SP_GIT" = ok ] && pronto=true
  cat <<JSON
{
  "pronto": $pronto,
  "sistema": $(sp_json "$(sp_sistema)"),
  "python": {"ok": $py_ok, "comando": $(sp_json "$py_cmd"), "versao": $(sp_json "$py_ver"), "recusados": [$rec]},
  "instalar_python": {"gerenciador": $(sp_json "$SP_GER"), "comando": $(sp_json "$SP_CMD"), "usa_sudo": $([ "$SP_SUDO" = 1 ] && echo true || echo false)},
  "python_pendente": $pendente,
  "continuando": $continuando,
  "git": {"situacao": $(sp_json "$SP_GIT"), "pasta": $(sp_json "$SP_GIT_PASTA"), "comando_safe_directory": $(sp_json "$SP_GIT_SAFE")}
}
JSON
  [ "$pronto" = true ] || return 5
}

sp_cmd_git_init() {
  sp_git
  case "$SP_GIT" in
    ok) echo "Esta pasta já é um repositório git ($SP_GIT_PASTA). Nada a fazer."; return 0 ;;
    pasta_pessoal) echo "Recusado: esta é a sua pasta pessoal ($SP_GIT_PASTA). Abra o Claude Code na pasta do projeto e rode /instalar-status lá." >&2; return 3 ;;
    sem_git) echo "O git não está instalado. Instale o git (no Windows, o Git for Windows, que traz o Git Bash) e rode de novo." >&2; return 4 ;;
    dono_diferente) echo "O git recusa esta pasta (dono diferente, comum em pasta de rede). Rode antes: $SP_GIT_SAFE" >&2; return 3 ;;
  esac
  git init && echo "Repositório git criado em $(pwd -P)."
}

sp_cmd_instalar_python() {
  sp_limpar_cache
  if sp_procurar; then echo "O Python já responde: ${SP_PY[*]}. Nada a instalar."; sp_achar_python; return 0; fi
  sp_gerenciador
  if [ "$SP_GER" = nenhum ]; then
    echo "Não achei gerenciador de pacotes para instalar sozinho."; echo; sp_passo_a_passo; return 4
  fi
  if [ "$SP_SUDO" = 1 ] && ! sudo -n true >/dev/null 2>&1; then
    echo "Este comando pede a sua senha, e eu não consigo digitá-la. Rode você mesmo no prompt (com o ! na frente):"
    echo "  ! $SP_CMD"
    echo "Depois rode /instalar-status de novo."
    return 6
  fi
  echo "Rodando: $SP_CMD"
  if ! eval "$SP_CMD"; then
    echo; echo "A instalação falhou."; echo; sp_passo_a_passo; return 4
  fi
  sp_limpar_cache
  if sp_achar_python; then
    echo; echo "Python pronto nesta sessão: ${SP_PY[*]} ($("${SP_PY[@]}" -c 'import platform; print(platform.python_version())' 2>/dev/null))."
    return 0
  fi
  local marca; marca="$(sp_marca)"
  if [ -n "$marca" ]; then
    mkdir -p "${marca%/*}" 2>/dev/null && printf '%s\n%s\n' "$(date '+%Y-%m-%d %H:%M')" "$SP_CMD" > "$marca"
  fi
  echo
  echo "Instalado, mas este terminal ainda não enxerga o Python (o PATH novo só vale em terminal novo)."
  echo "Feche o Claude Code (e o terminal), abra de novo nesta pasta e rode /instalar-status: ele continua de onde parou."
  return 7
}
