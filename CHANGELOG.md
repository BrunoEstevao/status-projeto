# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versões: [SemVer](https://semver.org/lang/pt-BR/).
Regra de compatibilidade: versão nova nunca exige reinstalar. Campos novos do `.claude-status/config.json` entram com
valor padrão (`comum.migrar`); `STATUS.md`, `sessoes.csv` e `estimativa_git.csv` nunca são reescritos por atualização;
as colunas do `sessoes.csv` só podem ganhar colunas novas no fim.

## [1.0.0] — 2026-11-20
### Adicionado
- `/instalar-status`: instalação por etapas guardadas em `.claude-status/config.json` (continua de onde parou),
  com as opções sair, verificar, reparar e atualizar quando já está instalado. Projeto novo ganha `STATUS.md` vazio;
  projeto existente ganha o `STATUS.md` analisado do código e do git e a estimativa de horas pelo git. Antes de mexer,
  lista o status espalhado em outros arquivos. Confere o `.gitignore`, grava as regras no `CLAUDE.md` num bloco só,
  instala o `.gitattributes` (`merge=union`) e o guia `docs/COMO_USAR_STATUS.md`.
- Hooks de tempo (SessionStart, UserPromptSubmit, PostToolUse, Stop, SessionEnd) → `docs/tempo/sessoes.csv`, com os
  tipos interativo, autônomo, teste e planejamento. 30 min sem evento fecham a sessão. Um teste esquecido aberto gera
  uma pergunta, uma vez só. Avisa quando o limite de 3 itens em 🌐 já foi atingido somando os repos irmãos.
- `/status-relatorio`, `/status-valor`, `/status-historico`, `/status-cronograma`, `/status-resumo`, `/status-ajuda`
  e `/verificar-integracao`.
- Projeto com vários repos (`repos` no config, `status-projeto repos --adicionar`).
