#!/usr/bin/env bash
# Hook de tempo: roda scripts/tempo_hook.py com o Python 3 que houver (python3, python ou py -3).
# Sem Python, sai em silêncio com código 0 (nada de "hook failed"); o /instalar-status oferece instalar.
aqui="${BASH_SOURCE[0]//\\//}"
case "$aqui" in */*) aqui="${aqui%/*}" ;; *) aqui=. ;; esac
raiz="$aqui/.."
. "$raiz/scripts/python.sh" 2>/dev/null || { cat >/dev/null 2>&1; exit 0; }
if sp_achar_python; then
  exec "${SP_PY[@]}" "$raiz/scripts/tempo_hook.py" "$@"
fi
cat >/dev/null 2>&1
exit 0
