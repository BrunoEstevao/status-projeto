---
name: status-erros
description: Erros a corrigir do projeto (ERROS.md) — listar, anotar, completar tela/aparelho/versão, mudar o estado e montar a fatia de correção (FATIA_CORRECOES_N). Use quando o usuário disser "anota o erro: ...", "quais erros a corrigir?" ou "monta a fatia de correção".
argument-hint: "[anotar <texto> [--grave] | completar ID | estado ID --para ... | fatia | --todos]"
allowed-tools: Bash(status-projeto *) Bash(git diff *) AskUserQuestion
---
Argumentos: `$ARGUMENTS`. O programa é `status-projeto` (no PATH; senão
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status_projeto.py"`). Nunca edite o `ERROS.md` à mão: só acrescenta linha,
pelo programa, e nada é apagado.

- **Anotar** (`anotar ...` ou "anota o erro: ..."): grave na hora, do jeito que foi dito, **sem perguntas**:
  `status-projeto erro anotar "<texto>" [--grave] [--tela X] [--aparelho Y] [--versao Z]` — só o que foi dito
  (`--grave` só se o usuário disse que é grave ou que impede o uso). O que faltar fica `incompleto`.
  - Código 3 com **teste aberto**: diga que erro achado no teste de uma fatia em 🧪 é teste reprovado — a fatia volta
    para 🌐 com o erro em `Pendente:` (regra do CLAUDE.md) — e não grave no ERROS.md. Só se o usuário disser que o
    erro não é daquela fatia: `--fora-do-teste`.
  - Código 3 com **vários repos**: pergunte de qual app é (AskUserQuestion, sem recomendada) e rode com `--app NOME`.
  - **Erro grave**: ofereça (AskUserQuestion) **Montar a fatia de correção agora, no topo do 📦 (Recomendado)** —
    motivo: "erro grave passa na frente das outras fatias" · **Deixar na lista**. Sim → `status-projeto erro fatia
    --ids ID`, mostre a prévia e grave com `--gravar`.
- **Listar** (sem argumentos, ou "quais erros a corrigir?"): `status-projeto erro listar` (`--todos` inclui os
  corrigidos) e mostre a saída inteira. Para cada erro `incompleto`, pergunte o que falta (tela, aparelho, versão; só o
  usuário sabe) e grave com `status-projeto erro completar ID --tela ... --aparelho ... --versao ...`.
- **Montar a fatia de correção** (`fatia` ou "monta a fatia de correção"): `status-projeto erro fatia` mostra a
  prévia (erros abertos agrupados por área/tela, tamanho, posição no 📦). Se houver incompletos, pergunte os dados
  antes. Com o sim: `status-projeto erro fatia --gravar` (cria `fatias/FATIA_CORRECOES_N.md`, registra em 📦 — no
  topo se houver erro grave — e marca os erros `em FATIA_CORRECOES_N`). Mostre o `git diff`.
- **Mudar o estado**: `status-projeto erro estado ID [ID...] --para aberto | "em FATIA_CORRECOES_N" | corrigido`, ou
  `--fatia FATIA_CORRECOES_N --para corrigido` quando a fatia de correção passar no teste (✅).
- Commit só com "pode commitar".
