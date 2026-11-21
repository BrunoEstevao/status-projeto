---
name: instalar-status
description: Instala (ou verifica, repara e atualiza) o status-projeto neste repositório — STATUS.md com 5 fases, regras no CLAUDE.md, medição de tempo por hooks, estimativa de horas pelo git e guia de uso.
argument-hint: "[usuario=Nome valor=150 pasta=fatias] [verificar|reparar|atualizar|sair]"
disable-model-invocation: true
allowed-tools: Bash(status-projeto *) Bash(git log *) Bash(git status *) Bash(git ls-files *) Bash(git branch *) Bash(git tag *) Bash(git show *) Bash(git diff *) Read Glob Grep Write Edit AskUserQuestion
---

# /instalar-status

Você vai instalar o status-projeto no repositório atual. Fale em português, curto. O programa auxiliar é
`status-projeto` (está no PATH; se não estiver, use `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status_projeto.py"`).
Argumentos recebidos: `$ARGUMENTS` (podem trazer `usuario=`, `valor=`, `pasta=`; o que vier não precisa ser perguntado).

## Regras que nunca quebram
- **Nunca** reinstale por cima: se já houver instalação, siga o passo 1.
- **Nunca** sobrescreva `STATUS.md` nem `docs/tempo/sessoes.csv`. **Nunca** refaça a estimativa do git
  (`status-projeto estimar` já se recusa). **Nunca** duplique as regras no `CLAUDE.md` (o bloco fica entre marcas).
- **Nunca** faça commit nem push sem o usuário escrever **"pode commitar"**.
- Não leia nem copie segredos (`.env`, chaves). O que não der para comprovar pelo código/git: `(?)`.

## Passo 0 — diagnóstico
Rode `status-projeto estado` e leia o JSON (instalado, etapas_feitas, etapas_pendentes, precisa_atualizar, git,
projeto_novo, status_md, claude_md, pastas_fatias_detectadas, fatias_soltas_na_raiz, hooks_manuais_antigos).
Se `git.repo_git` for false, avise que precisa ser um repositório git (sugira `git init`) e pare.

## Passo 1 — já instalado?
- `instalacao_completa: true` → **não reinstale.** Se os argumentos trouxerem `sair`, `verificar`, `reparar` ou
  `atualizar`, use essa escolha sem perguntar. Senão, pergunte (AskUserQuestion) o que fazer:
  **Sair** · **Verificar** (rode o /verificar-integracao: `status-projeto verificar`) · **Reparar** (só o que falta) ·
  **Atualizar** (se `precisa_atualizar`, recomende esta).
  - Reparar: `status-projeto reparar` lista o que falta ou quebrou; refaça **só esses itens** seguindo o passo
    correspondente abaixo. Nunca recrie STATUS.md por cima; se ele sumiu, ofereça restaurar do git.
  - Atualizar: `status-projeto atualizar` (migra o config, regrava só o bloco do CLAUDE.md e o guia), depois
    `status-projeto reparar` e trate o que aparecer. Mostre o que mudou do CHANGELOG do plugin
    (`${CLAUDE_PLUGIN_ROOT}/CHANGELOG.md`) entre `versao_plugin_instalada` e `versao_plugin`.
    Rode também o passo 3b (contradições nas fatias em 📦).
- `instalado: true` mas incompleto → diga "a instalação anterior parou; continuo de onde parou" e faça **só as etapas
  de `etapas_pendentes`**, na ordem abaixo. Não pergunte de novo o que já está no config.
- `instalado: false` → instalação nova, a partir do passo 2.

## Passo 2 — perguntas (só na primeira vez)
Uma AskUserQuestion com até 3 perguntas (pule as que vieram nos argumentos):
1. **Nome do usuário** (como as regras vão chamar a pessoa que testa e decide). Sugira o `git config user.name`.
2. **Valor da hora** — padrão **150** (R$). Opções: 150 (Recomendado), 100, 200.
3. **Pasta das fatias** — se `pastas_fatias_detectadas` não estiver vazia, a primeira detectada é a recomendada;
   senão, `fatias`. A pasta das concluídas é `<pasta>_executadas` (ou a existente, ex.: `fatias_executadas`).
Se `git.autores` mostrar mais de uma pessoa, pergunte também se a estimativa conta só os commits do usuário
(`--autor "Nome"`) ou todos. Se o usuário citar repos irmãos do mesmo projeto, use `--repo ../outro` (pode repetir).
Depois: `status-projeto init --usuario "<nome>" --valor <valor> --pasta-fatias <pasta> [--pasta-executadas X] [--autor A] [--repo ../R]`.

## Passo 3 — etapa `status_md`
**Antes de mexer em qualquer coisa**, rode `status-projeto espalhado` e mostre a lista de arquivos com status
espalhado (TODO, PROGRESSO, checklists, "concluído"...). Não apague nada: só informe que, pela regra, o status passa
a morar só no STATUS.md, e pergunte se quer que você tire o status desses arquivos depois (não faça agora sem ordem).

- **Projeto novo** (`projeto_novo: true`): `status-projeto status-md --vazio --marcar`.
- **STATUS.md já existe**: não sobrescreva. Se `status_md.fases_faltando` não estiver vazio, mostre e pergunte se pode
  acrescentar só as fases que faltam (`status-projeto status-md --completar-fases --marcar`). Se já tiver as 5,
  `status-projeto status-md --marcar`.
- **Projeto existente sem STATUS.md**: analise o código e o git e **escreva o STATUS.md** no formato do template
  (`${CLAUDE_PLUGIN_ROOT}/templates/STATUS.md`):
  - Fontes: `git log --all --date=short --format='%ad %h %s'` (e `--stat` onde precisar), branches e tags, arquivos
    da pasta de fatias (e fatias soltas na raiz), relatórios, README/CHANGELOG/TODO e o próprio código (o que existe
    de verdade, o que está pela metade, testes).
  - Cada item com `(desde DD/MM)` tirado do git (data do commit que o colocou na fase: criação da fatia → 📦; último
    commit da fatia sem conclusão → 🌐; relatório/commit de conclusão → ✅). Sem como comprovar: `(desde ?)`.
    Fato incerto: acrescente `(?)`.
  - 🌐 com `Parei em:` / `Próximo passo:` / `Pendente:` (no máximo 3). 📦 com `[P]/[M]/[G]` (use as horas da
    estimativa do passo 4 quando houver; senão o tamanho do escopo) e na ordem de execução provável. ⏸️ com motivo.
  - Formato de cada item (uma linha, tamanho no começo, data no fim; detalhes em subitens):
    `- [M] FATIA_NOME — o que é (desde 05/10)` ou `` - [P] `fatias/FATIA_NOME.md` — o que é (desde ?) ``.
  - Mostre o STATUS.md ao usuário e grave. Depois `status-projeto status-md --marcar` (ele mostra avisos de formato:
    corrija o que for seu).

## Passo 3b — contradições nas fatias em 📦 (projeto existente; também no Atualizar)
Pule em projeto novo. Com o STATUS.md já gravado, rode `status-projeto contradicoes`. Ele lê o arquivo de cada fatia em
📦 e aponta linhas que contradizem as regras do plugin: **onde arquivar** (a fatia e o relatório vão com `git mv` para a
pasta das executadas, nunca apagados nem para outra pasta), **.gitignore** (STATUS.md, CLAUDE.md, `docs/tempo/`, o
guia, o config e as pastas de fatias vão para o git), **onde gerar o relatório** (junto da fatia, na pasta das fatias)
e **status fora do STATUS.md** (TODO.md, PROGRESSO.md...).
- Código 0 → diga em uma linha que nenhuma fatia contradiz as regras (e cite as `sem arquivo`, se houver).
- Código 3 → mostre a lista **inteira** (arquivo:linha, trecho, regra, correção). A detecção é por padrão de texto:
  leia cada trecho no contexto da fatia e descarte (dizendo que descartou) o que não for instrução de verdade.
  Pergunte (AskUserQuestion): **Corrigir todas** · **Escolher quais** · **Marcar como ignorado (falso positivo)** ·
  **Não corrigir agora**. Falso positivo (seu ou do usuário) → `status-projeto contradicoes --ignorar ID --obs "motivo"`
  (o id aparece no começo de cada apontamento; fica em `contradicoes_ignoradas` no config e não volta nas próximas
  rodadas, enquanto o texto da linha não mudar). `--ignoradas` lista; `--desfazer ID` faz voltar a valer.
  Só com o sim, edite **apenas aquelas linhas** de cada fatia para seguir a regra (sem reescrever o resto),
  mostre o `git diff` das fatias e rode `status-projeto contradicoes` de novo para confirmar. Não faça commit.

## Passo 4 — etapa `estimativa`
`status-projeto estimar`. Grava `docs/tempo/estimativa_git.csv` uma vez só ("estimado antes da instalação": sessões
com mais de 2 h entre commits, +30 min antes do primeiro commit). Se o comando disser que já existe, aceite — não refaça.

## Passo 5 — etapa `claude_md`
`status-projeto claude-md`. Se sair com código 3 (regras antigas de status/tempo fora do bloco), mostre as seções
achadas e pergunte: **trocar as antigas pelo bloco do plugin** (aí você mesmo remove do CLAUDE.md só aquelas seções,
mostra o diff e roda de novo) ou **gravar o bloco mesmo assim** (`--mesmo-assim`) ou **pular**.

## Passo 6 — etapa `hooks`
`status-projeto hooks`. Os hooks vêm do próprio plugin; o comando registra o plugin no `.claude/settings.json` do
projeto (para quem abrir o repo, inclusive no Claude Code na web). Se avisar de **hooks manuais antigos**, mostre e
pergunte se pode tirá-los (senão a mesma sessão conta duas vezes); só edite com o sim.

## Passo 7 — etapas `gitattributes` e `gitignore`
`status-projeto gitattributes`, depois `status-projeto gitignore` (ele já ignora sozinho a trava e o estado local,
que é seguro). Se apontar arquivos do status que estão ignorados, mostre e, com o ok do usuário (ou se os argumentos
disserem que pode corrigir o .gitignore), `status-projeto gitignore --corrigir`. Se continuar com problema (pasta-mãe inteira ignorada),
explique a linha que precisa mudar e pergunte antes de editar.

## Passo 8 — etapa `guia` e fechamento (sempre, também em continuar/reparar/atualizar/verificar)
0. Rode `status-projeto github`. Ele lê o DONO/REPO do remote (`origin`, ou o único remote; aceita qualquer host antes
   dos dois-pontos, inclusive apelidos do `~/.ssh/config` como `git@github-zapai:Dono/repo.git`). Se sair com
   **código 4** (não deu para saber), **pergunte ao usuário** (AskUserQuestion, com o remote mostrado na mensagem como
   contexto) qual é o repositório no GitHub no formato `DONO/REPO` e grave com `status-projeto github DONO/REPO`.
   **Nunca** escreva `<dono>` nem invente o dono. O `guia` e o `atualizar` também param com código 4 / aviso se faltar.
1. `status-projeto guia --gravar --marcar` (regrava o guia com a lista de (?) atual; sem `--gravar` só mostra) grava `docs/COMO_USAR_STATUS.md` e imprime o bloco **"⚠️ ATENÇÃO — LEIA ANTES DE
   COMEÇAR"**. Mostre esse bloco **inteiro** ao usuário, sem resumir (ele já traz como funciona, frases, comandos,
   fases, os passos manuais com o texto das instruções do claude.ai com o nome do repo, a frase de teste e os itens (?)).
2. Mostre `git status --short` com o que a instalação criou/alterou e diga: "para eu fazer commit e push, escreva
   **pode commitar**". Só com essa frase: `git add` dos arquivos da instalação (STATUS.md, CLAUDE.md, .gitattributes,
   .gitignore, .claude-status/config.json, .claude/settings.json, docs/tempo/, docs/COMO_USAR_STATUS.md), commit
   `chore(status): instala o status-projeto` e push (se houver remote).
