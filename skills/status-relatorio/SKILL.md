---
name: status-relatorio
description: Relatório de horas e custo do projeto (estimado pelo git antes da instalação × medido pelos hooks; interativo, autônomo, planejamento e teste; por fatia; dias de 8 h). Use quando o usuário pedir horas, custo ou quanto o projeto já custou.
argument-hint: "[--todos] [--repo ../outro]"
allowed-tools: Bash(status-projeto *)
---
Rode `status-projeto relatorio $ARGUMENTS` (sem argumentos cobre só este repo; `--todos` soma os repos irmãos do
`.claude-status/config.json` descontando a sobreposição; `--repo DIR` soma outro repo).
Mostre a saída **inteira** num bloco de código. Depois, em até 3 linhas: total, quanto é estimado × medido, e a maior
fatia. Se o projeto tiver irmãos e o usuário não passou `--todos`, ofereça somar. Não recalcule nada à mão.
