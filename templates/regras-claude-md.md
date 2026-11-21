<!-- status-projeto:inicio v{{versao}} — bloco gravado pelo /instalar-status; não edite à mão entre as marcas (o /instalar-status → atualizar regrava) -->
## Regra de status (plugin status-projeto)
- **Status só no `STATUS.md`.** Nenhum outro arquivo diz o que está codando, pendente, em teste ou concluído.
  Exceção: arquivo lido por código, listado na seção "Exceções à regra de status" deste CLAUDE.md (fora deste bloco).
- Fases do `STATUS.md`, nesta ordem:
  - 🌐 **Codando** — no máximo **3 itens, somando todos os repos do projeto**. Cada item tem três subitens:
    `Parei em:` / `Próximo passo:` / `Pendente:`. Se for abrir um 4º, avise {{usuario}} e pergunte qual sai antes.
  - 📦 **Fatia pronta, não iniciada** — a ordem é a ordem de execução: **o primeiro é o próximo**. Todo item começa com
    o tamanho `[P]` (até 3 h), `[M]` (3–10 h) ou `[G]` (mais de 10 h), pelo histórico de horas.
  - 🧪 **Aguardando teste** — código pronto; falta {{usuario}} validar.
  - ⏸️ **Bloqueado** — depende de algo externo; sempre com o motivo.
  - ✅ **Concluído** — só título e a data em que concluiu.
- Todo item, em qualquer fase, termina com a data em que entrou na fase atual: `(desde DD/MM)`. Ao mover de fase, troque
  pela data do dia. Data que não dá para comprovar pelo `git log`: `(desde ?)`; fato que não dá para comprovar: `(?)`.
- O tamanho `[P]/[M]/[G]` acompanha o item em todas as fases (é ele que alimenta o `/status-cronograma`).
- {{repos_irmaos}}

### Frases do dia a dia (gatilhos)
- **"vou começar a codar [fatia]"** — sem nome, é o primeiro de 📦. Confira o limite de 3 em 🌐 (o hook informa o total
  dos repos). Procure o arquivo da fatia (regra das pastas, abaixo), mova o item para 🌐 com `(desde DD/MM)` de hoje e
  preencha `Parei em:` / `Próximo passo:` / `Pendente:`.
- **"finalizado"** — o código da fatia em 🌐 ficou pronto: mova para 🧪 com a data de hoje, com o roteiro de teste
  curto (o que {{usuario}} precisa conferir). Mostre o que mudou no `STATUS.md`.
- **"vou testar [fatia]"** — o hook abre o tempo de teste. Se o item não estiver em 🧪, mova para lá. Confirme em uma linha.
- **"terminei o teste [às HH:MM]"** — o hook fecha o tempo de teste. Pergunte se passou: passou → ✅ com a data de hoje
  (e a fatia vai para `{{pasta_executadas}}/`); não passou → volta para 🌐 com o que falhou em `Pendente:`.
- **Teste aberto e esquecido** — se o hook avisar que há teste aberto, pergunte **uma vez** se terminou e a que horas.
- **"fecha o dia"** (e ao fim de toda sessão) — atualize `Parei em` / `Próximo passo` / `Pendente` de cada item em 🌐,
  confira datas e fases, mostre o que mudou e faça commit do `STATUS.md` e de `docs/tempo/` (e push, se houver remote).
- **"vou planejar"** / modo plano — o tempo conta como planejamento até "vou começar a codar".

### Ideias e erros (`IDEIAS.md` e `ERROS.md`, na raiz de cada repo)
- Não são status (o status continua só no `STATUS.md`). Uma linha por registro, **sempre acrescentada no fim; nada é
  apagado** nem editado: mudar o estado é acrescentar uma linha com o mesmo id (vale a última). Grave **só pelo
  `status-projeto`** (`ideia`/`erro`), nunca à mão.
- **"anota a ideia: ..."** — grave na hora, do jeito que foi dito, **sem perguntas**:
  `status-projeto ideia anotar "<texto>"`. Confirme em uma linha.
- **"anota o erro: ..."** — grave na hora, do jeito que foi dito, **sem perguntas**:
  `status-projeto erro anotar "<texto>" [--grave] [--tela X] [--aparelho Y] [--versao Z]` (só o que foi dito; `--grave`
  só se {{usuario}} disse que é grave ou que impede o uso). O que faltar de tela, aparelho ou versão fica `incompleto` e
  é perguntado quando a lista for pedida.
  - **Erro achado no teste de uma fatia em 🧪 não entra no `ERROS.md`**: é teste reprovado e a fatia volta para 🌐 com
    o erro em `Pendente:`. O comando recusa (código 3) quando há teste aberto; `--fora-do-teste` só se o erro não for
    daquela fatia.
  - **Erro grave** → ofereça na hora virar fatia de correção no topo do 📦 (`status-projeto erro fatia --ids ID`,
    mostre a prévia e, com o sim, `--gravar`).
- **"quais ideias pendentes?"** — `status-projeto ideia listar`. Ideia pendente há mais de 60 dias: pergunte se mantém
  (`ideia estado ID --para pendente`) ou descarta (`--para descartada`). Virou fatia: `--para "virou FATIA_X"`.
- **"quais erros a corrigir?"** — `status-projeto erro listar`. Para cada erro `incompleto`, pergunte o que falta e
  grave com `status-projeto erro completar ID --tela ... --aparelho ... --versao ...`.
- **"monta a fatia de correção"** — `status-projeto erro fatia` (prévia: agrupa os erros abertos por área/tela). Mostre,
  e com o sim rode com `--gravar`: cria `{{pasta_fatias}}/FATIA_CORRECOES_N.md`, registra em 📦 (no topo se houver erro
  grave) e marca os erros `em FATIA_CORRECOES_N`. Quando essa fatia passar no teste (✅):
  `status-projeto erro estado --fatia FATIA_CORRECOES_N --para corrigido` (fica `corrigido e testado`).
- {{listas_repos}}
- Linha colada do claude.ai (começa com `- I-` ou `- E-`): `status-projeto colar "<linha>"` (grava como veio).

### Fatias: onde ficam e como andam
1. Fatia nova: criar em `{{pasta_fatias}}/FATIA_<NOME>.md` e registrar em 📦 no `STATUS.md`, na posição da ordem de
   execução, com o tamanho `[P]/[M]/[G]`.
2. **Ao mandar codar uma fatia**, procurar o arquivo em `{{pasta_fatias}}/` **e** na raiz do repo:
   - só em `{{pasta_fatias}}/` → seguir;
   - só na raiz → `git mv` para `{{pasta_fatias}}/`, registrar em 📦 (com tamanho) e seguir;
   - **não achou, ou achou nos dois lugares → parar e perguntar** a {{usuario}} antes de qualquer alteração.
3. Ao concluir: `git mv` da fatia **e do relatório dela** de `{{pasta_fatias}}/` para `{{pasta_executadas}}/`, ajustar
   os caminhos no `STATUS.md` e onde mais forem citados, e mover para ✅.

## Tempo e custo (plugin status-projeto)
- Os hooks do plugin gravam cada sessão em `docs/tempo/sessoes.csv` (`inicio,fim,repo,fatia,tipo,sessao,estado`) — **nunca
  o texto das mensagens**. Tipos: `interativo`, `autonomo` (`claude -p`/SDK ou `STATUS_PROJETO_TIPO=autonomo`), `teste`,
  `planejamento`. Mais de 30 min parada sem evento fecha a sessão no último evento.
- O passado foi estimado uma vez pelo `git log` e está em `docs/tempo/estimativa_git.csv` ("estimado antes da
  instalação"); **nunca refazer** essa estimativa. Relatórios mostram sempre estimado e medido separados.
- Valor da hora em `.claude-status/config.json` (`valor_hora`, com histórico). Mudar só pelo `/status-valor`: vale dali
  para frente, nunca retroativo.
- `docs/tempo/sessoes.csv` tem `merge=union` no `.gitattributes`; nunca apagar nem reescrever linhas à mão.
- Comandos: `/status-relatorio`, `/status-historico`, `/status-cronograma`, `/status-resumo`, `/status-ideias`,
  `/status-erros`, `/status-valor`, `/status-ajuda`, `/verificar-integracao`. Guia completo: `docs/COMO_USAR_STATUS.md`.
<!-- status-projeto:fim -->
