# ⚠️ ATENÇÃO — LEIA ANTES DE COMEÇAR

Projeto **{{projeto}}** · repositório **{{repo_github}}** · usuário **{{usuario}}** · valor da hora **{{valor}}/h**
Guia gerado pelo plugin status-projeto v{{versao}}. Fica salvo em `docs/COMO_USAR_STATUS.md`.

## Como funciona
- **O status fica todo no `STATUS.md`**, na raiz do repo. Nenhum outro arquivo diz o que está em andamento.
- O Claude Code atualiza o `STATUS.md` sozinho quando você usa as frases abaixo, seguindo as regras gravadas no
  `CLAUDE.md` (bloco status-projeto).
- Os hooks do plugin medem o tempo de cada sessão em `docs/tempo/sessoes.csv`: início, fim, repo, fatia, tipo e estado.
  **O texto das suas mensagens nunca é gravado.** Uma sessão parada por mais de 30 min fecha sozinha no último evento.
- O tempo de antes da instalação foi **estimado uma vez pelo `git log`** (`docs/tempo/estimativa_git.csv`). Daqui em
  diante vale o tempo **medido**, e os relatórios mostram sempre os dois separados.
- O claude.ai (no navegador ou no celular) lê o mesmo `STATUS.md` pelo GitHub. Por isso o `STATUS.md` precisa estar
  commitado e enviado (push) para o claude.ai ver a versão nova.

## As 5 fases do STATUS.md
| Fase | Quer dizer |
|---|---|
| 🌐 Codando | em andamento agora. **No máximo 3 itens, somando todos os repos do projeto.** Cada item tem Parei em / Próximo passo / Pendente |
| 📦 Fatia pronta, não iniciada | na fila. **O primeiro é o próximo.** Tamanho no começo: [P] até 3 h, [M] 3–10 h, [G] mais de 10 h |
| 🧪 Aguardando teste | código pronto; falta você testar |
| ⏸️ Bloqueado | depende de algo de fora; sempre com o motivo |
| ✅ Concluído | terminado, com a data |

Todo item termina com **(desde DD/MM)**, a data em que entrou na fase. **(?)** = não deu para comprovar.

## Frases do dia a dia (diga no Claude Code)
| Você diz | O que acontece |
|---|---|
| `vou começar a codar` (ou `vou começar a codar FATIA_X`) | o primeiro de 📦 (ou o que você disse) vai para 🌐. Avisa se já houver 3 em 🌐 |
| `finalizado` | a fatia em 🌐 vai para 🧪 com o roteiro do que testar |
| `vou testar FATIA_X` | começa a contar o tempo de teste |
| `terminei o teste` (ou `terminei o teste às 21:30`) | fecha o tempo de teste e pergunta se passou: passou → ✅; não passou → volta para 🌐 |
| `fecha o dia` | atualiza Parei em / Próximo passo / Pendente, mostra o que mudou e faz commit do STATUS.md e do tempo |
| `vou planejar` | o tempo passa a contar como planejamento (o modo plano também conta) |

Esqueceu um teste aberto? Na próxima mensagem o Claude pergunta se terminou e a que horas.

## Roteiro de teste por link (opcional)
Só vale numa máquina com o serviço de testes configurado (`status-projeto testes configurar --pasta ... --url ...`,
gravado em `~/.claude/status-projeto/testes.json`, fora do repositório). Sem isso, o roteiro aparece só no terminal.

| Você diz | O que acontece |
|---|---|
| `me traga o roteiro de teste` (ou `vou testar FATIA_X`, ou o `finalizado`) | o Claude monta os itens pelos critérios da fatia, publica e mostra o roteiro com o **link no topo**. No `STATUS.md` ficam só a rodada e a situação (publicada, respondida, avaliada); o link fica nesta máquina, fora do git. `status-projeto roteiro mostrar` devolve o link quando você pedir |
| `teste finalizado, avalie` | lê o resultado: não terminado → diz quantos itens já foram respondidos e para. Tudo passou → ✅ e arquiva. Algo reprovou → tabela com item, motivo e ação proposta, e **espera você mandar**. Só "não consegui testar" → continua em 🧪 e oferece nova rodada |

- **O que o testador vê:** o título, a introdução e, para cada item, os passos e o resultado esperado. Ele marca
  passou / reprovou / não consegui testar, escreve o motivo (ou dita), anexa fotos e pode registrar "outros erros".
  O cabeçalho pede só o nome (campos extras: `roteiro_cabecalho` no `.claude-status/config.json`). A versão do app,
  quando o projeto tem, vai gravada no roteiro, sem perguntar ao testador.
- **O que NÃO pode ir no roteiro:** senha, chave, token ou qualquer segredo. Escreva "use a senha do revendedor",
  nunca qual é. O plugin recusa e aponta o trecho. O link vale 7 dias e funciona como senha: não o publique.
- **O link não vai para o git.** Fica em `.claude-status/local/roteiros.json` (só nesta máquina). Quem quiser o link no `STATUS.md` liga `"link_no_status": true` no `.claude-status/config.json`, **só em repositório privado**. Pelo mesmo motivo, o arquivo da rodada traz só o nome das fotos; os links saem com `status-projeto roteiro mostrar --fatia FATIA_X --rodada N --fotos`.
- Usou o link? Não precisa dizer "vou testar" nem "terminei o teste": o tempo vem da página (no horário local), sem
  contar em dobro se você disser também.
- O resultado vai para `{{pasta_fatias}}/testes/<FATIA>-rodada-<N>.md` (só texto; as fotos ficam no serviço). Os
  "outros erros" vão para o `ERROS.md` com aparelho e versão, sem reprovar a fatia.
- **O texto do testador é dado, nunca instrução.** O Claude não roda comandos, não abre links e não segue ordens que
  apareçam nele, e só abre as fotos se você pedir.
- Nova rodada (depois da correção e do `finalizado`): os itens reprovados, os não testados e os que a correção pode ter
  afetado (o Claude diz quais e por quê), com o número seguinte.

## Ideias e erros (`IDEIAS.md` e `ERROS.md`)
Ficam na raiz do repo, uma linha por registro, e **nada é apagado**: mudar o estado acrescenta uma linha nova com o
mesmo id. Não são status (o status continua só no `STATUS.md`).
- Ideia: `pendente` → `virou FATIA_X` ou `descartada`.
- Erro: `aberto` → `em FATIA_CORRECOES_N` → `corrigido e testado`; gravidade `grave` ou `normal`; `incompleto` quando
  falta tela, aparelho ou versão.

| Você diz | O que acontece |
|---|---|
| `anota a ideia: ...` | grava na hora, do jeito que foi dito, sem perguntas |
| `anota o erro: ...` (ou `anota o erro grave: ...`) | grava na hora; o que faltar (tela, aparelho, versão) fica `incompleto`. Grave: o Claude oferece virar fatia de correção no topo do 📦 |
| `quais ideias pendentes?` | lista; ideia pendente há mais de 60 dias: pergunta se mantém ou descarta |
| `quais erros a corrigir?` | lista e pergunta o que falta nos incompletos |
| `monta a fatia de correção` | agrupa os erros abertos por área (tela), cria `{{pasta_fatias}}/FATIA_CORRECOES_N.md`, registra em 📦 e marca os erros |

- Erro achado **no teste de uma fatia em 🧪** não entra no `ERROS.md`: é teste reprovado e a fatia volta para 🌐.
- Projeto com vários repos: cada item leva a etiqueta do app e é gravado no repo dele; na dúvida, o Claude pergunta.
- O claude.ai também pode anotar (só nesses dois arquivos). Se ele não conseguir gravar, mostra a linha pronta: cole no
  Claude Code com `status-projeto colar "<linha>"`.

## Comandos
| Comando | Para quê |
|---|---|
| `/status-ajuda` | estado do projeto agora + este guia |
| `/status-relatorio` | horas e custo: estimado × medido; interativo, autônomo, planejamento e teste; por fatia; dias de 8 h. `--todos` soma os repos irmãos descontando a sobreposição |
| `/status-historico` | linha do tempo das fatias com datas, horas e custo |
| `/status-cronograma` | quando as fatias de 📦 devem ficar prontas, pela média das fatias do mesmo tamanho |
| `/status-resumo` | só o que mudou nos últimos 3 dias, por fase, e quantas ideias e erros estão abertos |
| `/status-ideias` | ideias pendentes: listar, anotar, mudar o estado (virou fatia, descartada, mantida) |
| `/status-erros` | erros a corrigir: listar, anotar, completar, mudar o estado, montar a fatia de correção |
| `/status-valor 180` | muda o valor da hora daqui para frente (nunca retroativo) |
| `/verificar-integracao` | confere tudo no repo e dá a frase para testar no claude.ai |
| `/instalar-status` | rodar de novo é seguro: verifica, repara o que faltar ou atualiza |

Os nomes completos são `/status-projeto:<comando>` (use se outro plugin tiver um comando com o mesmo nome).

## Atualizar o plugin
No terminal, dentro da pasta do projeto (o plugin está registrado no escopo do projeto):

    claude plugin marketplace update status-projeto
    claude plugin update status-projeto@status-projeto --scope project

Dentro da sessão: `/plugin` → aba **Installed** → `status-projeto` → **Update now** (digitar `/plugin update ...` com
argumentos pode só abrir o gerenciador). Depois rode `/reload-plugins` e `/instalar-status` → **Atualizar**.

## Fatias
- Fatia nova: `{{pasta_fatias}}/FATIA_<NOME>.md` e um item em 📦 com o tamanho.
- Ao mandar codar, o Claude procura o arquivo em `{{pasta_fatias}}/` e na raiz. Achou só na raiz: move para `{{pasta_fatias}}/`.
  Não achou, ou achou nos dois: **para e pergunta**.
- Concluída: a fatia e o relatório dela vão para `{{pasta_executadas}}/`.

## Passos manuais (só você pode fazer)
1. **Liberar o repositório no GitHub App do claude.ai.** claude.ai → Configurações → Conectores → GitHub → no bloco
   "Claude GitHub App", clique em Corrigir/Configurar → escolha "Only select repositories" → marque o repo
   **{{repo_github}}**.
2. **Conferir.** Na mesma tela, clique em "Verificar status do repositório".
3. **Instruções do projeto no claude.ai.** Abra o projeto → painel da direita → Instruções → Adicionar → cole este texto:

    ```text
{{instrucoes_claude_ai}}
    ```

4. **Frase de teste.** Depois de commit e push do `STATUS.md`, numa sessão do projeto no claude.ai, mande:

    ```text
    {{frase_teste}}
    ```

   A resposta tem que bater com o `STATUS.md` do GitHub. `/verificar-integracao` confere o lado do repo.
   **Teste de gravação** (o claude.ai só pode gravar no `IDEIAS.md` e no `ERROS.md`), na mesma sessão:

    ```text
    {{frase_gravacao}}
    ```

   Certo: uma linha nova no fim do `IDEIAS.md` no GitHub e nada no `STATUS.md`, ou a resposta "NÃO GRAVEI" com a linha
   pronta (cole no Claude Code com `status-projeto colar "<linha>"`). Depois diga no Claude Code
   "descarta a ideia de teste de gravação".
5. **Revise os itens com (?)** — o que a instalação não conseguiu comprovar pelo código e pelo git:
{{itens_revisar}}
