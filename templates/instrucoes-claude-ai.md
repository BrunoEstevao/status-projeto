Este projeto acompanha o repositório GitHub {{repo_github}} (conectado pelo GitHub).
O status do projeto fica SOMENTE no arquivo STATUS.md, na raiz do repositório. Nenhum outro arquivo vale como status.
Sempre que eu perguntar sobre andamento, o que fazer agora, o que falta ou o que testar, leia o STATUS.md do repositório
antes de responder. Não invente status e não use a memória de conversas antigas: o que vale é o STATUS.md de agora.
Fases, nesta ordem:
- 🌐 Codando: no máximo 3, com Parei em / Próximo passo / Pendente.
- 📦 Fatia pronta, não iniciada: o primeiro é o próximo.
- 🧪 Aguardando teste: falta {{usuario}} validar.
- ⏸️ Bloqueado: depende de algo externo (com motivo).
- ✅ Concluído: com a data.
Quando planejarmos uma fatia nova, entregue o arquivo FATIA_<NOME>.md pronto, com o tamanho [P] (até 3 h), [M] (3–10 h)
ou [G] (mais de 10 h) no topo, para eu colocar em {{pasta_fatias}}/ e registrar em 📦 pelo Claude Code.
Gravação: você pode gravar SOMENTE em IDEIAS.md e ERROS.md, na raiz do repositório, e só ACRESCENTANDO uma linha no
fim (nunca edite nem apague linha). Faça pull antes e confira que só essa linha mudou antes do push. NUNCA grave no
STATUS.md nem em outro arquivo: quem muda o STATUS.md é o Claude Code.
Quando eu disser "anota a ideia: ..." ou "anota o erro: ...", grave na hora, do jeito que eu disse, sem perguntas:
- IDEIAS.md: - I-AAMMDD-HHMMca | AAAA-MM-DD HH:MM | app | pendente | texto
- ERROS.md: - E-AAMMDD-HHMMca | AAAA-MM-DD HH:MM | app | aberto | normal | incompleto | tela: ? · aparelho: ? · versão: ? | texto
  (grave só se eu disser que é grave; tela, aparelho e versão só se eu disser; com os três ditos, "completo")
O id é a data e hora de agora seguida de "ca"; app é o nome do repositório. Se não conseguir gravar, diga claramente "NÃO GRAVEI" e
mostre a linha pronta, para eu colar no Claude Code com: status-projeto colar "<linha>".
