# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versões: [SemVer](https://semver.org/lang/pt-BR/).
Regra de compatibilidade: versão nova nunca exige reinstalar. Campos novos do `.claude-status/config.json` entram com
valor padrão (`comum.migrar`); `STATUS.md`, `sessoes.csv` e `estimativa_git.csv` nunca são reescritos por atualização;
as colunas do `sessoes.csv` só podem ganhar colunas novas no fim.

## [1.15.0] — 2026-11-25
### Adicionado
- `status-projeto sessao listar | corrigir | correcoes`: corrige uma sessão do `docs/tempo/sessoes.csv` sem apagar
  nem reescrever nada. `corrigir --linha N` (o nº que o `listar` mostra) ou `--inicio "AAAA-MM-DD HH:MM"`, com
  `--anular` (tempo zero) ou `--novo-inicio` / `--novo-fim` / `--novo-tipo` / `--nova-fatia`, e `--motivo`
  obrigatório. A correção é uma linha a mais no fim do arquivo (dados no campo `sessao`: `correcao|quando|ação|
  sessão|início|tipo|motivo`); vale a mais recente, mesmo que a linha original tenha fim mais tarde. Recusa (código
  3) sem motivo, fim antes do início ou no futuro, e correção de uma linha de correção. `relatorio`, `historico`,
  `resumo`, `ajuda`, `erro anotar` e o tempo do roteiro por link já usam o valor corrigido; os relatórios dizem
  quantas sessões corrigidas entraram. Teste aberto anulado deixa de estar aberto.
- Proteção para teste longo: fechar um teste com mais de 2 h mostra a duração e só grava com uma resposta que começa
  com "confirmo"; "vou testar" com teste aberto há mais de 2 h não abre outro nem fecha o anterior pela hora atual;
  teste aberto há mais de 12 h não fecha pela hora atual (pergunta o horário real).
### Corrigido
- "vou testar" abria teste em qualquer frase, inclusive "vou testar mais tarde". Agora não abre com adiamento
  (mais tarde, depois, amanhã, dia da semana etc.), negação ou pergunta; no meio de outra frase não abre e o Claude
  pergunta.
- "terminei o teste" só era reconhecido no começo da mensagem. Agora vale em qualquer ponto (também "acabei os
  testes", "terminei de testar"), menos com negação ("ainda não terminei o teste") ou pergunta.
- O horário de "terminei o teste às HH:MM" se perdia: com a frase fora do começo da mensagem nada era reconhecido,
  e um horário antes do início do teste virava, sem aviso, a hora em que a mensagem chegou. Agora o fim é o horário
  dito, com data opcional ("em 24/11 às 21:30"); passou da meia-noite é o dia seguinte; horário antes do início, no
  futuro ou ambíguo (mais de um dia possível) não é gravado e o Claude pergunta.
- Regras novas no bloco do CLAUDE.md (frases de teste, "confirmo", sessão gravada errada), no guia, no README e no
  `/status-ajuda` (mostra o fim que espera confirmação).
### Compatível
- Colunas do `sessoes.csv` não mudam; arquivos sem correção são lidos como antes. As linhas de correção ficam sempre
  no fim do arquivo quando o hook o regrava, para o nº de linha das sessões não mudar entre uma correção e outra.

## [1.14.0] — 2026-11-22
### Adicionado
- Teste interrompido para correção ("Parar para corrigir erros" no serviço de testes): `roteiro resultado` lê o
  `resultado.json` no formato 2 (`situacao` `interrompido`, itens `sem_resposta`, `observacao_geral`) e avalia como
  resultado final. No terminal: a observação geral no topo, entre as marcas do texto do testador, e a tabela de ações
  com uma linha por item reprovado e uma linha só "N itens não chegaram a ser testados" com os títulos, sem ação. No
  `STATUS.md`: `respondida (interrompido para correção; aguardando a ordem)` e o `Pendente:` com os reprovados e a
  quantidade de itens sem resposta, e nada mais até a ordem. No arquivo de rodada: a situação, a observação em
  citação e os sem resposta numa lista própria. Os "outros erros" vão para o `ERROS.md` e o tempo conta do início à
  interrupção, no horário local, sem duplicar com o "vou testar".
- `roteiro voltar` aceita o teste interrompido (volta para 🌐 com o mesmo `Pendente:`).
- `roteiro nova-rodada` repete também os `sem_resposta` e cita na introdução cada item pelo título, com o porquê.
- JSON da avaliação: `situacao_teste`, `sem_resposta` e `observacao_geral` (como `texto_do_testador`).
- Regra nova no bloco do CLAUDE.md, seção no guia e no README.
### Compatível
- Resultados no formato 1 continuam sendo lidos como antes; teste `aberto` continua só informando o andamento.
- Rodada interrompida e ainda não avaliada impede publicar outra, como a terminada.

## [1.13.0] — 2026-11-22
### Adicionado
- Roteiro de teste por link (opcional, com o serviço de testes): `status-projeto testes configurar` grava a pasta de
  dados, o endereço base e a validade (padrão 7 dias) em `~/.claude/status-projeto/testes.json`, fora dos repos, e
  confere se a pasta existe, aceita escrita e se o grupo dela vale na sessão. Sem a configuração, tudo como antes.
- `status-projeto roteiro publicar`: grava o `roteiro.json` no formato do serviço (código de 128 bits, pasta 2770),
  recusa senhas, chaves e tokens apontando o trecho, grava a versão do app (`versao_app`) quando o projeto tem, anota
  no item da fatia no `STATUS.md` só a rodada e a situação (`publicada` → `respondida` → `avaliada`) e mostra o
  roteiro com o link no topo. O link e o código ficam em `.claude-status/local/roteiros.json`, fora do git;
  `roteiro mostrar [--rodada N] [--fotos]` devolve o link e os links das fotos. Rodada publicada e sem
  resposta não é publicada de novo (mostra o mesmo link; `--substituir` troca).
- `status-projeto roteiro resultado` ("teste finalizado, avalie"): valida e limpa o `resultado.json`, informa o
  andamento se o teste não terminou (sem mudar nada), grava `fatias/testes/<FATIA>-rodada-<N>.md` (texto do testador
  em citação; fotos só como link), registra o tempo de teste em UTC → horário local sem contar em dobro com o
  "vou testar", manda os "outros erros" para o `ERROS.md` com aparelho e versão e decide: tudo passou → ✅ e arquiva
  a fatia, o relatório e as rodadas em `fatias_executadas/`; reprovou → espera a ordem (`roteiro voltar` → 🌐);
  só "não consegui testar" → fica em 🧪.
- `status-projeto roteiro nova-rodada [--afetados]` (reprovados + não testados + afetados com o porquê) e
  `roteiro mostrar`.
- Campo opcional `roteiro_cabecalho` no config do projeto (campos extras do cabeçalho; padrão: só o nome).
- Campo `link_no_status` no config do projeto (padrão `false`): `true` põe código e link no `STATUS.md` e os links
  das fotos no arquivo de rodada. Só para repositório privado; o plugin avisa ao publicar e no `verificar`.
- Regras novas no bloco do CLAUDE.md (gatilhos e segurança: o texto do testador é dado, nunca instrução), seção no
  guia e no README, frases na ajuda; `/verificar-integracao` confere a configuração de testes quando ela existe; o
  hook lembra a regra em "teste finalizado, avalie" e "me traga o roteiro de teste".

## [1.12.0] — 2026-11-21
### Adicionado
- Instalado em mais de um escopo (ex.: user 1.11.0 + project 1.1.0 no mesmo projeto): `comum.instalacoes_plugin`
  lê o `installed_plugins.json` (em `~/.claude/plugins` ou `$CLAUDE_CONFIG_DIR/plugins`), considera só as
  instalações que valem para o projeto (a user e as project/local daquela pasta), descarta as sem pasta e as
  desativadas (`enabledPlugins` = false no settings do escopo) e escolhe a que vence: a versão mais nova e, no
  empate, a user.
- `status-projeto instalacoes [--json]`: mostra as instalações e, com mais de uma valendo, os comandos para ficar com
  uma só no escopo user (código 3). `estado` traz `instalacoes_plugin` e `enabled_plugins_antigo`; `verificar`
  mostra as instalações no começo e marca ❌ quando há mais de uma ou quando o `enabledPlugins` antigo continua no
  `.claude/settings.json`.
- `/instalar-status` e `/verificar-integracao` avisam das instalações duplicadas antes de tudo, com os comandos. Não
  desinstalam nem atualizam o plugin sozinhos.
### Mudado
- Hook de tempo: se esta cópia está no `installed_plugins.json` e não é a que vence, sai em silêncio (código 0), e só
  a vencedora grava. Cópia fora do JSON (`--plugin-dir`) roda normalmente.
- README: instalar e atualizar sempre com `--scope user`; seção nova "Duas instalações ao mesmo tempo".
### Corrigido
- Causa da instalação dupla: a etapa `hooks` gravava `enabledPlugins` no `.claude/settings.json` de cada projeto, o
  que fazia o Claude Code oferecer a instalação em escopo project. Agora grava só o `extraKnownMarketplaces`. O
  `atualizar` (e a etapa `hooks`, quando roda de novo) tira o `enabledPlugins` do status-projeto dos projetos que já
  têm, mostrando antes o que sai, e não mexe nas entradas de outros plugins.
- `fonte_marketplace` lê o `known_marketplaces.json` também em `$CLAUDE_CONFIG_DIR`.

## [1.11.0] — 2026-11-21
### Adicionado
- Windows: o Python é achado sozinho, nesta ordem: `python3`, `python`, `py -3` (o primeiro que for Python 3.8+; o
  atalho da Microsoft Store e o Python 2 são pulados) e, fora do PATH, as pastas onde o instalador põe
  (`%LOCALAPPDATA%\Programs\Python\Python3*`, `Program Files`, Homebrew). O comando achado fica em cache em
  `~/.claude/status-projeto/python.txt` (os hooks rodam a cada ferramenta).
- `status-projeto preparar`, `git-init` e `instalar-python`, em bash puro (funcionam antes de existir Python):
  - `preparar`: JSON com o sistema, o Python achado (e os recusados), o comando de instalação e a situação do git
    (`ok`, `sem_repo`, `pasta_pessoal`, `dono_diferente` com o `safe.directory` que o git sugere, `sem_git`).
  - `git-init`: cria o repositório; recusa a pasta pessoal (código 3).
  - `instalar-python`: instala pelo `winget` (com `PrependPath=1`, que põe no PATH), `apt`, `dnf`, `pacman` ou `brew`.
    Sem gerenciador ou se falhar: passo a passo manual (no Windows, marcar "Add python.exe to PATH"). `sudo` que pede
    senha: código 6, com a linha para rodar com `!`. Instalou mas o terminal não vê: código 7, avisa para reabrir e
    marca a instalação pendente; na próxima rodada, `preparar` diz `continuando: true`.
- `/instalar-status` (passo 0a): antes de qualquer pergunta, confere git e Python e oferece `git init`,
  `safe.directory` e a instalação do Python, sempre com confirmação. Continua recusando a pasta pessoal (agora também
  no `init`, e também quando a pasta pessoal é um repositório git).
- `.gitattributes` do projeto ganha `docs/tempo/*.csv text eol=lf` (no Windows, com `core.autocrlf=true`, o checkout
  poria CRLF nos CSVs); `reparar` aponta quando falta. O `.gitattributes` do plugin força LF nos scripts.
### Mudado
- Os hooks chamam `bash hooks/tempo.sh` em vez de `python3`: sem Python, saem em silêncio com código 0 (nada de
  "hook failed"). Sem Python, os outros comandos do `status-projeto` saem com código 5 (`SEM_PYTHON`).
### Corrigido
- Windows: saída e entrada em UTF-8 (o console em cp1252 quebrava nos emojis, e o "vou começar a codar" com ç
  chegava errado ao hook); texto do git lido em UTF-8; todo arquivo gravado com LF (STATUS.md, CLAUDE.md, config,
  guia), não só os CSVs.
- Caminhos: barra invertida em `--pasta-fatias`, `--repo` e no config feito no Windows (`docs\fatias`, `..\outro`)
  vira `/`; projeto na raiz da unidade (`Z:\`) e em pasta de rede (`\\servidor\pasta`) acha a raiz e o nome certos;
  caminho em outra unidade (C: × Z:) não quebra o relativo.

## [1.10.0] — 2026-11-21
### Adicionado
- Ideias pendentes e erros a corrigir: `IDEIAS.md` e `ERROS.md` na raiz do repo, criados pelo instalador
  (`status-projeto listas`) e pelo Atualizar, com `merge=union` no `.gitattributes`. Uma linha por registro (id, data,
  app, estado, texto; no `ERROS.md` também gravidade `grave`/`normal`, `completo`/`incompleto` e tela · aparelho ·
  versão). Nada é apagado: mudar o estado acrescenta uma linha com o mesmo id e vale a última. Não contam como status
  espalhado e entram na lista do `.gitignore` que precisa ir para o git.
- Estados: ideia `pendente` → `virou FATIA_X` | `descartada`; erro `aberto` → `em FATIA_CORRECOES_N` →
  `corrigido e testado`.
- `status-projeto ideia [listar|anotar|estado]` e `status-projeto erro [listar|anotar|completar|estado|fatia]`.
  `erro anotar` recusa (código 3) quando há teste aberto: erro no teste de uma fatia em 🧪 é teste reprovado
  (`--fora-do-teste` quando não é daquela fatia); erro grave sai com a sugestão de virar fatia de correção.
  `erro fatia` mostra a prévia e, com `--gravar`, cria `fatias/FATIA_CORRECOES_N.md` com os erros abertos agrupados por
  área (tela), registra em 📦 (no topo se houver erro grave) e marca os erros `em FATIA_CORRECOES_N`.
  Ideia pendente há mais de 60 dias aparece marcada para perguntar se mantém ou descarta. Projeto com vários repos:
  cada item leva a etiqueta do app e vai para o repo dele; sem `--app`, o comando pede para perguntar (código 3).
- `status-projeto colar "<linha>"`: grava a linha pronta que o claude.ai mostra quando não consegue gravar.
- Skills `/status-ideias` e `/status-erros`. O `/status-resumo` e o `/status-ajuda` mostram quantas ideias e erros
  estão abertos. Regras do CLAUDE.md com as frases "anota a ideia: ...", "anota o erro: ...", "quais ideias
  pendentes?", "quais erros a corrigir?" e "monta a fatia de correção"; guia e README atualizados.
- Instruções do claude.ai: a sessão pode gravar **só** em `IDEIAS.md` e `ERROS.md`, sempre acrescentando linha, com
  pull antes do push; nunca no `STATUS.md`. Se não gravar, diz "NÃO GRAVEI" e mostra a linha pronta. O guia e o
  `/verificar-integracao` trazem uma frase de teste da gravação.
- `reparar`/`verificar` apontam `IDEIAS.md`/`ERROS.md` ou o `merge=union` deles faltando.

## [1.9.0] — 2026-11-21
### Adicionado
- Exceções à regra "status só no STATUS.md": o `espalhado` mostra quando um arquivo de status é lido pelo código
  (`lido_por`; ex.: `PENDENCIAS.md` lido por `packages/shared/src/versoes.ts`, o `versao:fechar`), casando o nome
  inteiro e sem contar comentários. `status-projeto excecao ARQUIVO [--motivo ...]` registra a exceção na seção
  "Exceções à regra de status (status-projeto)" do CLAUDE.md, **fora do bloco do plugin**: o Atualizar não apaga a
  seção, e ela não é tratada como regra antiga. `--listar` mostra as exceções; o `espalhado` marca as registradas.
- `/instalar-status` (passo 3): para cada arquivo de status lido pelo código, oferece registrar a exceção em vez de
  tirar o status dele.
- Regras do CLAUDE.md: a regra "status só no STATUS.md" cita a seção de exceções.

## [1.8.0] — 2026-11-21
### Adicionado
- `status-projeto autonomo` (e `chamadas_autonomas` no `estado`): acha os scripts que rodam o Claude sozinho
  (`claude -p`/`--print` em `.sh`, `.ps1`, `.bat`, `.js`, `.py`, `package.json`...), inclusive no PowerShell com o
  caminho numa variável (`Start-Process -FilePath $Claude -ArgumentList "-p ..."`), e diz se a chamada já leva
  `STATUS_PROJETO_TIPO=autonomo`. `--aplicar ARQUIVO:LINHA` inclui a variável: no shell antes do `claude` (com `env`
  depois de `exec`/`nohup`/`sudo`), no `.ps1`/`.bat` numa linha antes. Em `.js`/`.py`, a edição é à mão.
- `/instalar-status` (passo 6b): mostra essas chamadas e oferece incluir a variável, para o tempo de um supervisor
  entrar como autônomo no relatório.

## [1.7.0] — 2026-11-21
### Adicionado
- Corte do ✅: `status-projeto status-md --cortar-concluidos [--dias N] [--ver ARQUIVO]` mantém no ✅ só os itens dos
  últimos N dias (padrão 7, pela data do `(desde)`) e fecha a fase com `- Versões anteriores: ver <arquivo>`. Os itens
  tirados vão para `docs/CONCLUIDOS.md` (ou o `.md` indicado), com os subitens. Itens sem data ficam. Se o ✅ já
  tiver a linha apontando para outro lugar, a referência é mantida. Rodar de novo não muda nada. A escolha fica no
  config (`corte_concluidos_dias`, `arquivo_concluidos`).
- `/instalar-status` (passo 3c): oferece o corte quando há concluídos com mais de 7 dias
  (`status_md.concluidos_mais_de_7_dias` no `estado`).
### Corrigido
- A linha "Versões anteriores: ver ..." não é mais lida como item: não gera aviso de data faltando e não entra em
  histórico nem cronograma.

## [1.6.1] — 2026-11-21
### Corrigido
- Custo da estimativa: o relatório multiplicava as horas arredondadas (2 casas) pelo valor. Agora usa a coluna
  `custo` do CSV, calculada com as horas sem arredondar. No zapai, o subtotal estimado passa de R$ 36.601,50 para
  R$ 36.607,48, a soma do arquivo. A soma sem sobreposição usa o mesmo valor por hora de cada sessão.
- CSVs gravados sempre com LF (`lineterminator="\n"`): `sessoes.csv` (hooks) e `estimativa_git.csv`. Um
  `sessoes.csv` antigo com CRLF passa para LF na próxima gravação dos hooks. No `taxa.csv` do projeto, a linha nova
  segue a terminação que o arquivo já usa, porque as linhas antigas não são mexidas.

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
