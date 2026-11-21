---
name: status-ideias
description: Ideias pendentes do projeto (IDEIAS.md) — listar, anotar e mudar o estado (virou FATIA_X, descartada, mantida). Use quando o usuário disser "anota a ideia: ..." ou "quais ideias pendentes?".
argument-hint: "[anotar <texto> | estado ID --para 'virou FATIA_X'|descartada|pendente | --todas]"
allowed-tools: Bash(status-projeto *) AskUserQuestion
---
Argumentos: `$ARGUMENTS`. O programa é `status-projeto` (no PATH; senão
`bash "${CLAUDE_PLUGIN_ROOT}/bin/status-projeto"`). Nunca edite o `IDEIAS.md` à mão: só acrescenta linha,
pelo programa, e nada é apagado.

- **Anotar** (`anotar ...` ou "anota a ideia: ..."): `status-projeto ideia anotar "<texto do jeito que foi dito>"`, **sem
  perguntas**, e confirme em uma linha. Projeto com vários repos: passe `--app NOME`; se o comando sair com código 3
  (não dá para saber o app), pergunte qual é (AskUserQuestion, com os apps da mensagem; sem recomendada).
- **Mudar o estado**: `status-projeto ideia estado ID [ID...] --para "virou FATIA_X" | descartada | pendente`.
- **Listar** (sem argumentos, ou "quais ideias pendentes?"): `status-projeto ideia listar` (`--todas` mostra também
  as que viraram fatia ou foram descartadas) e mostre a saída inteira. Para cada ideia marcada "pendente há N dias",
  pergunte (AskUserQuestion, até 4 por chamada; só o usuário sabe, sem recomendada): **Manter** (`--para pendente`,
  conta 60 dias de novo) · **Descartar** (`--para descartada`) · **Virou fatia** (pergunte qual e use
  `--para "virou FATIA_X"`).
- Commit só com "pode commitar".
