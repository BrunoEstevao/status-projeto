---
name: instalar-status
description: Instala (ou verifica, repara e atualiza) o status-projeto neste repositório — STATUS.md com 5 fases, regras no CLAUDE.md, medição de tempo por hooks, estimativa de horas pelo git e guia de uso.
argument-hint: "[usuario=Nome valor=150 pasta=fatias] [verificar|reparar|atualizar|sair]"
disable-model-invocation: true
allowed-tools: Bash(status-projeto *) Bash(git log *) Bash(git status *) Bash(git ls-files *) Bash(git branch *) Bash(git tag *) Bash(git show *) Bash(git diff *) Read Glob Grep Write Edit AskUserQuestion
---

# /instalar-status

Você vai instalar o status-projeto no repositório atual. Fale em português, curto. O programa auxiliar é
`status-projeto` (está no PATH; se não estiver, use `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status_projeto.py"`).
Argumentos recebidos: `$ARGUMENTS` (podem trazer `usuario=`, `valor=`, `pasta=`; o que vier não precisa ser perguntado).

## Regras que nunca quebram
- **Nunca** reinstale por cima: se já houver instalação, siga o passo 1.
- **Nunca** sobrescreva `STATUS.md` nem `docs/tempo/sessoes.csv`. **Nunca** refaça a estimativa do git
  (`status-projeto estimar` já se recusa). **Nunca** duplique as regras no `CLAUDE.md` (o bloco fica entre marcas).
- **Nunca** faça commit nem push sem o usuário escrever **"pode commitar"**.
- Não leia nem copie segredos (`.env`, chaves). O que não der para comprovar pelo código/git: `(?)`.

## Como perguntar (toda AskUserQuestion deste instalador)
- A opção **recomendada vem primeiro**, com **"(Recomendado)" no fim do rótulo**, e a descrição dela é **o motivo
  em uma linha**. As outras opções dizem, na descrição, o que acontece se forem escolhidas.
- Quando a escolha depende de algo que só o usuário sabe, **não marque nenhuma como recomendada**: escreva na própria
  pergunta do que ela depende (ex.: "depende de os outros autores fazerem parte do mesmo custo").
- Abaixo, cada pergunta já traz a ordem, a recomendada e o motivo. Não invente outra recomendação.

## Passo 0 — diagnóstico
Rode `status-projeto estado` e leia o JSON (instalado, etapas_feitas, etapas_pendentes, precisa_atualizar, git,
projeto_novo, status_md, claude_md, pastas_fatias_detectadas, fatias_soltas_na_raiz, hooks_manuais_antigos).
Se `git.repo_git` for false, avise que precisa ser um repositório git (sugira `git init`) e pare.

## Passo 1 — já instalado?
- `instalacao_completa: true` → **não reinstale.** Se os argumentos trouxerem `sair`, `verificar`, `reparar` ou
  `atualizar`, use essa escolha sem perguntar. Senão, rode `status-projeto reparar` (só consulta) e pergunte
  (AskUserQuestion) o que fazer. A recomendada é a primeira que valer, nesta ordem:
  1. `precisa_atualizar` → **Atualizar (Recomendado)** — motivo: "instalado com a X, o plugin está na Y".
  2. `reparar` listou algo → **Reparar (Recomendado)** — motivo: o que falta, em poucas palavras.
  3. Nada disso → **Verificar (Recomendado)** — motivo: "confere se os hooks estão gravando e o GitHub está em dia,
     sem mudar nada".
  Depois da recomendada, as demais entre **Atualizar** · **Reparar** (só o que falta) · **Verificar**
  (rode o /verificar-integracao: `status-projeto verificar`), e **Sair** por último.
  - Reparar: `status-projeto reparar` lista o que falta ou quebrou; refaça **só esses itens** seguindo o passo
    correspondente abaixo. Nunca recrie STATUS.md por cima; se ele sumiu, ofereça restaurar do git.
  - Atualizar: `status-projeto atualizar` (migra o config, regrava só o bloco do CLAUDE.md e o guia), depois
    `status-projeto reparar` e trate o que aparecer. Mostre o que mudou do CHANGELOG do plugin
    (`${CLAUDE_PLUGIN_ROOT}/CHANGELOG.md`) entre `versao_plugin_instalada` e `versao_plugin`.
    Rode também o passo 3b (contradições nas fatias em 📦).
- `instalado: true` mas incompleto → diga "a instalação anterior parou; continuo de onde parou" e faça **só as etapas
  de `etapas_pendentes`**, na ordem abaixo. Não pergunte de novo o que já está no config.
- `instalado: false` → instalação nova, a partir do passo 2.

## Passo 2 — perguntas (só na primeira vez)
Uma AskUserQuestion com até 3 perguntas (pule as que vieram nos argumentos):
1. **Nome do usuário** (como as regras vão chamar a pessoa que testa e decide). Só o usuário sabe: sem recomendada.
   Primeira opção: o `git config user.name` (descrição: "o nome dos seus commits"); "Other" para outro nome.
2. **Valor da hora** (R$). Só o usuário sabe: sem recomendada; diga na pergunta que depende do valor que ele cobra
   ou quer usar como referência, e que vale só daqui para frente (muda com /status-valor). Opções:
   **150 (padrão do plugin)**, 100, 200.
3. **Pasta das fatias** — se `pastas_fatias_detectadas` não estiver vazia: **`<primeira detectada>` (Recomendado)** —
   motivo: "já tem N arquivos de fatia". Senão: **`fatias` (Recomendado)** — motivo: "é o nome que as regras e as
   instruções do claude.ai usam por padrão". A pasta das concluídas é `<pasta>_executadas` (ou a existente, ex.:
   `fatias_executadas`).
Se `git.autores` mostrar mais de uma pessoa, pergunte também se a estimativa conta **só os commits do usuário**
(`--autor "Nome"`) ou **todos**. Sem recomendada: depende de os outros autores fazerem parte do mesmo projeto/custo
(cite na pergunta os autores e o número de commits de cada um). Se o usuário citar repos irmãos do mesmo projeto, use `--repo ../outro` (pode repetir).
Depois: `status-projeto init --usuario "<nome>" --valor <valor> --pasta-fatias <pasta> [--pasta-executadas X] [--autor A] [--repo ../R]`.

## Passo 3 — etapa `status_md`
**Antes de mexer em qualquer coisa**, rode `status-projeto espalhado` e mostre a lista de arquivos com status
espalhado (TODO, PROGRESSO, checklists, "concluído"...). Não apague nada: só informe que, pela regra, o status passa
a morar só no STATUS.md, e pergunte (AskUserQuestion) o que fazer com esses arquivos — não faça agora sem ordem:
**Tirar o status desses arquivos depois (Recomendado)** — motivo: "duas fontes de status ficam diferentes com o
tempo, e o claude.ai só lê o STATUS.md" · **Deixar como está** — descrição: "escolha se outras pessoas ou
ferramentas usam esses arquivos". Se algum deles for de fatia, lembre que o passo 3b confere as fatias em 📦.

- **Projeto novo** (`projeto_novo: true`): `status-projeto status-md --vazio --marcar`.
- **STATUS.md já existe**: não sobrescreva.
  - **Fases fora do padrão** (`status_md.fases_extras` não vazio; ex.: `🔨 Em execução` no lugar de `🌐 Codando`):
    mostre cada uma com a fase sugerida (`sugestao`; vazia → proponha você pelo sentido, ou deixe de fora se for
    seção de notas) e quantos itens tem. Pergunte (AskUserQuestion):
    **Ajustar ao formato (Recomendado)** — motivo: "os hooks leem o nome da fatia da fase 🌐, o limite de 3 vale
    para ela e as instruções do claude.ai citam só as 5 fases padrão" ·
    **Só acrescentar as fases que faltam** — descrição: "deixa duas fases com o mesmo papel (ex.: 🔨 e 🌐), e os
    itens da fora do padrão ficam invisíveis para os hooks" · **Não mexer agora**.
    Ajustar: `status-projeto status-md --ajustar "🔨 Em execução=🌐" [--ajustar "Título=✅" ...] --marcar` (troca o
    título, junta os itens na fase padrão sem perder nenhum, põe as 5 na ordem e acrescenta as que faltam; o resto
    do arquivo fica igual). Mostre o `git diff STATUS.md`.
    Só acrescentar: `status-projeto status-md --completar-fases --marcar`.
  - **Só faltam fases** (`fases_faltando` não vazio, sem `fases_extras`): pergunte
    **Acrescentar as fases que faltam (Recomendado)** — motivo: "as regras e os hooks contam com as 5; nada do que
    existe é mexido" · **Não mexer agora**. Sim → `status-projeto status-md --completar-fases --marcar`.
  - Já tem as 5 e nada fora do padrão: `status-projeto status-md --marcar`.
- **Projeto existente sem STATUS.md**: analise o código e o git e **escreva o STATUS.md** no formato do template
  (`${CLAUDE_PLUGIN_ROOT}/templates/STATUS.md`):
  - Fontes: `git log --all --date=short --format='%ad %h %s'` (e `--stat` onde precisar), branches e tags, arquivos
    da pasta de fatias (e fatias soltas na raiz), relatórios, README/CHANGELOG/TODO e o próprio código (o que existe
    de verdade, o que está pela metade, testes).
  - Cada item com `(desde DD/MM)` tirado do git (data do commit que o colocou na fase: criação da fatia → 📦; último
    commit da fatia sem conclusão → 🌐; relatório/commit de conclusão → ✅). Sem como comprovar: `(desde ?)`.
    Fato incerto: acrescente `(?)`.
  - 🌐 com `Parei em:` / `Próximo passo:` / `Pendente:` (no máximo 3). 📦 com `[P]/[M]/[G]` (use as horas da
    estimativa do passo 4 quando houver; senão o tamanho do escopo) e na ordem de execução provável. ⏸️ com motivo.
  - Formato de cada item (uma linha, tamanho no começo, data no fim; detalhes em subitens):
    `- [M] FATIA_NOME — o que é (desde 05/10)` ou `` - [P] `fatias/FATIA_NOME.md` — o que é (desde ?) ``.
  - Mostre o STATUS.md ao usuário e grave. Depois `status-projeto status-md --marcar` (ele mostra avisos de formato:
    corrija o que for seu).

## Passo 3b — contradições nas fatias em 📦 (projeto existente; também no Atualizar)
Pule em projeto novo. Com o STATUS.md já gravado, rode `status-projeto contradicoes`. Ele lê o arquivo de cada fatia em
📦 e aponta linhas que contradizem as regras do plugin: **onde arquivar** (a fatia e o relatório vão com `git mv` para a
pasta das executadas, nunca apagados nem para outra pasta), **.gitignore** (STATUS.md, CLAUDE.md, `docs/tempo/`, o
guia, o config e as pastas de fatias vão para o git), **onde gerar o relatório** (junto da fatia, na pasta das fatias)
e **status fora do STATUS.md** (TODO.md, PROGRESSO.md...).
- Código 0 → diga em uma linha que nenhuma fatia contradiz as regras (e cite as `sem arquivo`, se houver).
- Código 3 → mostre a lista **inteira** (arquivo:linha, trecho, regra, correção). A detecção é por padrão de texto:
  leia cada trecho no contexto da fatia e descarte (dizendo que descartou) o que não for instrução de verdade.
  Pergunte (AskUserQuestion): **Corrigir todas (Recomendado)** — motivo: "na hora de executar, o Claude segue a
  instrução da fatia, então ela faria o contrário da regra" · **Escolher quais** · **Marcar como ignorado (falso
  positivo)** · **Não corrigir agora**. Se você mesmo achar que algum apontamento é falso positivo, diga qual e por
  quê antes da pergunta, e aí recomende **Escolher quais** — motivo: "N parecem falso positivo". Falso positivo (seu ou do usuário) → `status-projeto contradicoes --ignorar ID --obs "motivo"`
  (o id aparece no começo de cada apontamento; fica em `contradicoes_ignoradas` no config e não volta nas próximas
  rodadas, enquanto o texto da linha não mudar). `--ignoradas` lista; `--desfazer ID` faz voltar a valer.
  Só com o sim, edite **apenas aquelas linhas** de cada fatia para seguir a regra (sem reescrever o resto),
  mostre o `git diff` das fatias e rode `status-projeto contradicoes` de novo para confirmar. Não faça commit.

## Passo 4 — etapa `estimativa`
`status-projeto estimar`. Grava `docs/tempo/estimativa_git.csv` uma vez só ("estimado antes da instalação": sessões
com mais de 2 h entre commits, +30 min antes do primeiro commit). Se o comando disser que já existe, aceite — não refaça.

## Passo 5 — etapa `claude_md`
`status-projeto claude-md`. Se sair com código 3 (regras antigas de status/tempo fora do bloco), mostre as seções
achadas e pergunte (AskUserQuestion): **Trocar as antigas pelo bloco do plugin (Recomendado)** — motivo: "duas regras
de status no CLAUDE.md se contradizem e o Claude pode seguir a antiga" (aí você mesmo remove do CLAUDE.md só aquelas
seções, mostra o diff e roda de novo) · **Gravar o bloco mesmo assim** (`--mesmo-assim`) — descrição: "as duas
regras ficam valendo" · **Pular**. Se alguma seção achada tiver regra que não é de status/tempo (ex.: convenção de
commit), diga que ela fica e que você só tira a parte de status.

## Passo 6 — etapa `hooks`
`status-projeto hooks`. Os hooks vêm do próprio plugin; o comando registra o plugin no `.claude/settings.json` do
projeto (para quem abrir o repo, inclusive no Claude Code na web). Se avisar de **hooks manuais antigos**, mostre e
pergunte (AskUserQuestion): **Tirar os hooks antigos (Recomendado)** — motivo: "a mesma sessão seria contada duas vezes
no relatório" · **Manter**. Só edite com o sim. Se o hook antigo fizer mais coisa além de medir tempo, não recomende:
diga que depende de o usuário ainda precisar dessa outra função e proponha tirar só a parte do tempo.

## Passo 7 — etapas `gitattributes` e `gitignore`
`status-projeto gitattributes`, depois `status-projeto gitignore` (ele já ignora sozinho a trava e o estado local,
que é seguro). Se apontar arquivos do status que estão ignorados, mostre e pergunte (AskUserQuestion), a não ser que
os argumentos já digam que pode corrigir: **Corrigir o .gitignore (Recomendado)** — motivo: "o claude.ai lê o
status pelo GitHub, e arquivo ignorado não sobe" · **Não corrigir**. Sim → `status-projeto gitignore --corrigir`. Se continuar com problema (pasta-mãe inteira ignorada),
explique a linha que precisa mudar e pergunte antes de editar.

## Passo 8 — etapa `guia` e fechamento (sempre, também em continuar/reparar/atualizar/verificar)
0. Rode `status-projeto github`. Ele lê o DONO/REPO do remote (`origin`, ou o único remote; aceita qualquer host antes
   dos dois-pontos, inclusive apelidos do `~/.ssh/config` como `git@github-zapai:Dono/repo.git`). Se sair com
   **código 4** (não deu para saber), **pergunte ao usuário** (AskUserQuestion, com o remote mostrado na mensagem como
   contexto; só ele sabe, então sem recomendada) qual é o repositório no GitHub no formato `DONO/REPO` e grave com `status-projeto github DONO/REPO`.
   **Nunca** escreva `<dono>` nem invente o dono. O `guia` e o `atualizar` também param com código 4 / aviso se faltar.
1. `status-projeto guia --gravar --marcar` (regrava o guia com a lista de (?) atual; sem `--gravar` só mostra) grava `docs/COMO_USAR_STATUS.md` e imprime o bloco **"⚠️ ATENÇÃO — LEIA ANTES DE
   COMEÇAR"**. Mostre esse bloco **inteiro** ao usuário, sem resumir (ele já traz como funciona, frases, comandos,
   fases, os passos manuais com o texto das instruções do claude.ai com o nome do repo, a frase de teste e os itens (?)).
2. Mostre `git status --short` com o que a instalação criou/alterou e diga: "para eu fazer commit e push, escreva
   **pode commitar**". Só com essa frase: `git add` dos arquivos da instalação (STATUS.md, CLAUDE.md, .gitattributes,
   .gitignore, .claude-status/config.json, .claude/settings.json, docs/tempo/, docs/COMO_USAR_STATUS.md), commit
   `chore(status): instala o status-projeto` e push (se houver remote).
