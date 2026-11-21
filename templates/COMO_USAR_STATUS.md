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

## Comandos
| Comando | Para quê |
|---|---|
| `/status-ajuda` | estado do projeto agora + este guia |
| `/status-relatorio` | horas e custo: estimado × medido; interativo, autônomo, planejamento e teste; por fatia; dias de 8 h. `--todos` soma os repos irmãos descontando a sobreposição |
| `/status-historico` | linha do tempo das fatias com datas, horas e custo |
| `/status-cronograma` | quando as fatias de 📦 devem ficar prontas, pela média das fatias do mesmo tamanho |
| `/status-resumo` | só o que mudou nos últimos 3 dias, por fase |
| `/status-valor 180` | muda o valor da hora daqui para frente (nunca retroativo) |
| `/verificar-integracao` | confere tudo no repo e dá a frase para testar no claude.ai |
| `/instalar-status` | rodar de novo é seguro: verifica, repara o que faltar ou atualiza |

Os nomes completos são `/status-projeto:<comando>` (use se outro plugin tiver um comando com o mesmo nome).

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

{{instrucoes_claude_ai}}

4. **Frase de teste.** Depois de commit e push do `STATUS.md`, numa sessão do projeto no claude.ai, mande:

    {{frase_teste}}

   A resposta tem que bater com o `STATUS.md` do GitHub. `/verificar-integracao` confere o lado do repo.
5. **Revise os itens com (?)** — o que a instalação não conseguiu comprovar pelo código e pelo git:
{{itens_revisar}}
