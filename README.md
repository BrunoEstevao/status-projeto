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

Precisa de Claude Code 2.1 ou mais novo, `git` e `python3`.

**1. Instale o plugin** (uma vez por computador). Dentro do Claude Code:

```
/plugin marketplace add BrunoEstevao/status-projeto
/plugin install status-projeto@status-projeto
/reload-plugins
```

Ou pelo terminal:

```bash
claude plugin marketplace add BrunoEstevao/status-projeto
claude plugin install status-projeto@status-projeto
```

(Para testar a partir de uma pasta local:
`/plugin marketplace add /caminho/para/status-projeto`.)

**2. Instale no seu projeto.** Abra o Claude Code na pasta do projeto e rode:

```
/instalar-status
```

Ele pergunta três coisas: seu nome, o valor da hora (padrão R$ 150) e a pasta das fatias (ele mostra a pasta que já
existir). Depois disso:

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
no projeto (painel da direita → Instruções → Adicionar) e mandar a frase de teste numa sessão do projeto.

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

## Comandos

| Comando | Para quê |
|---|---|
| `/instalar-status` | instala, verifica, repara ou atualiza |
| `/status-ajuda` | estado atual do projeto + guia de uso |
| `/status-relatorio` | horas e custo: estimado × medido; interativo, autônomo, planejamento e teste separados; por fatia; equivalente em dias de 8 h. `--todos` soma os repos irmãos descontando a sobreposição |
| `/status-historico` | linha do tempo das fatias com datas, horas e custo |
| `/status-cronograma` | projeta as fatias de 📦 pela média de horas das fatias do mesmo tamanho; avisa quando houver pouco dado medido |
| `/status-resumo` | só o que mudou nos últimos 3 dias, por fase |
| `/status-valor 180` | muda o valor da hora daqui para frente, sem efeito retroativo |
| `/verificar-integracao` | confere tudo no repo e entrega a frase para testar no claude.ai |

Se outro plugin usar o mesmo nome, use o nome completo: `/status-projeto:status-relatorio`.

## O que o plugin grava no seu repositório

| Arquivo | O que é | Vai para o git? |
|---|---|---|
| `STATUS.md` | o status (5 fases) | sim |
| `CLAUDE.md` | regras, num bloco entre `<!-- status-projeto:inicio -->` e `<!-- status-projeto:fim -->` | sim |
| `.claude-status/config.json` | versão, data da instalação, seu nome, valor da hora com histórico, pasta das fatias, repos irmãos, etapas concluídas | sim |
| `docs/tempo/sessoes.csv` | tempo medido: `inicio,fim,repo,fatia,tipo,sessao,estado` | sim (com `merge=union`) |
| `docs/tempo/estimativa_git.csv` | horas estimadas pelo git antes da instalação | sim |
| `docs/COMO_USAR_STATUS.md` | o guia "ATENÇÃO — LEIA ANTES DE COMEÇAR" | sim |
| `.gitattributes`, `.gitignore` | `merge=union` no CSV; trava e estado local fora do git | sim |
| `.claude/settings.json` | registra o plugin no projeto (quem abrir o repo recebe o convite para instalar) | sim |
| `.claude-status/local/`, `docs/tempo/*.lock` | estado desta máquina | não |

**Privacidade:** o CSV guarda só data/hora, nome do repo, nome da fatia, tipo, id da sessão e estado. O texto das
mensagens nunca é gravado. Os hooks só fazem algo em repositórios que têm `.claude-status/config.json`. Nos outros
projetos o plugin não grava nada.

## Como o tempo é medido

- **Hooks** do plugin (início de sessão, mensagem, uso de ferramenta, fim de resposta, fim de sessão) atualizam a linha
  da sessão. **30 minutos sem nenhum evento fecham a sessão** no último evento, então terminal esquecido aberto não conta.
- **Tipos:** `interativo`; `autonomo` (`claude -p`, Agent SDK, `STATUS_PROJETO_TIPO=autonomo` ou um processo listado em
  `autonomo_processos` no config); `teste` ("vou testar" → "terminei o teste"); `planejamento` (modo plano ou "vou planejar").
- **Fatia** da sessão: a branch de trabalho, ou os itens em 🌐 do `STATUS.md`.
- **Estimativa pelo git** (uma vez, na instalação): commits de todas as branches. Mais de 2 h entre commits abre uma
  sessão nova, e cada sessão ganha 30 min antes do primeiro commit. A fatia vem de `FATIA_<NOME>` na mensagem ou do
  escopo do commit (`feat(login): ...`). É uma aproximação, e os relatórios sempre mostram a estimativa separada do
  tempo medido.
- **Valor da hora com histórico:** cada sessão usa o valor que valia quando ela começou. Mudar o valor
  (`/status-valor`) acrescenta uma linha e não muda nada do que já foi calculado.

## Projeto com vários repositórios

Se o projeto tem mais de um repo (por exemplo `app-web`, `app-ios`, `api`), instale o plugin em cada um e liste os
irmãos no config de cada repo:

```bash
status-projeto repos --adicionar ../app-ios --adicionar ../api
```

Com isso, o limite de 3 itens em 🌐 passa a somar todos os repos, e `/status-relatorio --todos` soma as horas
descontando o tempo em que dois repos andaram juntos. Um repo irmão sem o plugin entra só com a estimativa do git.

## Atualizar o plugin

```
/plugin marketplace update status-projeto
/plugin update status-projeto@status-projeto
/reload-plugins
```

Depois rode `/instalar-status` em cada projeto e escolha **Atualizar**. Isso completa o config com os campos novos e
regrava só o bloco de regras do `CLAUDE.md` e o guia. O `STATUS.md`, o `sessoes.csv` e a estimativa nunca são tocados.
Instalações antigas continuam funcionando mesmo sem atualizar, porque campos que faltam no config ganham o valor
padrão na leitura.

## Desinstalar

`/plugin uninstall status-projeto@status-projeto` desliga os hooks. Os arquivos no repo continuam lá (são seus); para
tirar as regras, apague o bloco entre as marcas `status-projeto` no `CLAUDE.md`.

## Desenvolvimento

```bash
claude plugin validate .        # valida plugin e marketplace
tests/testar.sh                 # instala 2x num repo vazio e num com histórico, simula hooks e relatórios
claude --plugin-dir .           # usa o plugin desta pasta sem instalar
```

Licença MIT.
