# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versões: [SemVer](https://semver.org/lang/pt-BR/).
Regra de compatibilidade: versão nova nunca exige reinstalar. Campos novos do `.claude-status/config.json` entram com
valor padrão (`comum.migrar`); `STATUS.md`, `sessoes.csv` e `estimativa_git.csv` nunca são reescritos por atualização;
as colunas do `sessoes.csv` só podem ganhar colunas novas no fim.

## [1.6.0] — 2026-11-21
### Adicionado
- Projeto que já tem `docs/tempo/taxa.csv`: o valor da hora vem dele, que passa a ser a fonte; o config guarda uma
  cópia. O `init` sem `--valor` aproveita o arquivo sem mexer nele. Com um valor diferente do atual, o `init` pede
  `--valor-desde` (o `/instalar-status` pergunta a partir de quando vale) e acrescenta uma linha no fim, sem tocar
  nas antigas. O `/status-valor` também acrescenta no taxa.csv.
- `estado` → `dados_existentes`: taxa.csv (histórico) e estimativa_git.csv (sessões, horas, custo, colunas) que o
  projeto já tem.
### Corrigido
- Instalação em projeto com estimativa e valor já registrados (caso do zapai): o instalador não recalcula nem edita a
  `estimativa_git.csv`, mesmo com outras colunas, e não troca o valor da hora sem perguntar a partir de quando vale.

## [1.5.0] — 2026-11-20
### Adicionado
- `status-projeto fatias-soltas` (e `fatias_fora_da_pasta` no `estado`): acha todo `FATIA_*.md` fora da pasta das
  fatias e da pasta das executadas, também com prefixo (`docs/2026-11-14_FATIA_X.md`), versionado, fora do git ou
  ignorado, e diz se o STATUS.md já o cita. Pasta com 3 ou mais fatias vira um grupo (uma pergunta só).
  O `/instalar-status` (passo 3a) roda isso sempre: com STATUS.md novo, já existente, ajustado e no Atualizar.
  Pergunta a fase de cada fatia solta, move para a pasta certa e registra no STATUS.md.
### Corrigido
- Fatias soltas ficavam de fora quando o STATUS.md já existia, e arquivos fora do git nem eram vistos (ex.:
  `FATIA_V3_API_2_CARTAO.md` na raiz).
- Status espalhado: o nome agora pega ESTADO, STATUS, PROGRESSO, ANDAMENTO (além de TODO, PENDENCIAS, BACKLOG...)
  em qualquer posição (`ESTADO_ATUAL.md`, `MINERADOR-STATUS.md`), sem confundir palavras como "metodologia". A busca
  inclui arquivos fora do git e ignorados (marcados assim) e pula `node_modules` e afins. O bloco de regras do
  plugin no `CLAUDE.md` não conta mais como status. Arquivos de fatia com checklist viram uma linha de contagem.

## [1.4.0] — 2026-11-20
### Adicionado
- STATUS.md com fases fora do padrão (ex.: `🔨 Em execução` no lugar de `🌐 Codando`): o `estado` lista essas seções
  em `status_md.fases_extras`, com a fase sugerida, e `status-projeto status-md --ajustar "Título=🌐"` troca o título
  pela fase padrão. Os itens vão juntos para a fase padrão sem perder nenhum, as 5 fases ficam na ordem e as que
  faltam são acrescentadas. Rodar de novo não muda nada. Antes, os itens dessas seções ficavam invisíveis para os hooks.
### Mudado
- `/instalar-status`: em toda pergunta de múltipla escolha, a opção recomendada vem primeiro, com "(Recomendado)" e
  o motivo em uma linha. Quando a escolha depende de algo que só o usuário sabe (nome, valor da hora, autores na
  estimativa, DONO/REPO), nenhuma vem recomendada e a pergunta diz do que depende. Com fases fora do padrão, a
  recomendada é "Ajustar ao formato".
### Corrigido
- README e guia: atualizar pelo terminal com `claude plugin update status-projeto@status-projeto` (com `--scope`
  quando houver mais de uma instalação) ou, dentro da sessão, pelo `/plugin` → Installed → Update now. Digitar
  `/plugin update ...` com argumentos pode só abrir o gerenciador.

## [1.3.0] — 2026-11-20
### Mudado
- `status-projeto guia` só mostra o guia. Para gravar `docs/COMO_USAR_STATUS.md` é preciso `--gravar` (o
  `/instalar-status` usa `guia --gravar --marcar`); `--marcar` sem `--gravar` é recusado. Antes, rodar o `guia` só
  para consultar regravava o arquivo do projeto.
- `reparar` não grava mais o config (só lista o que falta). O teste confere que os comandos de consulta (`relatorio`,
  `historico`, `cronograma`, `resumo`, `ajuda`, `contradicoes` sem `--ignorar`, `guia`, `estado`, `espalhado`,
  `github`, `verificar`, `reparar`) não mudam nenhum arquivo, nem com o guia apagado e o config antigo.

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
