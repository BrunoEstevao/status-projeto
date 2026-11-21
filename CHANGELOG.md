# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versões: [SemVer](https://semver.org/lang/pt-BR/).
Regra de compatibilidade: versão nova nunca exige reinstalar. Campos novos do `.claude-status/config.json` entram com
valor padrão (`comum.migrar`); `STATUS.md`, `sessoes.csv` e `estimativa_git.csv` nunca são reescritos por atualização;
as colunas do `sessoes.csv` só podem ganhar colunas novas no fim.

## [1.2.0] — 2026-11-20
### Adicionado
- `status-projeto contradicoes --ignorar ID [--obs motivo]`: marca um apontamento como falso positivo. Fica em
  `contradicoes_ignoradas` no config (campo novo, padrão vazio) e não volta nas próximas rodadas. O id não depende do
  número da linha nem da pasta da fatia; se o texto da linha mudar, o apontamento volta. `--ignoradas` lista os ignorados e
  `--desfazer ID` faz um voltar a valer. O `/instalar-status` oferece a opção "Marcar como ignorado".
### Corrigido
- `contradicoes` marcava como `.gitignore` instruções de deixar a árvore limpa ("se houver alteração não commitada,
  pare e peça para commitar"). Agora só conta instrução de não versionar ("não commite o X") com um arquivo do status
  citado, e não marca o que concorda com a regra ("confira que X não está no .gitignore", "tire X do .gitignore").
- Guia: as instruções do claude.ai separavam as fases com ` | `, e a linha "🧪 Aguardando teste" aparecia duplicada
  na tabela de fases quando o guia era exibido em markdown (o template estava certo). As fases agora vêm uma por
  linha, e as instruções e a frase de teste ficam em bloco de código.

## [1.1.0] — 2026-11-20
### Adicionado
- `status-projeto contradicoes`: na instalação em projeto existente (e no Atualizar), lê o arquivo de cada fatia em 📦
  e lista as instruções que contradizem as regras do plugin — onde arquivar (`git mv` para a pasta das executadas,
  nunca apagar), `.gitignore` (arquivos do status vão para o git), onde gerar o relatório (junto da fatia) e status
  fora do `STATUS.md`. Não altera nada: o `/instalar-status` mostra a lista e pergunta se pode corrigir.

## [1.0.1] — 2026-11-20
### Corrigido
- O remote com apelido SSH do `~/.ssh/config` (ex.: `git@github-zapai:Dono/repo.git`) não era reconhecido e o guia
  saía com `<dono>/repo`. Agora qualquer host antes dos dois-pontos é aceito (e também `https://`, `ssh://` com porta
  e credenciais na URL); sem `origin`, vale o único remote do repo.
- Quando mesmo assim não dá para saber o `DONO/REPO`, o guia não é gravado com `<dono>`: o comando sai com código 4 e
  o `/instalar-status` pergunta ao usuário. O `reparar` aponta guia antigo com `<dono>`.
### Adicionado
- `status-projeto github [DONO/REPO]`: mostra o repo detectado ou grava o informado (campo novo `repo_github` no
  config, com valor padrão vazio — não exige reinstalar).

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
