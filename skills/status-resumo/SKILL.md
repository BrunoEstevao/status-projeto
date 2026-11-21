---
name: status-resumo
description: Só o que mudou no STATUS.md nos últimos 3 dias, por fase, com as horas do período.
argument-hint: "[--dias N]"
allowed-tools: Bash(status-projeto *)
---
Rode `status-projeto resumo $ARGUMENTS` (padrão: 3 dias) e mostre a saída inteira num bloco de código.
Não acrescente nada que não mudou. Se não houve mudança, diga isso em uma linha.
