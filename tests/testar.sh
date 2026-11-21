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
    $SP gitignore --corrigir && $SP guia --gravar --marcar > /dev/null ) 2>&1 | sed 's/^/    | /'
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
git -C "$V" remote add origin git@github-zapai:Dono-Teste/vazio.git   # apelido SSH do ~/.ssh/config
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
checa "remote com apelido SSH vira Dono-Teste/vazio no guia" "grep -q 'Dono-Teste/vazio' $V/docs/COMO_USAR_STATUS.md && ! grep -q '<dono>' $V/docs/COMO_USAR_STATUS.md"

echo "== 2. Repo com histórico"
H="$BASE/historico"; mkdir -p "$H"; git -C "$H" init -q -b main
git -C "$H" remote add origin https://github.com/Dono-Teste/historico.git
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

echo "== 6. Remote: qualquer host antes dos dois-pontos; sem DONO/REPO, pergunta (nunca escreve <dono>)"
checa "formatos de URL do remote" "python3 -I - '$PLUGIN/scripts' <<'PY'
import sys; sys.path.insert(0, sys.argv[1]); import comum as c
casos = {'git@github-zapai:BrunoEstevao/zapai.git': 'BrunoEstevao/zapai', 'git@github.com:D/R.git': 'D/R',
         'github-x:D/R': 'D/R', 'https://github.com/D/R': 'D/R', 'https://u:t@github.com/D/R.git/': 'D/R',
         'ssh://git@github-x:22/D/R.git': 'D/R', '/srv/repo.git': '', 'host:sem-dono.git': '', '': ''}
ruins = {u: c.dono_repo_da_url(u) for u, e in casos.items() if c.dono_repo_da_url(u) != e}
print(ruins) if ruins else None; sys.exit(1 if ruins else 0)
PY"
R="$BASE/sem_remote"; rm -rf "$R"; mkdir -p "$R"; git -C "$R" init -q -b main
git -C "$R" remote add upstream git@github-zapai:Dono-Teste/sem_remote.git   # sem origin: usa o único remote
( cd "$R" && $SP init --usuario T --valor 150 > /dev/null )
checa "sem origin, usa o outro remote" "[ \"\$($SP --raiz $R github)\" = Dono-Teste/sem_remote ]"
git -C "$R" remote set-url upstream /srv/git/sem_remote.git
( cd "$R" && $SP guia --gravar --marcar > /dev/null 2>&1 ); rc=$?
checa "remote ilegível: guia sai com código 4 e não grava <dono>" "[ $rc = 4 ] && [ ! -e $R/docs/COMO_USAR_STATUS.md ]"
$SP --raiz "$R" github Dono-Teste/manual > /dev/null
( cd "$R" && $SP guia --gravar --marcar > /dev/null )
checa "DONO/REPO informado vai para o guia" "grep -q 'Dono-Teste/manual' $R/docs/COMO_USAR_STATUS.md && ! grep -q '<dono>' $R/docs/COMO_USAR_STATUS.md"
checa "formato inválido recusado" "! $SP --raiz $R github 'sem barra' 2>/dev/null"

echo "== 7. Contradições nas fatias em 📦"
F="$BASE/contradicoes"; rm -rf "$F"; mkdir -p "$F/fatias"; git -C "$F" init -q -b main
( cd "$F" && $SP init --usuario T --valor 150 > /dev/null )
cat > "$F/STATUS.md" <<'EOF'
## 🌐 Codando
## 📦 Fatia pronta, não iniciada
- [M] `fatias/FATIA_RUIM.md` — contradiz (desde ?)
- [P] FATIA_SOLTA — na raiz (desde ?)
- [P] FATIA_LIMPA — segue as regras (desde ?)
## 🧪 Aguardando teste
## ⏸️ Bloqueado (externo)
## ✅ Concluído
- [P] FATIA_VELHA — fora de 📦, não é conferida (desde 01/10)
EOF
cat > "$F/fatias/FATIA_RUIM.md" <<'EOF'
Gere o relatório em docs/relatorios/FATIA_RUIM_RELATORIO.md.
Depois mova esta fatia para docs/concluidas/.
Adicione docs/tempo/ ao .gitignore.
Marque como feito no TODO.md.
EOF
printf 'Ao terminar, apague esta fatia.\nNão commite o STATUS.md.\n' > "$F/FATIA_SOLTA.md"
cat > "$F/fatias/FATIA_LIMPA.md" <<'EOF'
Tela de relatório em src/pages/relatorio.tsx.
Crie o relatório em `fatias/RELATORIO_LIMPA.md` e ao concluir `git mv` para fatias_executadas/.
Coloque node_modules/ no .gitignore.
EOF
printf 'Depois apague esta fatia.\n' > "$F/fatias/FATIA_VELHA.md"
CT="$($SP --raiz "$F" contradicoes --json)"; ( $SP --raiz "$F" contradicoes > /dev/null ); rc=$?
tipos() { python3 -c "import json,sys;d=json.load(sys.stdin);print(' '.join(sorted(f\"{x['arquivo']}:{x['linha']}:{x['tipo']}\" for x in d['contradicoes'])))"; }
checa "acha as 6 contradições (arquivar, .gitignore, relatório, status)" "[ \"\$(tipos <<<\"\$CT\")\" = 'FATIA_SOLTA.md:1:arquivar FATIA_SOLTA.md:2:gitignore fatias/FATIA_RUIM.md:1:relatorio fatias/FATIA_RUIM.md:2:arquivar fatias/FATIA_RUIM.md:3:gitignore fatias/FATIA_RUIM.md:4:status' ]"
checa "fatia que segue as regras e fatia fora de 📦 não aparecem" "! grep -q 'LIMPA\|VELHA' <<<\"\$CT\""
checa "sai com código 3 e não altera as fatias" "[ $rc = 3 ] && grep -q 'apague' $F/FATIA_SOLTA.md"
printf 'Ao concluir, git mv para fatias_executadas/.\n' > "$F/FATIA_SOLTA.md"; printf 'ok\n' > "$F/fatias/FATIA_RUIM.md"
checa "depois de corrigidas, código 0" "$SP --raiz $F contradicoes > /dev/null"
cat > "$F/fatias/FATIA_LIMPA.md" <<'EOF'
Rode `git status`. Se houver QUALQUER
   alteração não commitada, **PARE, NÃO execute a fatia** e avise o T para ele commitar
Confira que o STATUS.md não está no .gitignore.
Tire docs/tempo/ do .gitignore se estiver lá.
EOF
checa "'alteração não commitada' e 'não está no .gitignore' não são contradição" "$SP --raiz $F contradicoes > /dev/null"
printf 'Não commite o STATUS.md.\n' > "$F/FATIA_SOLTA.md"
ID="$($SP --raiz $F contradicoes --json | python3 -c 'import json,sys;print(json.load(sys.stdin)["contradicoes"][0]["id"])')"
$SP --raiz "$F" contradicoes --ignorar "$ID" --obs "falso positivo" > /dev/null
checa "apontamento ignorado fica no config e não volta" "grep -q '\"$ID\"' $F/.claude-status/config.json && $SP --raiz $F contradicoes | grep -q '1 apontamento'"
printf '# título novo\nNão commite o STATUS.md.\n' > "$F/FATIA_SOLTA.md"
checa "ignorado continua ignorado se a linha só mudou de número" "$SP --raiz $F contradicoes > /dev/null"
$SP --raiz "$F" contradicoes --ignorar "$ID" > /dev/null
checa "ignorar de novo não duplica" "[ \$(grep -c '\"$ID\"' $F/.claude-status/config.json) = 1 ]"
$SP --raiz "$F" contradicoes --desfazer "$ID" > /dev/null
checa "--desfazer faz o apontamento voltar" "! $SP --raiz $F contradicoes > /dev/null"
checa "id inexistente é recusado" "! $SP --raiz $F contradicoes --ignorar ffffffff 2>/dev/null"

echo "== 8. Guia: cada fase uma vez só na tabela; instruções do claude.ai em bloco de código"
checa "guia impresso: nenhuma linha fora de bloco de código repete a fase" "python3 - $V/docs/COMO_USAR_STATUS.md <<'PY'
import sys
dentro, fora = False, []
for l in open(sys.argv[1], encoding='utf-8'):
    if l.strip().startswith('\`\`\`'):
        dentro = not dentro
        continue
    if not dentro:
        fora.append(l)
sys.exit(0 if sum('Aguardando teste' in l for l in fora) == 1 and not dentro else 1)
PY"
checa "instruções do claude.ai sem ' | ' (viravam linha de tabela)" "! grep -q ' | 🧪' $V/docs/COMO_USAR_STATUS.md"

echo "== 9. Comandos de consulta não gravam nada em disco"
foto() { ( cd "$H" && find . -path ./.git -prune -o -type f -print0 | sort -z | xargs -0 sha256sum ); }
velho() {  # guia apagado e config antigo: o que gravar sem pedir aparece na foto
  rm -f "$H/docs/COMO_USAR_STATUS.md"
  python3 - "$H/.claude-status/config.json" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
for k in ("repo_github", "contradicoes_ignoradas", "ocioso_min"): d.pop(k, None)
json.dump(d, open(p, "w"))
PY
}
for cmd in relatorio "relatorio --todos" historico cronograma resumo ajuda contradicoes "contradicoes --json" \
           "contradicoes --ignoradas" guia estado espalhado fatias-soltas github verificar reparar; do
  velho; F1="$(foto)"; $SP --raiz "$H" $cmd > /dev/null 2>&1; F2="$(foto)"
  checa "$cmd não grava" '[ "$F1" = "$F2" ]'
done
velho; ( cd "$H" && $SP guia --gravar > /dev/null )
checa "guia --gravar grava o arquivo" "[ -s $H/docs/COMO_USAR_STATUS.md ]"
checa "guia --marcar sem --gravar é recusado" "! $SP --raiz $H guia --marcar 2>/dev/null"

echo "== 10. STATUS.md com fases fora do padrão: Ajustar ao formato"
J="$BASE/ajustar"; rm -rf "$J"; mkdir -p "$J"; git -C "$J" init -q -b main
( cd "$J" && $SP init --usuario T --valor 150 > /dev/null )
cat > "$J/STATUS.md" <<'EOF'
# STATUS — ajustar
Atualizado: 20/11/2026

## 🔨 Em execução
- [M] FATIA_A — a (desde 01/11)
  - Parei em: x
  - Próximo passo: y
  - Pendente: z

## 📦 Fatia pronta, não iniciada
- [P] FATIA_B — b (desde 02/11)

## Feito
- [P] FATIA_C — c (desde 03/10)

## ✅ Concluído
- [P] FATIA_D — d (desde 01/10)

## Notas
texto livre
EOF
EXTRAS="$($SP --raiz $J estado | python3 -c "import json,sys;print(' '.join(f\"{x['titulo']}={x['sugestao']}\" for x in json.load(sys.stdin)['status_md']['fases_extras']))")"
checa "estado aponta as fases fora do padrão com a fase sugerida ($EXTRAS)" "[ \"$EXTRAS\" = '🔨 Em execução=🌐 Feito=✅' ]"
checa "seção fora do padrão: hook não enxerga a fatia antes do ajuste" "python3 -c \"import sys;sys.path.insert(0,'$PLUGIN/scripts');import comum as c;f,_=c.ler_status_arquivo('$J');sys.exit(len(f['🌐']))\""
$SP --raiz "$J" status-md --ajustar "🔨 Em execução=🌐" --ajustar "Feito=✅" --marcar > /dev/null
checa "ajustado: 5 fases na ordem, Notas mantida" "[ \"\$(grep '^## ' $J/STATUS.md | tr '\n' '|')\" = '## 🌐 Codando|## 📦 Fatia pronta, não iniciada|## 🧪 Aguardando teste|## ⏸️ Bloqueado (externo)|## ✅ Concluído|## Notas|' ]"
checa "nenhum item perdido, subitens mantidos" "for x in FATIA_A FATIA_B FATIA_C FATIA_D 'Parei em: x' 'texto livre'; do grep -q \"\$x\" $J/STATUS.md || exit 1; done"
checa "fatia em 🌐 depois do ajuste e itens de Feito juntos em ✅" "python3 -c \"import sys;sys.path.insert(0,'$PLUGIN/scripts');import comum as c;f,_=c.ler_status_arquivo('$J');assert [i['nome'] for i in f['🌐']]==['FATIA_A'] and [i['nome'] for i in f['✅']]==['FATIA_C','FATIA_D']\""
A1="$(sha256sum < $J/STATUS.md)"; $SP --raiz "$J" status-md --marcar > /dev/null
checa "ajustar não sobra nada fora do padrão; rodar de novo não muda" "[ \"\$(sha256sum < $J/STATUS.md)\" = \"$A1\" ] && $SP --raiz $J estado | grep -q '\"fases_extras\": \[\]'"
checa "título inexistente é recusado" "! $SP --raiz $J status-md --ajustar 'Nada=🌐' 2>/dev/null"
checa "guia e README sem '/plugin update' como comando de atualizar" "! grep -q '^/plugin update' $PLUGIN/README.md $V/docs/COMO_USAR_STATUS.md && grep -q 'claude plugin update status-projeto@status-projeto' $V/docs/COMO_USAR_STATUS.md"

echo "== 11. Status espalhado e fatias fora da pasta: também fora do git e ignorados"
K="$BASE/soltas"; rm -rf "$K"; mkdir -p "$K/fatias" "$K/docs" "$K/node_modules/pacote"; git -C "$K" init -q -b main
( cd "$K" && $SP init --usuario T --valor 150 > /dev/null )
printf '## 🌐 Codando\n## 📦 Fatia pronta, não iniciada\n- [P] `fatias/FATIA_DENTRO.md` — ok (desde ?)\n## 🧪 Aguardando teste\n- [M] FATIA_CITADA — na raiz (desde ?)\n## ⏸️ Bloqueado (externo)\n## ✅ Concluído\n' > "$K/STATUS.md"
echo x > "$K/fatias/FATIA_DENTRO.md"; echo x > "$K/FATIA_CITADA.md"; echo x > "$K/README.md"
echo "# metodologia" > "$K/metodologia.md"; echo "# todo" > "$K/node_modules/pacote/TODO.md"
git -C "$K" add -A; git -C "$K" commit -q -m "inicio"
echo x > "$K/FATIA_V3_API_2_CARTAO.md"                       # fora do git
echo "- [ ] a" > "$K/MINERADOR-STATUS.md"                    # fora do git, STATUS no fim do nome
echo "- [ ] a" > "$K/ESTADO_ATUAL.md"; echo "ESTADO_ATUAL.md" >> "$K/.git/info/exclude"   # ignorado
echo "x" > "$K/docs/V3-ANDAMENTO.md"
for n in 1 2 3; do echo x > "$K/docs/2026-11-0${n}_FATIA_N$n.md"; done   # pasta-arquivo de fatias antigas

ESP="$($SP --raiz $K espalhado)"
checa "espalhado acha ESTADO_ATUAL (ignorado) e MINERADOR-STATUS (fora do git)" "grep -q 'ESTADO_ATUAL.md \[ignorado\]' <<<\"\$ESP\" && grep -q 'MINERADOR-STATUS.md \[fora do git\]' <<<\"\$ESP\""
checa "espalhado acha ANDAMENTO no nome e não confunde metodologia com TODO" "grep -q 'docs/V3-ANDAMENTO.md' <<<\"\$ESP\" && ! grep -q 'metodologia' <<<\"\$ESP\""
checa "espalhado não entra em node_modules" "! grep -q node_modules <<<\"\$ESP\""
SOL="$($SP --raiz $K fatias-soltas --json)"
sol() { python3 -c "import json,sys;d={x['arquivo']:x for x in json.load(sys.stdin)};print(' '.join(f\"{k}:{v['situacao']}:{int(v['citada_no_status'])}:{v['grupo']}\" for k,v in sorted(d.items())))" <<<"$SOL"; }
checa "fatias-soltas: raiz fora do git, citada no STATUS, docs/ em grupo, fatias/ fora ($(sol))" "[ \"\$(sol)\" = 'FATIA_CITADA.md:versionado:1: FATIA_V3_API_2_CARTAO.md:fora do git:0: docs/2026-11-01_FATIA_N1.md:fora do git:0:docs docs/2026-11-02_FATIA_N2.md:fora do git:0:docs docs/2026-11-03_FATIA_N3.md:fora do git:0:docs' ]"
checa "estado traz fatias_fora_da_pasta" "$SP --raiz $K estado | grep -q 'FATIA_V3_API_2_CARTAO'"
checa "CLAUDE.md não conta como status espalhado por causa do bloco do plugin" "! $SP --raiz $V espalhado | grep -q '^- CLAUDE.md'"

echo "== 12. Projeto que já tem taxa.csv e estimativa_git.csv: aproveita sem mexer"
Z="$BASE/dados"; rm -rf "$Z"; mkdir -p "$Z/docs/tempo"; git -C "$Z" init -q -b main
( cd "$Z" && git commit -q --allow-empty -m "início" )
printf 'vigente_desde,valor_hora,observacao\n2026-10-01,150.00,valor inicial\n' > "$Z/docs/tempo/taxa.csv"
printf 'data,inicio,fim,horas,fatia,tipo,commits,repo,valor_hora,custo\n2026-10-24,2026-10-24 20:17,2026-10-25 02:46,6.47,f06,interativo,37,dados,150.00,971.21\n' > "$Z/docs/tempo/estimativa_git.csv"
H_TX="$(sha256sum < $Z/docs/tempo/taxa.csv)"; H_EST="$(sha256sum < $Z/docs/tempo/estimativa_git.csv)"
checa "estado mostra taxa.csv (R\$ 150) e a estimativa existente" "$SP --raiz $Z estado | python3 -c \"import json,sys;d=json.load(sys.stdin)['dados_existentes'];assert d['taxa_csv']['valor_atual']==150 and d['estimativa_git']['sessoes']==1\""
( cd "$Z" && $SP init --usuario T --valor 100 > /dev/null 2>&1 ); rc=$?
checa "valor diferente sem --valor-desde: recusa (código 3) e não cria config" "[ $rc = 3 ] && [ ! -e $Z/.claude-status/config.json ] && [ \"\$(sha256sum < $Z/docs/tempo/taxa.csv)\" = \"$H_TX\" ]"
checa "--valor-desde antes da última linha é recusado" "! ( cd $Z && $SP init --usuario T --valor 100 --valor-desde 2026-09-01 ) 2>/dev/null"
( cd "$Z" && $SP init --usuario T --valor 100 --valor-desde 2026-11-21 > /dev/null )
checa "linha nova no fim do taxa.csv, antigas intactas" "[ \"\$(head -2 $Z/docs/tempo/taxa.csv | sha256sum)\" = \"$H_TX\" ] && tail -1 $Z/docs/tempo/taxa.csv | grep -q '^2026-11-21,100.00,'"
checa "config usa o histórico do taxa.csv" "python3 -c \"import sys;sys.path.insert(0,'$PLUGIN/scripts');import comum as c;v=[x['valor'] for x in c.ler_config('$Z')['valor_hora']];assert v==[150.0,100.0],v\""
( cd "$Z" && $SP estimar > /dev/null && $SP status-md --vazio --marcar > /dev/null )
checa "estimativa existente não foi recalculada nem mexida" "[ \"\$(sha256sum < $Z/docs/tempo/estimativa_git.csv)\" = \"$H_EST\" ]"
$SP --raiz "$Z" valor 120 --obs teste > /dev/null
checa "/status-valor acrescenta no taxa.csv sem tocar nas antigas" "[ \$(wc -l < $Z/docs/tempo/taxa.csv) = 4 ] && [ \"\$(head -2 $Z/docs/tempo/taxa.csv | sha256sum)\" = \"$H_TX\" ]"
Y="$BASE/dados2"; rm -rf "$Y"; mkdir -p "$Y/docs/tempo"; git -C "$Y" init -q -b main
printf 'vigente_desde,valor_hora,observacao\n2026-10-01,150.00,x\n' > "$Y/docs/tempo/taxa.csv"; HY="$(sha256sum < $Y/docs/tempo/taxa.csv)"
( cd "$Y" && $SP init --usuario T > /dev/null )
checa "init sem --valor aproveita o taxa.csv sem mexer" "[ \"\$(sha256sum < $Y/docs/tempo/taxa.csv)\" = \"$HY\" ] && grep -q '\"valor\": 150.0' $Y/.claude-status/config.json"

echo
echo "Saídas em $BASE (saida_*.txt). Falhas: $FALHAS"
exit $FALHAS
