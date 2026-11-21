#!/usr/bin/env python3
"""Hook de tempo do status-projeto.

Chamado por hooks/hooks.json com o nome do evento:
  SessionStart | UserPromptSubmit | PostToolUse | Stop | SessionEnd
Só age em repositório que tenha .claude-status/config.json (instalado com /instalar-status).
Grava em docs/tempo/sessoes.csv do repositório principal (também quando a sessão roda numa worktree):

  inicio,fim,repo,fatia,tipo,sessao,estado

- tipo: autonomo (claude -p / SDK, STATUS_PROJETO_TIPO=autonomo ou processo pai listado em
  "autonomo_processos" no config) | planejamento (modo plano ou "vou planejar") | teste ("vou testar")
  | interativo.
- estado: aberta (Claude esperando o usuário) | ocupada (Claude trabalhando) | fechada.
- Mais de 30 min (config "ocioso_min") sem evento com a sessão parada fecha a linha no último evento.
- O texto das mensagens nunca vai para o CSV: só data/hora, repo, nome da fatia, tipo, id e estado.
Nunca bloqueia o Claude: qualquer erro sai com código 0.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c  # noqa: E402

try:
    import fcntl
except ImportError:  # Windows: sem trava (o merge de duas gravações simultâneas é raro)
    fcntl = None

OCUPADO_MAX = timedelta(hours=3)  # sessão "ocupada" sem evento há 3 h = caiu

RE_TESTAR = re.compile(r"^\s*vou\s+testar\b[\s:,-]*(.*)", re.I | re.S)
RE_TERMINEI = re.compile(r"^\s*(terminei|acabei|finalizei)\s+(o\s+)?teste\b(.*)", re.I | re.S)
RE_CODAR = re.compile(r"^\s*vou\s+come[cç]ar\s+a\s+codar\b[\s:,-]*(.*)", re.I | re.S)
RE_PLANEJAR = re.compile(r"^\s*(vou|vamos)\s+(planejar|projetar)\b", re.I)
RE_FINALIZADO = re.compile(r"^\s*finalizad[oa]\b", re.I)
RE_FECHA_DIA = re.compile(r"^\s*fecha\s+o\s+dia\b", re.I)
ARTIGOS = {"o", "a", "os", "as", "do", "da", "de", "dos", "das", "no", "na", "the", "fatia"}


def autonomo(cfg):
    tipo = os.environ.get("STATUS_PROJETO_TIPO", "").strip().lower()
    if tipo:
        return tipo == "autonomo"
    if os.environ.get("CLAUDE_CODE_ENTRYPOINT", "").startswith("sdk"):
        return True  # claude -p, Agent SDK
    procs = [p for p in cfg.get("autonomo_processos", []) if p]
    if not procs:
        return False
    pid = os.getppid()
    for _ in range(15):
        try:
            cmd = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="replace")
            if any(p in cmd for p in procs):
                return True
            stat = open(f"/proc/{pid}/stat").read()
            pid = int(stat.rsplit(")", 1)[1].split()[1])
            if pid <= 1:
                break
        except Exception:
            break
    return False


def nome_da_fatia(texto, raiz, cwd):
    """Só o nome da fatia (a primeira palavra útil). O resto da mensagem nunca vai para o CSV."""
    m = re.search(r"FATIA_[A-Za-z0-9_]+", texto)
    if m:
        return m.group(0)
    for tok in re.findall(r"[A-Za-z0-9À-ú_.\-/]{2,60}", texto)[:6]:
        if tok.lower() in ARTIGOS:
            continue
        fases, _ = c.ler_status_arquivo(raiz)
        if fases:
            for e in ("🧪", "🌐", "📦", "⏸️", "✅"):
                for it in fases[e]:
                    if c.mesma_fatia(tok, it["nome"]):
                        return it["nome"]
        return tok.strip(".")
    return c.fatia_atual(cwd, raiz)


def hora_dita(texto, inicio, agora):
    """'às 21:30', '21h30', '21h' → a primeira vez que esse horário acontece depois do início do teste
    (e não depois de agora). Sem horário: agora."""
    m = re.search(r"\b(\d{1,2})(?::(\d{2})|h(\d{2})?)\b", texto)
    if not m or int(m.group(1)) > 23:
        return agora
    hh, mm = int(m.group(1)), int(m.group(2) or m.group(3) or 0)
    t = inicio.replace(hour=hh, minute=mm, second=0)
    if t < inicio:
        t += timedelta(days=1)
    return min(t, agora)


def contar_codando(raiz, cfg):
    total, por_repo = 0, []
    for nome, cam in c.repos_do_projeto(raiz, cfg):
        n = len(c.fatias_codando(cam))
        total += n
        if n:
            por_repo.append(f"{nome}: {n}")
    return total, por_repo


def main():
    evento = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        dados = json.load(sys.stdin)
    except Exception:
        dados = {}
    cwd = dados.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    raiz = c.raiz_principal(cwd)
    cfg = c.ler_config(raiz)
    if cfg is None:
        return  # repositório sem o status-projeto instalado
    sid = dados.get("session_id", "")
    modo = dados.get("permission_mode", "")
    prompt = (dados.get("prompt") or "").strip() if evento == "UserPromptSubmit" else ""
    pasta = os.path.join(raiz, c.PASTA_TEMPO)
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(raiz, c.CSV_SESSOES)
    agora = c.agora()
    s_agora = agora.strftime(c.FMT)
    ocioso = timedelta(minutes=float(cfg.get("ocioso_min") or 30))
    repo = os.path.basename(raiz)
    avisos = []

    trava = open(caminho + ".lock", "w")
    try:
        if fcntl:
            fcntl.flock(trava, fcntl.LOCK_EX)
        linhas = c.ler_sessoes(caminho)
        est = c.estado_local(raiz)
        tipos_sessao = est.setdefault("tipo", {})
        perguntou = est.setdefault("perguntou_teste", {})

        # Arrumação: fecha sessões de trabalho que pararam de dar sinal (inclusive as que caíram).
        for l in linhas:
            if l["tipo"] == "teste" or l["estado"] == "fechada" or l["sessao"] == sid:
                continue
            fim = c.para_dt(l["fim"])
            if fim is None:
                continue
            parado = agora - fim
            if (l["estado"] == "aberta" and parado > ocioso) or parado > OCUPADO_MAX:
                l["estado"] = "fechada"

        # Tipo desejado desta sessão.
        atual = tipos_sessao.get(sid, {})
        if autonomo(cfg):
            desejado = {"tipo": "autonomo", "origem": "auto"}
        elif modo == "plan":
            desejado = {"tipo": "planejamento", "origem": "modo"}
        elif prompt and RE_PLANEJAR.match(prompt):
            desejado = {"tipo": "planejamento", "origem": "frase"}
        elif prompt and RE_CODAR.match(prompt):
            desejado = {"tipo": "interativo", "origem": ""}
        elif atual.get("origem") == "modo" and modo:
            desejado = {"tipo": "interativo", "origem": ""}  # saiu do modo plano
        else:
            desejado = atual or {"tipo": "interativo", "origem": ""}
        if sid:
            tipos_sessao[sid] = desejado

        # Linha de trabalho desta sessão.
        minha = next((l for l in linhas if l["sessao"] == sid and l["estado"] != "fechada"
                      and l["tipo"] != "teste"), None) if sid else None
        if minha:
            parado = agora - (c.para_dt(minha["fim"]) or agora)
            if (minha["estado"] == "aberta" and parado > ocioso) or parado > OCUPADO_MAX:
                minha["estado"] = "fechada"  # fecha no último evento; a próxima linha começa agora
                minha = None
            elif minha["tipo"] != desejado["tipo"]:
                minha["fim"], minha["estado"] = s_agora, "fechada"  # mudou o tipo: nova linha
                minha = None
        if sid and evento != "SessionEnd":
            if not minha:
                minha = {"inicio": s_agora, "fim": s_agora, "repo": repo, "fatia": c.fatia_atual(cwd, raiz),
                         "tipo": desejado["tipo"], "sessao": sid, "estado": "aberta"}
                linhas.append(minha)
            minha["fim"] = s_agora
            minha["estado"] = "ocupada" if evento in ("UserPromptSubmit", "PostToolUse") else "aberta"
            if not minha["fatia"]:  # 🌐 pode ter sido preenchido no meio da sessão
                minha["fatia"] = c.fatia_atual(cwd, raiz)
        elif minha:  # SessionEnd
            minha["fim"], minha["estado"] = s_agora, "fechada"
        if evento == "SessionEnd" and sid:
            tipos_sessao.pop(sid, None)
            perguntou.pop(sid, None)

        teste = next((l for l in linhas if l["tipo"] == "teste" and l["estado"] != "fechada"), None)
        usuario = cfg.get("usuario") or "o usuário"

        if evento == "SessionStart" and teste:
            avisos.append(f"[status-projeto] Há um teste aberto desde {c.data_br(teste['inicio'])} "
                          f"('{teste['fatia']}'). Na primeira resposta, pergunte a {usuario} se o teste terminou "
                          "e a que horas (a resposta é 'terminei o teste às HH:MM').")
            if sid:
                perguntou[sid] = teste["inicio"]
        if evento == "SessionStart":
            pend = [e for e in c.ETAPAS if e not in cfg.get("etapas", {})]
            if pend:
                avisos.append("[status-projeto] A instalação não terminou (faltam: " + ", ".join(pend)
                              + "). Sugira rodar /instalar-status para continuar de onde parou.")

        if evento == "UserPromptSubmit" and prompt:
            m_ini, m_fim = RE_TESTAR.match(prompt), RE_TERMINEI.match(prompt)
            if m_ini:
                if teste:
                    teste["fim"], teste["estado"] = s_agora, "fechada"
                nome = nome_da_fatia(m_ini.group(1), raiz, cwd)
                linhas.append({"inicio": s_agora, "fim": "", "repo": repo, "fatia": nome,
                               "tipo": "teste", "sessao": "teste", "estado": "aberta"})
                avisos.append(f"[status-projeto] Teste de '{nome}' começou às {agora:%H:%M} (docs/tempo/sessoes.csv). "
                              "Siga a regra 'vou testar' do CLAUDE.md e confirme em uma linha.")
            elif m_fim and teste:
                ini = c.para_dt(teste["inicio"]) or agora
                fim = hora_dita(m_fim.group(3), ini, agora)
                teste["fim"], teste["estado"] = fim.strftime(c.FMT), "fechada"
                h = (fim - ini).total_seconds() / 3600
                avisos.append(f"[status-projeto] Teste de '{teste['fatia']}' fechado às {fim:%H:%M} ({h:.1f} h). "
                              "Siga a regra 'terminei o teste' do CLAUDE.md (pergunte se passou).")
            elif m_fim:
                avisos.append("[status-projeto] Não há teste aberto em docs/tempo/sessoes.csv. Avise em uma linha.")
            elif teste and perguntou.get(sid) != teste["inicio"]:
                avisos.append(f"[status-projeto] Há um teste aberto desde {c.data_br(teste['inicio'])} "
                              f"('{teste['fatia']}'). Antes de responder, pergunte a {usuario} se o teste terminou e "
                              "a que horas (a resposta é 'terminei o teste às HH:MM'). Pergunte só esta vez.")
                if sid:
                    perguntou[sid] = teste["inicio"]

            if RE_CODAR.match(prompt):
                total, por_repo = contar_codando(raiz, cfg)
                msg = f"[status-projeto] Itens em 🌐 Codando agora, somando os repos do projeto: {total}"
                msg += f" ({', '.join(por_repo)})." if por_repo else "."
                if total >= 3:
                    msg += " Já está no máximo de 3: avise e pergunte qual sai antes de abrir outro."
                avisos.append(msg + " Siga a regra 'vou começar a codar' do CLAUDE.md.")
            elif RE_FINALIZADO.match(prompt):
                avisos.append("[status-projeto] Siga a regra 'finalizado' do CLAUDE.md (bloco status-projeto).")
            elif RE_FECHA_DIA.match(prompt):
                avisos.append("[status-projeto] Siga a regra 'fecha o dia' do CLAUDE.md (bloco status-projeto).")

        c.gravar_sessoes(caminho, linhas)
        c.gravar_estado_local(raiz, est)
    finally:
        trava.close()

    if avisos and evento in ("SessionStart", "UserPromptSubmit"):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": evento,
                                                 "additionalContext": "\n".join(avisos)}}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        if os.environ.get("STATUS_PROJETO_DEBUG"):
            raise
    sys.exit(0)
