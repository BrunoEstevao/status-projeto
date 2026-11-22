---
name: verificar-integracao
description: Confere toda a instalação do status-projeto no repo (config, STATUS.md, CLAUDE.md, hooks gravando, .gitattributes, .gitignore, guia, GitHub e, quando existe, a configuração do serviço de testes) e entrega a frase para testar no claude.ai.
allowed-tools: Bash(status-projeto *)
---
Rode `status-projeto verificar`. **Antes de tudo**, se o começo da saída disser "ATENÇÃO: N instalações valendo ao
mesmo tempo", diga isso primeiro, em uma linha, com os comandos que ela traz para o usuário rodar no terminal (ou com
`!` na frente). **Não desinstale nem atualize o plugin você mesmo.** Depois mostre a saída inteira num bloco de código (cada item com ✅ ou ❌ e a frase de
teste do claude.ai, de leitura e de gravação). Para cada ❌, diga em uma linha como resolver; se for algo da instalação, ofereça
/instalar-status → Reparar. Commit/push do STATUS.md só com "pode commitar".
Lembre os passos manuais que só o usuário faz (estão em `docs/COMO_USAR_STATUS.md`, "Passos manuais"): liberar o repo
no GitHub App do claude.ai e colar as instruções do projeto.
