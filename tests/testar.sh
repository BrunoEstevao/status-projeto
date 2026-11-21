#!/usr/bin/env bash
# Teste do status-projeto sem LLM: instala duas vezes num repo vazio e num com histórico,
# simula os hooks e prova que nada duplicou. Uso: tests/testar.sh [pasta-temporária]
set -uo pipefail
PLUGIN="$(cd "$(dirname "$0")/.." && pwd)"
SP="python3 $PLUGIN/scripts/status_projeto.py"
HOOK="$PLUGIN/scripts/tempo_hook.py"
BASE="${1:-$(mktemp -d)}"
rm -rf "$BASE/vazio" "$BASE/historico"
mkdir -p "$BASE"
FALHAS=0
ok()  { echo "  ✅ $*"; }
nok() { echo "  ❌ $*"; FALHAS=$((FALHAS + 1)); }
checa() { if eval "$2"; then ok "$1"; else nok "$1"; fi; }
export GIT_CONFIG_GLOBAL=/dev/null GIT_AUTHOR_NAME="Pessoa Teste" GIT_AUTHOR_EMAIL=teste@exemplo.invalid \
       GIT_COMMITTER_NAME="Pessoa Teste" GIT_COMMITTER_EMAIL=teste@exemplo.invalid
unset CLAUDE_CODE_ENTRYPOINT STATUS_PROJETO_TIPO

instalar() {  # simula as etapas mecânicas do /instalar-status
  local d="$1"; shift
  ( cd "$d" &&
    $SP init --usuario "Pessoa Teste" --valor 150 --pasta-fatias fatias "$@" &&
    { [ -f STATUS.md ] && $SP status-md --marcar || $SP status-md --vazio --marcar; } &&
    $SP estimar && $SP claude-md && $SP hooks && $SP gitattributes &&
    $SP gitignore --corrigir && $SP guia --marcar > /dev/null ) 2>&1 | sed 's/^/    | /'
}
assinatura() {  # hash dos arquivos que a 2ª instalação não pode mudar
  ( cd "$1" && sha256sum STATUS.md docs/tempo/sessoes.csv docs/tempo/estimativa_git.csv CLAUDE.md .gitattributes \
      .gitignore 2>/dev/null; jq -S 'del(.atualizado_em)' .claude-status/config.json 2>/dev/null \
      || python3 -c "import json,sys;d=json.load(open('.claude-status/config.json'));d.pop('atualizado_em',None);print(json.dumps(d,sort_keys=True))" )
}
evento() {  # evento SESSAO NOME [prompt]
  local raiz="$1" sid="$2" ev="$3" pr="${4:-}"
  python3 - "$raiz" "$sid" "$ev" "$pr" <<'PY' | python3 "$HOOK" "$3"
import json, sys
raiz, sid, ev, pr = sys.argv[1:]
d = {"session_id": sid, "cwd": raiz, "hook_event_name": ev, "permission_mode": "default"}
if ev == "UserPromptSubmit":
    d["prompt"] = pr
print(json.dumps(d))
PY
}
contagens() {
  echo "blocos=$(grep -c 'status-projeto:inicio' "$1/CLAUDE.md") union=$(grep -c 'merge=union' "$1/.gitattributes") gi=$(grep -c '>>> status-projeto' "$1/.gitignore") fases=$(grep -c '^## ' "$1/STATUS.md")"
}

echo "== 1. Repo vazio (projeto novo)"
V="$BASE/vazio"; mkdir -p "$V"; git -C "$V" init -q -b main
instalar "$V"
A1="$(assinatura "$V")"; C1="$(contagens "$V")"
echo "  -- 2ª instalação (precisa não mudar nada):"
instalar "$V"
A2="$(assinatura "$V")"; C2="$(contagens "$V")"
checa "STATUS.md com as 5 fases" "[ \"\$(grep -c '^## [🌐📦🧪⏸✅]' $V/STATUS.md)\" = 5 ]"
checa "estimativa: sem histórico (nada a estimar)" "grep -q 'sem historico' $V/.claude-status/config.json"
checa "contagens iguais nas duas rodadas ($C2)" "[ \"$C1\" = \"$C2\" ] && [ \"$C2\" = 'blocos=1 union=1 gi=1 fases=5' ]"
checa "nenhum arquivo mudou na 2ª rodada" '[ "$A1" = "$A2" ]'
checa "instalação completa" "$SP --raiz $V reparar | grep -q 'Nada faltando'"

echo "== 2. Repo com histórico"
H="$BASE/historico"; mkdir -p "$H"; git -C "$H" init -q -b main
cd "$H"
mkdir -p fatias src
printf '# Meu app\n' > README.md
printf '# CLAUDE.md — meu app\n\nUse TypeScript estrito.\n' > CLAUDE.md
printf 'node_modules/\ndocs/*\n' > .gitignore   # esconde docs/ (como em muitos projetos)
printf '# TODO\n- [x] login\n- [ ] relatório\n- [ ] exportar\nSTATUS: em andamento\n' > TODO.md
c() { GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git commit -q --allow-empty -m "$2"; }
git add -A; c "2026-10-01T09:00:00" "chore: início"
printf '[M] login\n' > fatias/FATIA_LOGIN.md; git add -A; c "2026-10-01T09:40:00" "docs: FATIA_LOGIN"
echo a > src/a.ts; git add -A; c "2026-10-01T10:30:00" "feat(login): tela FATIA_LOGIN"
c "2026-10-01T11:45:00" "feat(login): validação"
c "2026-10-02T14:00:00" "fix(login): erro de senha"
printf '[P] relatório\n' > fatias/FATIA_RELATORIO.md; git add -A; c "2026-10-03T08:00:00" "docs: FATIA_RELATORIO"
c "2026-10-03T09:10:00" "feat(relatorio): primeira versão"
c "2026-10-03T10:00:00" "feat(relatorio): filtros"
c "2026-10-05T20:00:00" "chore: deps"
git checkout -q -b feat/exportar; c "2026-10-06T21:00:00" "feat(exportar): csv"; git checkout -q main
cd - > /dev/null
# STATUS.md como o Claude escreveria na análise (com datas do git e (?) no que não comprovou)
cat > "$H/STATUS.md" <<'EOF'
# STATUS — historico
Atualizado: 20/11/2026

## 🌐 Codando
- [P] FATIA_EXPORTAR — exportar CSV, na branch feat/exportar (desde 06/10)
  - Parei em: exportação CSV básica.
  - Próximo passo: exportar PDF (?).
  - Pendente: testes.

## 📦 Fatia pronta, não iniciada
- [M] `fatias/FATIA_PERFIL.md` — tela de perfil (desde ?)

## 🧪 Aguardando teste
- [P] `fatias/FATIA_RELATORIO.md` — relatório com filtros (desde 03/10)

## ⏸️ Bloqueado (externo)
(nada agora)

## ✅ Concluído
- [M] `fatias/FATIA_LOGIN.md` — login (desde 02/10)
EOF
echo "  status espalhado encontrado antes de mexer:"
$SP --raiz "$H" espalhado | sed 's/^/    | /'
echo "  -- 1ª instalação:"
instalar "$H"
B1="$(assinatura "$H")"; D1="$(contagens "$H")"
echo "  -- 2ª instalação (precisa não mudar nada):"
instalar "$H"
B2="$(assinatura "$H")"; D2="$(contagens "$H")"
checa "estimativa do git gravada" "[ \$(wc -l < $H/docs/tempo/estimativa_git.csv) -gt 1 ]"
checa "estimativa não refeita na 2ª rodada" "grep -q 'não é refeita' <<<\"\$(cd $H && $SP estimar)\""
checa "CLAUDE.md manteve o conteúdo original" "grep -q 'Use TypeScript estrito' $H/CLAUDE.md"
checa "contagens iguais nas duas rodadas ($D2)" "[ \"$D1\" = \"$D2\" ] && [ \"$D2\" = 'blocos=1 union=1 gi=1 fases=5' ]"
checa "nenhum arquivo mudou na 2ª rodada" '[ "$B1" = "$B2" ]'
checa "docs/tempo e o guia deixaram de ser ignorados" "! git -C $H check-ignore -q docs/tempo/sessoes.csv && ! git -C $H check-ignore -q docs/COMO_USAR_STATUS.md"
checa "trava e estado local ignorados" "git -C $H check-ignore -q docs/tempo/sessoes.csv.lock && git -C $H check-ignore -q .claude-status/local/estado.json"
checa "STATUS.md não foi sobrescrito" "grep -q 'FATIA_EXPORTAR' $H/STATUS.md"

echo "== 3. CLAUDE.md com regras antigas fora do bloco (não duplica)"
X="$BASE/antigo"; rm -rf "$X"; mkdir -p "$X"; git -C "$X" init -q -b main
printf '# CLAUDE.md\n\n## Regra de status\n- status no STATUS.md\n' > "$X/CLAUDE.md"
( cd "$X" && $SP init --usuario T --valor 150 > /dev/null && $SP claude-md > /dev/null 2>&1 ); rc=$?
checa "recusa gravar e pede decisão (código 3)" "[ $rc = 3 ] && ! grep -q 'status-projeto:inicio' $X/CLAUDE.md"

echo "== 4. Hooks (sessões simuladas no repo com histórico)"
S1="aaaaaaaa-0000-0000-0000-000000000001"
evento "$H" "$S1" SessionStart > /dev/null
evento "$H" "$S1" UserPromptSubmit "vou começar a codar FATIA_PERFIL com o segredo XYZ123" | sed 's/^/    | /'
evento "$H" "$S1" PostToolUse > /dev/null
evento "$H" "$S1" Stop > /dev/null
evento "$H" "$S1" UserPromptSubmit "vou testar FATIA_RELATORIO senha-super-secreta" | sed 's/^/    | /'
evento "$H" "$S1" UserPromptSubmit "outra coisa qualquer" | sed 's/^/    | /'
evento "$H" "$S1" UserPromptSubmit "mais uma" > "$BASE/saida_mais_uma.txt"
evento "$H" "$S1" UserPromptSubmit "terminei o teste" | sed 's/^/    | /'
evento "$H" "$S1" UserPromptSubmit "vou planejar a próxima fatia" > /dev/null
evento "$H" "$S1" SessionEnd > /dev/null
CSV="$H/docs/tempo/sessoes.csv"
echo "    sessoes.csv:"; sed 's/^/    | /' "$CSV"
checa "texto das mensagens nunca vai para o CSV" "! grep -qiE 'XYZ123|segredo|senha|qualquer|próxima' $CSV"
checa "linha interativa, de teste e de planejamento" "grep -q ',interativo,' $CSV && grep -q ',teste,' $CSV && grep -q ',planejamento,' $CSV"
checa "teste aberto é perguntado uma vez só" "[ ! -s $BASE/saida_mais_uma.txt ]"
checa "sessão fechada no SessionEnd" "! grep -q ',aberta$\\|,ocupada$' $CSV"
# Sessão esquecida: fim há 2 h, estado aberta → fecha no último evento quando outra sessão dá sinal
python3 - "$CSV" <<'PY'
import csv, sys
from datetime import datetime, timedelta
p = sys.argv[1]
l = list(csv.DictReader(open(p)))
t = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
l.append({"inicio": t, "fim": t, "repo": "historico", "fatia": "x", "tipo": "interativo", "sessao": "velha", "estado": "aberta"})
w = csv.DictWriter(open(p, "w", newline=""), fieldnames=l[0].keys()); w.writeheader(); w.writerows(l)
PY
evento "$H" "bbbbbbbb-0000-0000-0000-000000000002" SessionStart > /dev/null
checa "30 min sem evento fecha a sessão esquecida" "grep -q ',velha,fechada' $CSV"
# Teste esquecido + hora dita
evento "$H" "$S1" UserPromptSubmit "vou testar FATIA_RELATORIO" > /dev/null
python3 - "$CSV" <<'PY'
import csv, sys
from datetime import datetime, timedelta
p = sys.argv[1]
l = list(csv.DictReader(open(p)))
ini = (datetime.now() - timedelta(hours=26)).replace(minute=0, second=0)
for r in l:
    if r["tipo"] == "teste" and r["estado"] != "fechada":
        r["inicio"] = ini.strftime("%Y-%m-%d %H:%M:%S")
w = csv.DictWriter(open(p, "w", newline=""), fieldnames=l[0].keys()); w.writeheader(); w.writerows(l)
print(ini.strftime("%H"))
PY
H1=$(python3 -c "from datetime import datetime,timedelta;print(((datetime.now()-timedelta(hours=26)).replace(minute=0)+timedelta(hours=1)).strftime('%H:%M'))")
S3="cccccccc-0000-0000-0000-000000000003"
echo "    nova sessão com teste esquecido:"; evento "$H" "$S3" SessionStart | sed 's/^/    | /'
evento "$H" "$S3" UserPromptSubmit "terminei o teste às $H1" | sed 's/^/    | /'
checa "teste esquecido fechado na hora dita (1,0 h)" "evento $H x Stop >/dev/null; $SP --raiz $H relatorio | grep -q 'testando'"
evento "$H" "$S3" SessionEnd > /dev/null
# Merge=union duplicando a mesma linha: vale a de fim mais tarde
tail -1 "$CSV" | sed 's/,fechada$/,aberta/' >> "$CSV"
checa "linha repetida do merge=union não conta duas vezes" "[ \$(python3 -c \"import sys;sys.path.insert(0,'$PLUGIN/scripts');import comum;print(len(comum.ler_sessoes('$CSV')))\") = \$((\$(wc -l < $CSV) - 2)) ]"
# claude -p conta como autônomo
CLAUDE_CODE_ENTRYPOINT=sdk-cli evento "$H" "dddddddd-0000-0000-0000-000000000004" SessionStart > /dev/null
checa "claude -p registrado como autonomo" "grep -q ',autonomo,dddddddd' $CSV"
# repo sem config: hook não faz nada
evento "$BASE/antigo/.." "eeee" SessionStart > /dev/null
checa "repo sem instalação não ganha CSV" "[ ! -e $BASE/docs/tempo/sessoes.csv ]"

echo "== 5. Relatórios e comandos"
cd "$H"
for cmd in "relatorio" "historico" "cronograma" "resumo" "ajuda"; do
  if $SP $cmd > "$BASE/saida_$cmd.txt" 2>&1; then ok "$cmd roda"; else nok "$cmd falhou"; cat "$BASE/saida_$cmd.txt"; fi
done
$SP valor 180 --obs teste > /dev/null && ok "valor muda" || nok "valor"
checa "valor sem efeito retroativo (recusa data passada)" "! $SP valor 200 --desde 2026-01-01 2>/dev/null"
checa "estimativa mantém o valor antigo" "! grep -q ',180.00,' docs/tempo/estimativa_git.csv"
$SP verificar > "$BASE/saida_verificar.txt" 2>&1; ok "verificar roda (código $?; sem GitHub é esperado ❌)"
# Repo irmão (multi-repo)
$SP init --usuario X > /dev/null 2>&1
$SP repos --adicionar ../vazio > /dev/null
checa "relatorio --todos soma os repos" "$SP relatorio --todos | grep -q 'projeto com os repos'"
# Atualização de config antigo (sem campos novos)
python3 - <<'PY'
import json
p = ".claude-status/config.json"; d = json.load(open(p))
for k in ("repos", "ocioso_min", "horas_dia", "autonomo_processos"): d.pop(k, None)
d["versao_plugin"] = "0.9.0"; json.dump(d, open(p, "w"))
PY
$SP atualizar > /dev/null
checa "atualizar migra config antigo sem perder dados" "python3 -c \"import json;d=json.load(open('.claude-status/config.json'));assert d['ocioso_min']==30 and d['usuario']=='Pessoa Teste' and len(d['valor_hora'])==2\""
checa "atualizar não duplicou o bloco" "[ \$(grep -c 'status-projeto:inicio' CLAUDE.md) = 1 ]"
cd - > /dev/null

echo
echo "Saídas em $BASE (saida_*.txt). Falhas: $FALHAS"
exit $FALHAS
