---
name: status-valor
description: Muda o valor da hora do projeto daqui para frente, sem efeito retroativo.
argument-hint: "<valor> [--desde AAAA-MM-DD] [--obs texto]"
disable-model-invocation: true
allowed-tools: Bash(status-projeto *) AskUserQuestion
---
Argumentos: `$ARGUMENTS`. Se não vier um valor, pergunte qual (mostre o atual com `status-projeto relatorio | head -3`).
Rode `status-projeto valor <valor> [--desde ...] [--obs "..."]`. Ele acrescenta uma linha ao histórico em
`.claude-status/config.json`; nunca muda as anteriores e recusa data no passado. Mostre a saída e lembre em uma linha
que sessões antigas continuam com o valor da época. Não edite o config à mão.
