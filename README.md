# status-projeto — plugin do Claude Code

**O status do seu projeto num lugar só, e o tempo de trabalho medido sozinho.**

Você trabalha com o Claude Code em "fatias" (pedaços de trabalho com começo, meio e fim). Este plugin:

- mantém **um arquivo só de status**, o `STATUS.md`, com 5 fases. O Claude atualiza o arquivo quando você usa frases
  simples como "vou começar a codar", "finalizado" e "fecha o dia";
- **mede o tempo** de cada sessão do Claude Code (interativo, autônomo, teste e planejamento) num CSV dentro do repo,
  **sem gravar o texto das suas mensagens**;
- **estima as horas de antes da instalação** pelo histórico do git, uma vez só, e guarda essa estimativa separada do
  tempo medido;
- gera **relatórios de horas e custo**, a **linha do tempo** das fatias, o **cronograma** do que falta e o **resumo** dos
  últimos dias;
- deixa o mesmo `STATUS.md` legível pelo **claude.ai** (navegador/celular) pelo GitHub, para você perguntar "o que falta?"
  de qualquer lugar.

Tudo em português. Só usa Python 3 (biblioteca padrão) e git, que você já tem.

## As 5 fases do STATUS.md

| Fase | Quer dizer |
|---|---|
| 🌐 Codando | em andamento agora (no máximo 3 itens, somando todos os repos do projeto). Cada item tem *Parei em / Próximo passo / Pendente* |
| 📦 Fatia pronta, não iniciada | na fila; o primeiro é o próximo. Tamanho `[P]` até 3 h, `[M]` 3–10 h, `[G]` mais de 10 h |
| 🧪 Aguardando teste | código pronto, falta você testar |
| ⏸️ Bloqueado | depende de algo de fora, sempre com o motivo |
| ✅ Concluído | terminado, com a data |

Todo item termina com `(desde DD/MM)`, a data em que entrou na fase.

## Instalação

Precisa de Claude Code 2.1 ou mais novo, `git` e Python 3.8 ou mais novo (`python3`, `python` ou `py -3`: o
plugin usa o primeiro que for Python 3).

**No Windows** o Claude Code roda os comandos no **Git Bash**, então precisa do [Git for Windows](https://git-scm.com/download/win)
(traz o git e o Git Bash) e do **Python 3** ([python.org](https://www.python.org/downloads/); no instalador, marque
**"Add python.exe to PATH"**). Funciona em pasta com letra de unidade (`Z:\projeto`) e em pasta de rede.

O que o `/instalar-status` resolve sozinho, sempre perguntando antes (a opção recomendada é "sim"):

- **Pasta sem git**: oferece rodar `git init`. Na sua pasta pessoal ele recusa (abra o Claude Code na pasta do projeto).
- **Pasta de rede que o git recusa** ("dubious ownership"): mostra o `git config --global --add safe.directory ...` que o
  próprio git sugere e oferece rodar.
- **Sem Python 3**: mostra o comando e oferece instalar pelo gerenciador do sistema (`winget` no Windows, `apt`/`dnf`/
  `pacman` no Linux, `brew` no macOS). Se não houver gerenciador ou a instalação falhar, mostra o passo a passo.
  Comando com `sudo` que pede senha: ele mostra a linha para você rodar com `!` na frente.
- **Instalou, mas o terminal ainda não vê o Python** (o PATH novo só vale em terminal novo): ele procura também nas
  pastas onde o instalador põe o Python; se mesmo assim não achar, avisa para reabrir o Claude Code e, ao rodar
  `/instalar-status` de novo, continua de onde parou.

Sem Python, os hooks de tempo saem em silêncio (nada de "hook failed"); só não medem o tempo até o Python existir.

**1. Instale o plugin** (uma vez por computador, **sempre no escopo user**). Pelo terminal:

```bash
claude plugin marketplace add BrunoEstevao/status-projeto
claude plugin install status-projeto@status-projeto --scope user
```

Ou dentro do Claude Code: `/plugin marketplace add BrunoEstevao/status-projeto`, depois `/plugin` → aba
**Discover** → `status-projeto` → instalar escolhendo o escopo **user**, e `/reload-plugins`.

Não instale também no escopo project (nem aceite o convite "instalar para este projeto"): o plugin ficaria duas vezes,
cada uma numa versão. Veja [Duas instalações ao mesmo tempo](#duas-instalações-ao-mesmo-tempo).

(Para testar a partir de uma pasta local:
`/plugin marketplace add /caminho/para/status-projeto`.)

**2. Instale no seu projeto.** Abra o Claude Code na pasta do projeto e rode:

```
/instalar-status
```

Ele pergunta três coisas: seu nome, o valor da hora (padrão R$ 150) e a pasta das fatias (ele mostra a pasta que já
existir). Se o projeto já tiver `docs/tempo/taxa.csv` e `docs/tempo/estimativa_git.csv`, ele aproveita os dois sem
sobrescrever nem recalcular. Se o valor informado for diferente do atual do taxa.csv, ele pergunta a partir de quando
o novo vale e acrescenta uma linha no fim, sem mexer nas antigas. Depois disso:

- **projeto novo:** cria o `STATUS.md` vazio com as 5 fases;
- **projeto que já existe:** lista antes o status que estiver espalhado em outros arquivos (TODO, PROGRESSO,
  checklists...). Depois analisa o código e o git e preenche o `STATUS.md` com as datas `(desde DD/MM)`, marcando com
  `(?)` o que não conseguiu comprovar. Também estima as horas passadas pelo git e confere o `.gitignore`. Por fim,
  lista as instruções das fatias em 📦 que contradizem as regras do plugin (onde arquivar, `.gitignore`, onde gerar o
  relatório) e pergunta se pode corrigir;
- grava as regras no `CLAUDE.md` (num bloco marcado, sem mexer no resto) e o `.gitattributes`;
- termina com o guia **"ATENÇÃO — LEIA ANTES DE COMEÇAR"**, que também fica salvo em `docs/COMO_USAR_STATUS.md`.

Ele **não faz commit sozinho**: só depois que você escrever **"pode commitar"**.

Rodar `/instalar-status` de novo é seguro. Se já estiver instalado, ele oferece **sair, verificar, reparar** (só o que
falta) **ou atualizar**. Se a instalação anterior parou no meio, ele continua de onde parou. Ele nunca refaz a
estimativa do git, nunca sobrescreve o `STATUS.md` nem o `sessoes.csv` e nunca duplica as regras no `CLAUDE.md`.

**3. Passos manuais (para o claude.ai ler o status).** O guia final traz o texto pronto, já com o nome do repo:
liberar o repo no GitHub App do claude.ai (Configurações → Conectores → GitHub → "Claude GitHub App" →
Corrigir/Configurar → "Only select repositories"), conferir em "Verificar status do repositório", colar as instruções
no projeto (painel da direita → Instruções → Adicionar) e mandar a frase de teste numa sessão do projeto. Há também
uma frase de teste para a gravação no `IDEIAS.md` (a única coisa que o claude.ai pode gravar, junto com o `ERROS.md`).

## No dia a dia

| Você diz no Claude Code | O que acontece |
|---|---|
| `vou começar a codar` | o primeiro de 📦 (ou a fatia que você disser) vai para 🌐. O Claude avisa se já houver 3 em 🌐 |
| `finalizado` | a fatia vai para 🧪 com o roteiro do que testar |
| `vou testar FATIA_X` | começa a contar o tempo de teste |
| `terminei o teste` / `terminei o teste às 21:30` | fecha o tempo de teste e pergunta se passou (✅ ou volta para 🌐) |
| `fecha o dia` | atualiza Parei em / Próximo passo / Pendente, mostra o que mudou e faz commit do status e do tempo |
| `vou planejar` | o tempo conta como planejamento (o modo plano também conta) |

Se você esquecer um teste aberto, na próxima conversa o Claude pergunta se terminou e a que horas.

## Ideias e erros

Duas listas na raiz do repo, criadas pelo instalador (e pelo **Atualizar**): `IDEIAS.md` e `ERROS.md`. Cada uma tem
uma linha por registro (id, data, app, estado e texto; no `ERROS.md` também a gravidade `grave`/`normal`, a marca
`incompleto` e tela, aparelho e versão). **Nada é apagado**: mudar o estado acrescenta uma linha nova com o mesmo id, e
vale a última. Os dois arquivos têm `merge=union` e não contam como status espalhado.

- Ideia: `pendente` → `virou FATIA_X` | `descartada`.
- Erro: `aberto` → `em FATIA_CORRECOES_N` → `corrigido e testado`.

| Você diz no Claude Code | O que acontece |
|---|---|
| `anota a ideia: ...` | grava na hora, do jeito que foi dito, sem perguntas |
| `anota o erro: ...` | grava na hora; o que faltar (tela, aparelho, versão) fica `incompleto` e é perguntado quando a lista for pedida. Erro grave: o Claude oferece virar fatia de correção no topo do 📦 |
| `quais ideias pendentes?` | lista; ideia pendente há mais de 60 dias: pergunta se mantém ou descarta |
| `quais erros a corrigir?` | lista e pergunta o que falta nos incompletos |
| `monta a fatia de correção` | agrupa os erros abertos por área (tela), gera `fatias/FATIA_CORRECOES_N.md`, registra em 📦 e marca os erros |

Regras: erro achado durante o teste de uma fatia em 🧪 não entra na lista (é teste reprovado, e a fatia volta para
🌐). Em projeto com vários repos, cada item leva a etiqueta do app e é gravado no repo dele; na dúvida, o Claude
pergunta. O claude.ai também pode anotar, mas **só** nesses dois arquivos e sempre acrescentando linha (pull antes do
push); se não conseguir gravar, ele diz que não gravou e mostra a linha pronta para `status-projeto colar "<linha>"`.

## Comandos

| Comando | Para quê |
|---|---|
| `/instalar-status` | instala, verifica, repara ou atualiza |
| `/status-ajuda` | estado atual do projeto + guia de uso |
| `/status-relatorio` | horas e custo: estimado × medido; interativo, autônomo, planejamento e teste separados; por fatia; equivalente em dias de 8 h. `--todos` soma os repos irmãos descontando a sobreposição |
| `/status-historico` | linha do tempo das fatias com datas, horas e custo |
| `/status-cronograma` | projeta as fatias de 📦 pela média de horas das fatias do mesmo tamanho; avisa quando houver pouco dado medido |
| `/status-resumo` | só o que mudou nos últimos 3 dias, por fase, e quantas ideias e erros estão abertos |
| `/status-ideias` | ideias pendentes: listar, anotar, mudar o estado |
| `/status-erros` | erros a corrigir: listar, anotar, completar, mudar o estado, montar a fatia de correção |
| `status-projeto excecao ARQUIVO` | registra no CLAUDE.md (fora do bloco do plugin) um arquivo de status que o código lê, como exceção à regra "status só no STATUS.md" |
| `status-projeto status-md --cortar-concluidos` | mantém no ✅ só os últimos 7 dias (ou `--dias N`); os mais antigos vão para `docs/CONCLUIDOS.md` e o ✅ fecha com "Versões anteriores: ver ..." |
| `/status-valor 180` | muda o valor da hora daqui para frente, sem efeito retroativo |
| `/verificar-integracao` | confere tudo no repo e entrega a frase para testar no claude.ai |
| `status-projeto instalacoes` | instalações do plugin que valem neste projeto (user, project, local), qual vence e, se houver mais de uma, os comandos para ficar com uma só |

Se outro plugin usar o mesmo nome, use o nome completo: `/status-projeto:status-relatorio`.

## O que o plugin grava no seu repositório

| Arquivo | O que é | Vai para o git? |
|---|---|---|
| `STATUS.md` | o status (5 fases) | sim |
| `CLAUDE.md` | regras, num bloco entre `<!-- status-projeto:inicio -->` e `<!-- status-projeto:fim -->` | sim |
| `.claude-status/config.json` | versão, data da instalação, seu nome, valor da hora com histórico, pasta das fatias, repos irmãos, etapas concluídas | sim |
| `docs/tempo/sessoes.csv` | tempo medido: `inicio,fim,repo,fatia,tipo,sessao,estado` | sim (com `merge=union`) |
| `docs/tempo/estimativa_git.csv` | horas estimadas pelo git antes da instalação | sim |
| `docs/tempo/taxa.csv` | só se o projeto já tiver: histórico do valor da hora (`vigente_desde,valor_hora,observacao`), que passa a ser a fonte do valor; o plugin só acrescenta linhas no fim | sim |
| `IDEIAS.md`, `ERROS.md` | ideias pendentes e erros a corrigir, uma linha por registro (nada é apagado) | sim (com `merge=union`) |
| `docs/COMO_USAR_STATUS.md` | o guia "ATENÇÃO — LEIA ANTES DE COMEÇAR" | sim |
| `.gitattributes`, `.gitignore` | `merge=union` no CSV, no `IDEIAS.md` e no `ERROS.md`; trava e estado local fora do git | sim |
| `.claude/settings.json` | registra só o marketplace (`extraKnownMarketplaces`); não grava `enabledPlugins`, que levaria a uma 2ª instalação em escopo project | sim |
| `.claude-status/local/`, `docs/tempo/*.lock` | estado desta máquina | não |

**Privacidade:** o CSV guarda só data/hora, nome do repo, nome da fatia, tipo, id da sessão e estado. O texto das
mensagens nunca é gravado. Os hooks só fazem algo em repositórios que têm `.claude-status/config.json`. Nos outros
projetos o plugin não grava nada.

## Como o tempo é medido

- **Hooks** do plugin (início de sessão, mensagem, uso de ferramenta, fim de resposta, fim de sessão) atualizam a linha
  da sessão. **30 minutos sem nenhum evento fecham a sessão** no último evento, então terminal esquecido aberto não conta.
- **Tipos:** `interativo`; `autonomo` (`claude -p`, Agent SDK, `STATUS_PROJETO_TIPO=autonomo` ou um processo listado em
  `autonomo_processos` no config); `teste` ("vou testar" → "terminei o teste"); `planejamento` (modo plano ou "vou planejar").
  Scripts do projeto que chamam `claude -p` (um supervisor, por exemplo) são achados na instalação, que oferece
  incluir `STATUS_PROJETO_TIPO=autonomo` na chamada (`status-projeto autonomo`).
- **Fatia** da sessão: a branch de trabalho, ou os itens em 🌐 do `STATUS.md`.
- **Estimativa pelo git** (uma vez, na instalação): commits de todas as branches. Mais de 2 h entre commits abre uma
  sessão nova, e cada sessão ganha 30 min antes do primeiro commit. A fatia vem de `FATIA_<NOME>` na mensagem ou do
  escopo do commit (`feat(login): ...`). É uma aproximação, e os relatórios sempre mostram a estimativa separada do
  tempo medido.
- **Valor da hora com histórico:** cada sessão usa o valor que valia quando ela começou. Mudar o valor
  (`/status-valor`) acrescenta uma linha e não muda nada do que já foi calculado.
- **Custo sem arredondar:** o custo de cada sessão estimada é o da coluna `custo` do CSV, calculado com as horas
  exatas, então o relatório bate com a soma do arquivo. Os CSVs são gravados com LF.

## Projeto com vários repositórios

Se o projeto tem mais de um repo (por exemplo `app-web`, `app-ios`, `api`), instale o plugin em cada um e liste os
irmãos no config de cada repo:

```bash
status-projeto repos --adicionar ../app-ios --adicionar ../api
```

Com isso, o limite de 3 itens em 🌐 passa a somar todos os repos, e `/status-relatorio --todos` soma as horas
descontando o tempo em que dois repos andaram juntos. Um repo irmão sem o plugin entra só com a estimativa do git.

## Atualizar o plugin

**Pelo terminal** (a forma que a documentação do Claude Code dá para atualizar), dentro da pasta do projeto:

```bash
claude plugin marketplace update status-projeto
claude plugin update status-projeto@status-projeto --scope user
```

O primeiro comando só baixa o catálogo novo e não troca a versão instalada; quem atualiza é o segundo. Passe sempre o
`--scope user`: sem ele, o `update` atualiza a instalação mais específica da pasta onde você está (local → projeto →
usuário), e uma instalação de projeto esquecida seria atualizada no lugar da sua.

**Dentro da sessão:** `/plugin` → aba **Installed** → `status-projeto` → **Update now**. (Digitar `/plugin update ...`
com argumentos pode só abrir esse gerenciador, sem atualizar nada.)

Depois, numa sessão que já estava aberta, rode `/reload-plugins`. Até lá, os hooks continuam rodando da versão antiga.

Depois rode `/instalar-status` em cada projeto e escolha **Atualizar**. Isso completa o config com os campos novos e
regrava só o bloco de regras do `CLAUDE.md` e o guia. O `STATUS.md`, o `sessoes.csv` e a estimativa nunca são tocados.
Instalações antigas continuam funcionando mesmo sem atualizar, porque campos que faltam no config ganham o valor
padrão na leitura.

## Duas instalações ao mesmo tempo

O Claude Code deixa o mesmo plugin instalado em mais de um escopo: **user** (vale em todos os projetos) e **project**
ou **local** (só numa pasta). Quando os dois valem no mesmo projeto, os dois rodam, cada um na sua versão. O sintoma:
você atualiza e o projeto continua com o comportamento antigo, ou o tempo aparece contado duas vezes.

Até a 1.11.0, a etapa hooks do `/instalar-status` gravava `enabledPlugins` no `.claude/settings.json` do projeto, e
é isso que faz o Claude Code oferecer a instalação em escopo project a quem abre o repo. Desde a 1.12.0:

- a etapa hooks grava só o `extraKnownMarketplaces` (o marketplace) e o **Atualizar** tira o `enabledPlugins` do
  status-projeto dos projetos que já têm, mostrando antes o que sai;
- com mais de uma instalação valendo, só a que vence grava o tempo: a **versão mais nova** e, no empate, a **user**.
  As outras saem em silêncio. Instalações sem pasta ou desativadas não contam. Uma cópia carregada com
  `--plugin-dir` (fora do `installed_plugins.json`) roda sempre;
- `status-projeto instalacoes`, `/verificar-integracao` e `/instalar-status` mostram as instalações e, quando há
  mais de uma, os comandos para corrigir. **O plugin não desinstala nada sozinho.**

Versões anteriores à 1.12.0 não sabem qual vence e gravam sempre. Por isso, fique com uma só, no escopo user:

```bash
claude plugin marketplace update status-projeto
claude plugin update status-projeto@status-projeto --scope user
cd /caminho/do/projeto && claude plugin uninstall status-projeto@status-projeto --scope project
```

(Use `--scope local` se for essa a instalação a mais.) Depois, numa sessão aberta, rode `/reload-plugins`. Para ver a
situação de um projeto: `status-projeto instalacoes` na pasta dele (código 3 = mais de uma valendo).

## Desinstalar

`/plugin uninstall status-projeto@status-projeto` desliga os hooks. Os arquivos no repo continuam lá (são seus); para
tirar as regras, apague o bloco entre as marcas `status-projeto` no `CLAUDE.md`.

## Desenvolvimento

```bash
claude plugin validate .        # valida plugin e marketplace
tests/testar.sh                 # instala 2x num repo vazio e num com histórico, simula hooks e relatórios
                                # (inclui sem python, só python, py -3, pasta sem git e caminhos do Windows)
claude --plugin-dir .           # usa o plugin desta pasta sem instalar
```

Licença MIT.
