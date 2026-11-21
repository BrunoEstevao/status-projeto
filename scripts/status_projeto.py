#!/usr/bin/env python3
"""status-projeto — comandos usados pelas skills do plugin.

Uso: status-projeto <comando> [opções]   (rode sem comando para ver a lista)
Todos os comandos rodam na raiz do repositório principal da pasta atual (ou --raiz DIR).
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c  # noqa: E402
import listas as L  # noqa: E402

TEMPLATES = os.path.join(c.RAIZ_PLUGIN, "templates")
MARCA_INI = "<!-- status-projeto:inicio"
MARCA_FIM = "<!-- status-projeto:fim -->"
GI_INI = "# >>> status-projeto (não edite entre estas marcas)"
GI_FIM = "# <<< status-projeto"
GENERICOS = {
    "deps", "dep", "ci", "cd", "docs", "doc", "chore", "build", "test", "tests", "release", "config", "readme",
    "lint", "format", "style", "wip", "main", "core", "app", "api", "ui", "server", "client", "web", "status",
    "infra", "deploy", "repo", "misc", "geral", "general", "changelog", "version", "versao", "types",
}
# nome de arquivo de status: a palavra em qualquer posição, separada por início/fim, '-', '_', '.' ou espaço
# (ESTADO_ATUAL.md, MINERADOR-STATUS.md, STATUS_LOTE.md); "metodologia" não conta como TODO
NOMES_STATUS = re.compile(r"(?:^|[^a-z0-9])(TODO|ROADMAP|PROGRESSO|PROGRESS|ANDAMENTO|ESTADO|STATUS|PENDENCIAS|"
                          r"PEND[ÊE]NCIAS|BACKLOG|TASKS|TAREFAS)(?=[^a-z0-9]|$)[^/]*\.(md|txt)$", re.I)
NOME_FATIA = re.compile(r"(?:^|[^a-z0-9])(FATIA|SLICE)[_\-][^/]*\.md$", re.I)
PASTAS_PESADAS = {"node_modules", "vendor", "build", "dist", "target", "venv", ".venv", "__pycache__", ".next",
                  ".nuxt", "coverage", ".git"}
MARCAS_STATUS = re.compile(r"(^\s*[-*]\s*\[[ xX]\]|STATUS\s*:|\bem andamento\b|\bconclu[ií]d[oa]\b|\bpendente\b|"
                           r"\bbloquead[oa]\b|\bin progress\b|\bdone\b|✅|🚧|⏳)", re.I)


def sair(msg, codigo=1):
    print(msg, file=sys.stderr)
    sys.exit(codigo)


def ler(caminho, padrao=""):
    try:
        with open(caminho, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return padrao


def escrever(caminho, texto):
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:  # LF também no Windows
        f.write(texto)


def template(nome, valores):
    t = ler(os.path.join(TEMPLATES, nome))
    for k, v in valores.items():
        t = t.replace("{{" + k + "}}", str(v))
    return t


def precisa_config(raiz):
    cfg = c.ler_config(raiz)
    if cfg is None:
        sair("Este repositório ainda não tem o status-projeto. Rode /instalar-status.")
    return cfg


def marcar(raiz, cfg, etapa, valor=None):
    """Marca a etapa como feita; se já estava, mantém a data original (rodar de novo não muda nada)."""
    et = cfg.setdefault("etapas", {})
    if etapa in et and not valor:
        return
    et[etapa] = valor or c.agora_s()
    c.gravar_config(raiz, cfg)


# =================================================================== instalação

def detectar_pastas_fatias(raiz):
    achadas = []
    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("node_modules", "vendor", "build",
                                                                                  "dist", "target", "venv")]
        rel = os.path.relpath(dirpath, raiz)
        if rel.count(os.sep) > 2:
            dirnames[:] = []
            continue
        base = os.path.basename(dirpath).lower()
        n_fatias = sum(1 for f in filenames if re.match(r"(FATIA|SLICE)[_\-].*\.md$", f, re.I))
        if rel != "." and (base in ("fatias", "slices", "fatia") or n_fatias >= 2):
            if not base.endswith(("executadas", "concluidas", "done", "arquivadas")):
                achadas.append({"pasta": rel, "arquivos_fatia": n_fatias})
    na_raiz = sorted(f for f in os.listdir(raiz) if re.match(r"FATIA[_\-].*\.md$", f, re.I))
    achadas.sort(key=lambda a: (-a["arquivos_fatia"], a["pasta"]))
    return achadas, na_raiz


def arquivos_versionados(raiz):
    out = c.git(raiz, "ls-files")
    if out:
        return out.splitlines()
    lst = []
    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "node_modules"]
        lst += [c.rel(os.path.join(dirpath, f), raiz) for f in filenames]
    return lst


def arquivos_do_repo(raiz, exts=(".md", ".txt")):
    """{caminho: situação} dos arquivos com essas extensões: 'versionado', 'fora do git' (nunca adicionado) ou
    'ignorado' (.gitignore ou .git/info/exclude). Sem git: tudo da pasta. Pastas pesadas (node_modules...) ficam fora."""
    def ok(rel):
        partes = rel.split("/")
        return rel.lower().endswith(exts) and not any(p in PASTAS_PESADAS for p in partes[:-1])
    if not c.eh_repo_git(raiz):
        out = {}
        for dirpath, dirnames, filenames in os.walk(raiz):
            dirnames[:] = [d for d in dirnames if d not in PASTAS_PESADAS and not d.startswith(".")]
            for f in filenames:
                rel = c.rel(os.path.join(dirpath, f), raiz)
                if ok(rel):
                    out[rel] = "fora do git"
        return out
    out = {}
    for sit, args in (("versionado", ["ls-files"]), ("fora do git", ["ls-files", "--others", "--exclude-standard"]),
                      ("ignorado", ["ls-files", "--others", "--ignored", "--exclude-standard", "--directory"])):
        for rel in c.git(raiz, *args, timeout=60).splitlines():
            rel = rel.strip().strip('"')
            if rel and not rel.endswith("/") and ok(rel) and rel not in out:
                out[rel] = sit
    return out


def status_espalhado(raiz, cfg=None):
    ignorar = {"STATUS.md", "CHANGELOG.md", c.GUIA, L.ARQ["ideia"], L.ARQ["erro"]}
    pf = (cfg or {}).get("pasta_fatias", "fatias")
    achados = []
    todos = arquivos_do_repo(raiz)
    for rel, situacao in sorted(todos.items()):
        if rel in ignorar or not rel.lower().endswith((".md", ".txt")) or rel.startswith(c.PASTA_CFG):
            continue
        texto = ler(os.path.join(raiz, rel))
        por_nome = bool(NOMES_STATUS.search(os.path.basename(rel)))
        texto = re.sub(re.escape(MARCA_INI) + r".*?" + re.escape(MARCA_FIM), "", texto, flags=re.S)  # bloco do plugin
        if not texto and not por_nome:
            continue
        linhas = [l.strip() for l in texto.splitlines() if MARCAS_STATUS.search(l)]
        if por_nome or len(linhas) >= 3:
            achados.append({"arquivo": rel, "linhas_com_status": len(linhas), "pelo_nome": por_nome,
                            "fatia": rel.startswith(pf + "/") or bool(NOME_FATIA.search(os.path.basename(rel))),
                            "situacao": situacao,
                            "exemplos": [l[:100] for l in linhas[:3]]})
    excecoes = set(excecoes_registradas(raiz))
    lidos = leitores_de(raiz, sorted({os.path.basename(x["arquivo"]) for x in achados if not x["fatia"]}))
    for x in achados:
        x["excecao"] = x["arquivo"] in excecoes
        x["lido_por"] = [] if x["fatia"] else lidos.get(os.path.basename(x["arquivo"]), [])[:5]
    achados.sort(key=lambda a: (a["fatia"], not a["pelo_nome"], -a["linhas_com_status"]))
    return achados


def fatias_fora_da_pasta(raiz, cfg=None):
    """Arquivos FATIA_*.md (também com prefixo, ex.: docs/2026-11-14_FATIA_X.md) fora da pasta das fatias e da
    pasta das executadas, versionados ou não, dizendo se o STATUS.md já cita a fatia pelo nome."""
    pf = c.barra((cfg or {}).get("pasta_fatias", "fatias")).strip("/")
    pe = c.barra((cfg or {}).get("pasta_fatias_executadas", "fatias_executadas")).strip("/")
    status = ler(os.path.join(raiz, "STATUS.md")).lower()
    out = []
    for rel, situacao in sorted(arquivos_do_repo(raiz, (".md",)).items()):
        if not NOME_FATIA.search(os.path.basename(rel)) or rel.startswith((pf + "/", pe + "/")):
            continue
        nome = os.path.basename(rel)[:-3]
        out.append({"arquivo": rel, "situacao": situacao, "na_raiz": "/" not in rel,
                    "citada_no_status": nome.lower() in status,
                    "ultimo_commit": c.git(raiz, "log", "-1", "--format=%ad %s", "--date=short", "--", rel)[:100]})
    # pasta com 3 ou mais fatias fora do lugar = arquivo de fatias antigas: pergunta-se uma vez pela pasta
    por_pasta = collections.Counter(os.path.dirname(x["arquivo"]) for x in out)
    for x in out:
        d = os.path.dirname(x["arquivo"])
        x["grupo"] = d if d and por_pasta[d] >= 3 else ""
    return out


# ------------------------------------------------------------------- scripts que rodam o Claude sozinho

EXT_SCRIPT = (".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".js", ".mjs", ".cjs", ".ts", ".py", ".json", "makefile")
RE_CLAUDE_P = re.compile(r"(?<![\w/.-])claude(?:\.exe|\.cmd)?\s[^\n]*?(?<!\S)(?:-p|--print)(?![\w-])")
RE_CLAUDE_SPAWN = re.compile(r"""['"]claude(?:\.exe|\.cmd)?['"]\s*,\s*\[[^\]]*['"](?:-p|--print)['"]""")
RE_COMENTARIO = re.compile(r"^\s*(#(?!!)|//|rem\s|::|<#)", re.I)
# PowerShell com o caminho do claude numa variável: Start-Process -FilePath $Claude -ArgumentList "-p ..." ou & $Claude -p
RE_PS_INDIRETO = re.compile(r"(Start-Process\b[^\n]*-ArgumentList\b|&\s*\$\w+\s)[^\n]*(?<![\w-])(?:-p|--print)(?![\w-])", re.I)


# definição que vale para o resto do script (VAR=x na frente de um comando vale só para aquele comando)
RE_DEFINE_TIPO = re.compile(r"^\s*(export\s+STATUS_PROJETO_TIPO=|STATUS_PROJETO_TIPO=\S+\s*(;|$)|\$env:STATUS_PROJETO_TIPO\s*=|"
                            r"set\s+\"?STATUS_PROJETO_TIPO=|.*process\.env\.STATUS_PROJETO_TIPO\s*=|"
                            r".*os\.environ\[\s*['\"]STATUS_PROJETO_TIPO['\"]\s*\]\s*=)", re.I)


def chama_claude_p(linha, texto, ext):
    if RE_CLAUDE_P.search(linha) or RE_CLAUDE_SPAWN.search(linha):
        return True
    return ext == ".ps1" and bool(RE_PS_INDIRETO.search(linha)) and bool(re.search(r"\bclaude(\.exe|\.cmd)?\b", texto, re.I))


def chamadas_autonomas(raiz):
    """Linhas de scripts que chamam 'claude -p' / '--print' (ou spawn('claude', ['-p', ...])), dizendo se a chamada
    já leva STATUS_PROJETO_TIPO=autonomo (na linha ou definida antes no arquivo)."""
    out = []
    for rel, situacao in sorted(arquivos_do_repo(raiz, EXT_SCRIPT).items()):
        if rel.startswith(c.PASTA_CFG):
            continue
        texto = ler(os.path.join(raiz, rel))
        linhas = texto.splitlines()
        ext = os.path.splitext(rel)[1].lower()
        definida = None
        for i, l in enumerate(linhas, 1):
            if RE_DEFINE_TIPO.match(l) and not RE_COMENTARIO.match(l) and definida is None:
                definida = i
            if RE_COMENTARIO.match(l) or not chama_claude_p(l, texto, ext):
                continue
            tem = "STATUS_PROJETO_TIPO" in l or (definida is not None and definida < i)
            out.append({"id": f"{rel}:{i}", "arquivo": rel, "linha": i, "trecho": l.strip()[:160], "situacao": situacao,
                        "ja_tem": tem, "aplicavel": ext in (".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd", "")})
    return out


def aplicar_autonomo(raiz, ident):
    rel, _, n = ident.rpartition(":")
    if not rel or not n.isdigit():
        sair(f"Use --aplicar ARQUIVO:LINHA (como aparece na lista). Recebido: {ident}")
    p = os.path.join(raiz, rel)
    texto = ler(p)
    linhas = texto.split("\n")
    i = int(n) - 1
    ext = os.path.splitext(rel)[1].lower()
    if i >= len(linhas) or not chama_claude_p(linhas[i], texto, ext):
        sair(f"{ident}: a linha não tem mais a chamada 'claude -p' (o arquivo mudou?). Rode `status-projeto autonomo`.")
    l = linhas[i]
    recuo = re.match(r"\s*", l).group(0)
    if ext == ".ps1":
        linhas.insert(i, f'{recuo}$env:STATUS_PROJETO_TIPO = "autonomo"')
    elif ext in (".bat", ".cmd"):
        linhas.insert(i, f"{recuo}set STATUS_PROJETO_TIPO=autonomo")
    elif ext in (".sh", ".bash", ".zsh", ""):
        m = RE_CLAUDE_P.search(l)
        antes = l[:m.start()]
        # depois de exec/nohup/sudo/time/xargs a atribuição VAR=x não vale: usa env
        pre = "env STATUS_PROJETO_TIPO=autonomo " if re.search(r"\b(exec|nohup|sudo|time|xargs|nice|timeout)\s+$", antes) \
            else "STATUS_PROJETO_TIPO=autonomo "
        linhas[i] = antes + pre + l[m.start():]
    else:
        sair(f"{ident}: em {ext or 'esse arquivo'} a variável vai no ambiente da chamada (ex.: "
             "env: {...process.env, STATUS_PROJETO_TIPO: 'autonomo'}); edite à mão, com o ok do usuário.")
    escrever(p, "\n".join(linhas))
    return rel


def cmd_autonomo(a):
    raiz = a.raiz
    if a.aplicar:
        for ident in a.aplicar:
            alvo = next((x for x in chamadas_autonomas(raiz) if x["id"] == ident), None)
            if alvo and alvo["ja_tem"]:
                print(f"{ident}: já leva STATUS_PROJETO_TIPO=autonomo; nada mudou.")
                continue
            aplicar_autonomo(raiz, ident)
            print(f"{ident}: STATUS_PROJETO_TIPO=autonomo incluído (mostre o git diff).")
        return
    lst = chamadas_autonomas(raiz)
    if a.json:
        print(json.dumps(lst, ensure_ascii=False, indent=2))
        return
    if not lst:
        print("Nenhum script chama 'claude -p' neste repositório.")
        return
    print("Scripts que rodam o Claude sozinho ('claude -p'):")
    for x in lst:
        st = "✅ já leva STATUS_PROJETO_TIPO=autonomo" if x["ja_tem"] else (
            "falta a variável" + ("" if x["aplicavel"] else " (edite à mão: variável no env da chamada)"))
        print(f"- {x['id']} — {st}" + ("" if x["situacao"] == "versionado" else f" [{x['situacao']}]"))
        print(f"    {x['trecho']}")
    faltam = [x["id"] for x in lst if not x["ja_tem"] and x["aplicavel"]]
    if faltam:
        print("Para incluir: status-projeto autonomo " + " ".join(f"--aplicar {f}" for f in faltam))


def cmd_fatias_soltas(a):
    cfg = c.ler_config(a.raiz) or {}
    lst = fatias_fora_da_pasta(a.raiz, cfg)
    if a.json:
        print(json.dumps(lst, ensure_ascii=False, indent=2))
        return
    if not lst:
        print(f"Nenhum arquivo FATIA_* fora de {cfg.get('pasta_fatias', 'fatias')}/.")
        return
    print(f"Arquivos de fatia fora de {cfg.get('pasta_fatias', 'fatias')}/ (nada foi movido):")
    for x in [x for x in lst if not x["grupo"]]:
        tags = [x["situacao"]] + (["citada no STATUS.md"] if x["citada_no_status"] else ["não está no STATUS.md"])
        print(f"- {x['arquivo']} ({', '.join(tags)})" + (f" — último commit: {x['ultimo_commit']}" if x["ultimo_commit"] else ""))
    for g in sorted({x["grupo"] for x in lst if x["grupo"]}):
        do_g = [x for x in lst if x["grupo"] == g]
        sit = collections.Counter(x["situacao"] for x in do_g)
        print(f"- {g}/: {len(do_g)} arquivos de fatia (" + ", ".join(f"{n} {s}" for s, n in sit.most_common())
              + f"; {sum(x['citada_no_status'] for x in do_g)} citados no STATUS.md) — ex.: "
              + ", ".join(os.path.basename(x["arquivo"]) for x in do_g[:3]))


# ------------------------------------------------------------------- exceções à regra "status só no STATUS.md"

TITULO_EXCECOES = "## Exceções à regra de status (status-projeto)"
EXT_CODIGO = (".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", ".sh", ".bash", ".ps1", ".bat", ".cmd", ".rb",
              ".go", ".php", "package.json", "makefile")


def leitores_de(raiz, nomes):
    """{nome: ['arquivo:linha', ...]} — onde o código cita cada arquivo (ex.: PENDENCIAS.md lido pelo versao:fechar)."""
    nomes = [n for n in nomes if n]
    out = {n: [] for n in nomes}
    if not nomes:
        return out
    res = {n: re.compile(r"(?<![\w.-])" + re.escape(n) + r"(?![\w])") for n in nomes}  # nome inteiro
    for rel in sorted(arquivos_do_repo(raiz, EXT_CODIGO)):
        if rel.startswith(c.PASTA_CFG):
            continue
        for i, l in enumerate(ler(os.path.join(raiz, rel)).splitlines(), 1):
            if RE_COMENTARIO.match(l):
                continue
            for n in nomes:
                if n in l and res[n].search(l):
                    out[n].append(f"{rel}:{i}")
    return out


def excecoes_registradas(raiz):
    """Arquivos listados na seção de exceções do CLAUDE.md (fora do bloco do plugin)."""
    texto = re.sub(re.escape(MARCA_INI) + r".*?" + re.escape(MARCA_FIM), "", ler(os.path.join(raiz, "CLAUDE.md")), flags=re.S)
    if TITULO_EXCECOES not in texto:
        return []
    corpo = texto.split(TITULO_EXCECOES, 1)[1]
    corpo = re.split(r"^#{1,2} ", corpo, maxsplit=1, flags=re.M)[0]
    return re.findall(r"^- `([^`]+)`", corpo, flags=re.M)


def registrar_excecao(raiz, arquivo, motivo):
    p = os.path.join(raiz, "CLAUDE.md")
    texto = ler(p)
    if arquivo in excecoes_registradas(raiz):
        return False
    linha = f"- `{arquivo}` — {motivo}. Continua sendo mantido no formato que o código espera; o status das fatias " \
            "fica no STATUS.md."
    if TITULO_EXCECOES in texto:
        ini = texto.index(TITULO_EXCECOES) + len(TITULO_EXCECOES)
        resto = texto[ini:]
        m = re.search(r"^#{1,2} |^" + re.escape(MARCA_INI), resto, flags=re.M)
        fim = ini + (m.start() if m else len(resto))
        trecho = texto[ini:fim].rstrip("\n")
        novo = texto[:ini] + trecho + "\n" + linha + "\n" + ("\n" if m else "") + texto[fim:].lstrip("\n") \
            if m else texto[:ini] + trecho + "\n" + linha + "\n"
    else:
        novo = texto.rstrip("\n") + ("\n\n" if texto.strip() else "") + TITULO_EXCECOES + "\n" + \
            "Arquivos de status que o código do projeto lê. Ficam fora do bloco do plugin (o `/instalar-status` → " \
            "atualizar não mexe aqui).\n" + linha + "\n"
    escrever(p, novo)
    return True


def cmd_excecao(a):
    raiz = a.raiz
    if a.listar or not a.arquivo:
        lst = excecoes_registradas(raiz)
        print("Exceções à regra de status no CLAUDE.md: " + (", ".join(lst) if lst else "nenhuma"))
        return
    arq = a.arquivo.strip().lstrip("./")
    if not os.path.exists(os.path.join(raiz, arq)):
        sair(f"{arq} não existe neste repositório.")
    motivo = a.motivo.strip().rstrip(".")
    if not motivo:
        lidos = leitores_de(raiz, [os.path.basename(arq)])[os.path.basename(arq)]
        if not lidos:
            sair(f"Nenhum código cita {arq}; diga o motivo com --motivo \"lido por ...\".")
        motivo = "lido por " + ", ".join(f"`{x}`" for x in lidos[:3])
    if registrar_excecao(raiz, arq, motivo):
        print(f"Exceção registrada no CLAUDE.md (seção '{TITULO_EXCECOES[3:]}', fora do bloco do plugin): {arq}")
    else:
        print(f"{arq} já está nas exceções; nada mudou.")


def conflitos_claude_md(texto):
    """Seções de status/tempo fora do bloco do plugin (instalação manual antiga)."""
    fora = re.sub(re.escape(MARCA_INI) + r".*?" + re.escape(MARCA_FIM), "", texto, flags=re.S)
    achou = []
    for i, l in enumerate(fora.splitlines(), 1):
        if re.match(r"^#{1,4}\s*(Regra(s)? de status|Tempo e custo|Status do projeto)\b", l, re.I):
            achou.append(l.strip())
    return achou


def projeto_e_novo(raiz):
    if c.n_commits(raiz) > 0:
        return False
    arquivos = [f for f in arquivos_versionados(raiz) if not re.match(
        r"(README|LICENSE|\.gitignore|\.gitattributes|CLAUDE\.md|STATUS\.md|\.claude)", f, re.I)]
    return len(arquivos) == 0


# palavras do título de uma fase fora do padrão → fase padrão equivalente (a ordem importa: "aguardando teste"
# é 🧪 antes de ser ⏸️; "fatia pronta, não iniciada" é 📦 antes de ser ✅)
SINONIMOS_FASE = [
    ("🧪", r"test|valida|homolog|review|revis[ãa]o|\bqa\b"),
    ("⏸️", r"bloque|block|pausad|parad|esperando|aguardando|externo|on hold"),
    ("📦", r"n[ãa]o\s+iniciad|fila|backlog|a\s+fazer|to\s*do|pr[óo]xim|planejad|pendente|prontas?\s+para|ready"),
    ("🌐", r"execu|andamento|codando|fazendo|doing|progress|desenvolv|wip|ativ|trabalhando|agora"),
    ("✅", r"conclu|feit[oa]|done|finaliz|entregue|pronto|encerrad|arquivad"),
]


def secoes_status(texto):
    """[(titulo_ou_None, linhas)]: o preâmbulo vem com título None; cada '## ' abre uma seção."""
    secoes = [(None, [])]
    for l in texto.splitlines():
        if l.startswith("## "):
            secoes.append((l, []))
        else:
            secoes[-1][1].append(l)
    return secoes


def sugerir_fase(titulo):
    t = re.sub(r"^##\s*", "", titulo).lower()
    for e, padrao in SINONIMOS_FASE:
        if re.search(padrao, t):
            return e
    return ""


def fases_extras(raiz):
    """Seções '## ' do STATUS.md que não são uma das 5 fases (os hooks e as regras não enxergam os itens delas)."""
    texto = ler(os.path.join(raiz, "STATUS.md"))
    out = []
    for tit, linhas in secoes_status(texto)[1:]:
        if c.RE_FASE.match(tit):
            continue
        itens = sum(1 for l in linhas if l.startswith("- "))
        if itens or sugerir_fase(tit):  # seção de notas sem itens e sem cara de fase fica de fora
            out.append({"titulo": tit[3:].strip(), "itens": itens, "sugestao": sugerir_fase(tit)})
    return out


def ajustar_status(texto, mapa):
    """Troca os títulos de `mapa` ({titulo: emoji}) pela fase padrão, junta seções da mesma fase (itens da seção
    trocada vão para o fim da fase que já existia, sem o '(nada agora)'), põe as 5 fases na ordem e acrescenta as
    que faltarem. Outras seções e o preâmbulo ficam como estão. Rodar de novo não muda nada."""
    secoes = secoes_status(texto)
    preambulo, resto = secoes[0][1], secoes[1:]
    fases, outras, posicao = {}, [], None
    for i, (tit, linhas) in enumerate(resto):
        nome = tit[3:].strip()
        m = c.RE_FASE.match(tit)
        e = c.emoji_fase(m.group(1)) if m else mapa.get(nome, "")
        if not e:
            outras.append((tit, linhas))
            continue
        posicao = len(outras) if posicao is None else posicao
        corpo = [l for l in linhas]
        if e in fases:
            base = fases[e][1]
            novos = [l for l in corpo if l.strip() and l.strip() != "(nada agora)"]
            if novos:
                base[:] = [l for l in base if l.strip() != "(nada agora)"]
                while base and not base[-1].strip():
                    base.pop()
                base += novos + [""]
        else:
            titulo = tit if m else f"## {e} {dict(c.FASES)[e]}"
            fases[e] = (titulo, corpo)
    for e, nome in c.FASES:
        if e not in fases:
            fases[e] = (f"## {e} {nome}", ["(nada agora)", ""])
    posicao = 0 if posicao is None else posicao
    ordem = outras[:posicao] + [fases[e] for e, _ in c.FASES] + outras[posicao:]
    linhas = list(preambulo)
    for tit, corpo in ordem:
        linhas.append(tit)
        corpo = list(corpo)
        while len(corpo) > 1 and not corpo[-1].strip() and not corpo[-2].strip():
            corpo.pop()
        if corpo and corpo[-1].strip():
            corpo.append("")
        linhas += corpo
    return "\n".join(linhas).rstrip("\n") + "\n"


ARQ_CONCLUIDOS = os.path.join("docs", "CONCLUIDOS.md")


def cortar_concluidos(texto, dias, ver, hoje=None):
    """Mantém no ✅ só os itens dos últimos `dias` (pela data do '(desde DD/MM)'); sem data, o item fica.
    Fecha o ✅ com '- Versões anteriores: ver <ver>'. Devolve (texto_novo, itens_tirados[lista de blocos de linhas])."""
    hoje = (hoje or c.agora()).replace(hour=0, minute=0, second=0, microsecond=0)
    limite = hoje - timedelta(days=dias)
    secoes = secoes_status(texto)
    tirados, achou = [], False
    for i, (tit, linhas) in enumerate(secoes):
        if not tit or not c.RE_FASE.match(tit) or c.emoji_fase(c.RE_FASE.match(tit).group(1)) != "✅":
            continue
        achou = True
        blocos, solto = [], []  # blocos de item (linha + subitens) e o texto que não é item
        for l in linhas:
            if l.startswith("- "):
                blocos.append([l])
            elif blocos and l[:1] in (" ", "\t") and l.strip():
                blocos[-1].append(l)
            else:
                solto.append((len(blocos), l))
        fica = []
        for b in blocos:
            if c.RE_VERSOES_ANT.match(b[0]):
                continue  # a linha antiga sai; a nova vai no fim
            ds = c.RE_DESDE.findall(" ".join(b))
            dt = c.data_do_desde(ds[-1]) if ds and ds[-1] != "?" else None
            (tirados if dt and dt < limite else fica).append(b)
        cab = [l for n, l in solto if n == 0 and l.strip()]  # texto antes do 1º item (ex.: descrição da fase)
        corpo = cab + [l for b in fica for l in b]
        corpo = [l for l in corpo if l.strip() != "(nada agora)"] or []
        corpo.append(f"- Versões anteriores: ver {ver}")
        secoes[i] = (tit, corpo + [""])
    if not achou:
        return texto, []
    out = []
    for tit, linhas in secoes:
        if tit:
            out.append(tit)
        out += linhas
    return "\n".join(out).rstrip("\n") + "\n", tirados


def ver_atual(texto):
    """Para onde a linha 'Versões anteriores: ver X' do ✅ já aponta (ex.: 'VERSOES.json e PROGRESSO.md'), ou ''."""
    for l in texto.splitlines():
        if c.RE_VERSOES_ANT.match(l):
            m = re.search(r"\bver\s+(.+?)\s*(?:\(desde[^)]*\))?\s*\.?$", l, re.I)
            return m.group(1).strip("` ") if m else ""
    return ""


def concluidos_antigos(raiz, dias):
    texto = ler(os.path.join(raiz, "STATUS.md"))
    return len(cortar_concluidos(texto, dias, "x")[1]) if texto else 0


def guardar_concluidos(raiz, arquivo, tirados, dias):
    p = os.path.join(raiz, arquivo)
    os.makedirs(os.path.dirname(p) or raiz, exist_ok=True)
    novo = not os.path.exists(p)
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        if novo:
            f.write(f"# Concluídos anteriores — {c.nome_pasta(raiz)}\n\n"
                    "Itens tirados do ✅ do STATUS.md pelo corte (status-projeto status-md --cortar-concluidos).\n")
        f.write(f"\n## Corte de {c.agora():%d/%m/%Y} (concluídos há mais de {dias} dias)\n")
        for b in tirados:
            f.write("\n".join(b) + "\n")


def fases_faltando(raiz):
    fases, presentes = c.ler_status_arquivo(raiz)
    if fases is None:
        return None
    return [e for e, _ in c.FASES if e not in presentes]


def dados_existentes(raiz):
    """taxa.csv e estimativa_git.csv que o projeto já tem: o instalador aproveita, sem sobrescrever nem recalcular."""
    tx = c.ler_taxa_csv(raiz)
    est = c.ler_estimativa(os.path.join(raiz, c.CSV_ESTIMATIVA))
    out = {"taxa_csv": None, "estimativa_git": None}
    if tx:
        out["taxa_csv"] = {"arquivo": c.CSV_TAXA, "linhas": len(tx), "valor_atual": tx[-1]["valor"],
                           "desde": tx[-1]["desde"], "historico": [[t["desde"], t["valor"]] for t in tx]}
    if est is not None:
        h = sum(float(r.get("horas") or 0) for r in est)
        cu = sum(float(r.get("custo") or 0) for r in est)
        out["estimativa_git"] = {"arquivo": c.CSV_ESTIMATIVA, "sessoes": len(est), "horas": round(h, 2),
                                 "custo": round(cu, 2), "colunas": list(est[0].keys()) if est else []}
    return out


def cmd_estado(a):
    raiz = a.raiz
    cfg = c.ler_config(raiz)
    pastas, na_raiz = detectar_pastas_fatias(raiz)
    autores = collections.Counter(c.git(raiz, "log", "--all", "--format=%an").splitlines())
    claude_md = ler(os.path.join(raiz, "CLAUDE.md"))
    etapas = (cfg or {}).get("etapas", {})
    pend = [e for e in c.ETAPAS if e not in etapas]
    saida = {
        "raiz": raiz,
        "repo": c.nome_pasta(raiz),
        "instalado": cfg is not None,
        "instalacao_completa": cfg is not None and not pend,
        "etapas_feitas": {e: etapas[e] for e in c.ETAPAS if e in etapas},
        "etapas_pendentes": pend if cfg else c.ETAPAS,
        "versao_plugin": c.versao_plugin(),
        "versao_plugin_instalada": (cfg or {}).get("versao_plugin", ""),
        "precisa_atualizar": bool(cfg) and (cfg.get("versao_plugin") != c.versao_plugin()),
        "config": cfg,
        "git": {
            "repo_git": c.eh_repo_git(raiz),
            "pasta_pessoal": c.eh_pasta_pessoal(raiz),
            "commits": c.n_commits(raiz),
            "autores": autores.most_common(5),
            "github": c.remoto_github(raiz),
            "branch": c.git(raiz, "rev-parse", "--abbrev-ref", "HEAD"),
        },
        "projeto_novo": projeto_e_novo(raiz),
        "status_md": {"existe": os.path.exists(os.path.join(raiz, "STATUS.md")),
                      "fases_faltando": fases_faltando(raiz),
                      "fases_extras": fases_extras(raiz) if os.path.exists(os.path.join(raiz, "STATUS.md")) else [],
                      "concluidos_mais_de_7_dias": concluidos_antigos(raiz, 7)},
        "claude_md": {"existe": bool(claude_md), "tem_bloco": MARCA_INI in claude_md,
                      "regras_antigas_fora_do_bloco": conflitos_claude_md(claude_md)},
        "sessoes_csv": os.path.exists(os.path.join(raiz, c.CSV_SESSOES)),
        "estimativa_git": os.path.exists(os.path.join(raiz, c.CSV_ESTIMATIVA)),
        "pastas_fatias_detectadas": pastas,
        "fatias_soltas_na_raiz": na_raiz,
        "dados_existentes": dados_existentes(raiz),
        "chamadas_autonomas": chamadas_autonomas(raiz),
        "fatias_fora_da_pasta": fatias_fora_da_pasta(raiz, cfg),
        "hooks_manuais_antigos": hooks_manuais(raiz),
        "instalacoes_plugin": json_instalacoes(raiz),
        "enabled_plugins_antigo": enabled_antigo(settings_projeto(raiz, estrito=False)[1]),
    }
    print(json.dumps(saida, ensure_ascii=False, indent=2))


def json_instalacoes(raiz):
    info = c.instalacoes_plugin(raiz)
    return {"arquivo": info["arquivo"],
            "todas": [{k: x[k] for k in ("chave", "escopo", "versao", "pasta", "projeto", "descartada", "vence", "esta")}
                      for x in info["todas"]],
            "validas": len(info["validas"]),
            "duplicadas": len(info["validas"]) > 1,
            "esta_vence": info["esta_vence"],
            "comandos_corrigir": c.comandos_corrigir_instalacoes(info),
            "texto": "\n".join(c.texto_instalacoes(info))}


def cmd_instalacoes(a):
    """Mostra as instalações do plugin que valem aqui e, se houver mais de uma, os comandos para corrigir.
    Código 3 quando há mais de uma valendo. Não desinstala nada."""
    info = c.instalacoes_plugin(a.raiz)
    if a.json:
        print(json.dumps(json_instalacoes(a.raiz), ensure_ascii=False, indent=2))
    else:
        print("\n".join(c.texto_instalacoes(info)))
    sys.exit(3 if len(info["validas"]) > 1 else 0)


def cmd_init(a):
    raiz = a.raiz
    cfg = c.ler_config(raiz)
    if cfg is not None:
        print("Config já existe; nada foi trocado (use /status-valor para mudar o valor da hora).")
        return
    if not a.usuario:
        sair("Falta --usuario.")
    if c.eh_pasta_pessoal(raiz):
        sair(f"Recusado: {raiz} é a sua pasta pessoal. Abra o Claude Code na pasta do projeto.", 3)
    cfg = c.config_padrao()
    tx = c.ler_taxa_csv(raiz)
    if tx:  # projeto já tem taxa.csv: aproveita, não sobrescreve
        atual = tx[-1]
        if a.valor is not None and abs(float(a.valor) - atual["valor"]) > 0.005:
            if not a.valor_desde:
                sair(f"{c.CSV_TAXA} já existe: valor atual {c.dinheiro(atual['valor'])} desde "
                     f"{c.data_br(atual['desde'])}. O valor informado ({c.dinheiro(float(a.valor))}) é diferente: "
                     "pergunte a partir de quando ele vale e rode de novo com --valor-desde AAAA-MM-DD "
                     "(acrescenta uma linha no taxa.csv; as antigas não mudam). Para manter o atual, rode sem --valor.", 3)
            d = c.para_dt(a.valor_desde) or (c.data_do_desde(a.valor_desde) if "/" in a.valor_desde else None)
            if not d:
                sair("Data inválida em --valor-desde (use AAAA-MM-DD ou DD/MM/AAAA).")
            if d.strftime(c.FMT) <= atual["desde"]:
                sair(f"--valor-desde precisa ser depois de {c.data_br(atual['desde'])} (a última linha do taxa.csv); "
                     "as linhas antigas não são mudadas.")
            c.acrescentar_taxa_csv(raiz, d, float(a.valor), "valor informado na instalação do status-projeto")
            print(f"{c.CSV_TAXA}: linha nova {c.dinheiro(float(a.valor))} a partir de {c.data_br(d.strftime(c.FMT))} "
                  "(as linhas antigas não mudaram).")
            tx = c.ler_taxa_csv(raiz)
        else:
            print(f"Valor da hora aproveitado de {c.CSV_TAXA} ({len(tx)} linha(s); atual {c.dinheiro(atual['valor'])}); "
                  "o arquivo não foi mexido.")
        valor_hora = tx
    else:
        valor_hora = [{"desde": c.INICIO_DOS_TEMPOS, "valor": float(150.0 if a.valor is None else a.valor),
                       "obs": "valor inicial"}]
    cfg.update({
        "instalado_em": c.agora_s(),
        "usuario": a.usuario.strip(),
        "valor_hora": valor_hora,
        "pasta_fatias": c.barra(a.pasta_fatias).strip("/"),
        "pasta_fatias_executadas": c.barra(a.pasta_executadas or c.barra(a.pasta_fatias).strip("/") + "_executadas").strip("/"),
        "projeto_novo": projeto_e_novo(raiz),
        "autores_git": a.autor or [],
        "repos": [{"nome": c.nome_pasta(r), "caminho": c.barra(r)} for r in (a.repo or [])],
    })
    cfg["etapas"] = {"config": c.agora_s()}
    c.gravar_config(raiz, cfg)
    print(f"Config criado em {c.ARQ_CFG} (instalado em {cfg['instalado_em']}; o tempo daqui em diante é medido pelos hooks).")


def cmd_status_md(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    p = os.path.join(raiz, "STATUS.md")
    if a.vazio:
        if os.path.exists(p):
            print("STATUS.md já existe; não foi sobrescrito.")
        else:
            escrever(p, template("STATUS.md", {"projeto": c.nome_pasta(raiz), "data": c.agora().strftime("%d/%m/%Y"),
                                               "usuario": cfg.get("usuario") or "o usuário"}))
            print("STATUS.md criado com as 5 fases vazias.")
    falta = fases_faltando(raiz)
    if falta is None:
        sair("STATUS.md não existe.")
    if a.ajustar:
        mapa = {}
        for par in a.ajustar:
            tit, _, e = par.rpartition("=")
            e = c.emoji_fase(e.strip())
            if not tit.strip() or e not in dict(c.FASES):
                sair(f"Use --ajustar \"Título da seção=🌐\" (fase: {' '.join(x for x, _ in c.FASES)}). Recebido: {par}")
            mapa[re.sub(r"^##\s*", "", tit.strip())] = e
        nomes = {x["titulo"] for x in fases_extras(raiz)}
        for t in mapa:
            if t not in nomes:
                sair(f"Seção '{t}' não encontrada entre as fases fora do padrão: {', '.join(sorted(nomes)) or 'nenhuma'}.")
        antes = ler(p)
        novo = ajustar_status(antes, mapa)
        if novo != antes:
            escrever(p, novo)
            print("STATUS.md ajustado ao formato (itens mantidos): "
                  + "; ".join(f"'{t}' → {e} {dict(c.FASES)[e]}" for t, e in mapa.items()))
        falta = fases_faltando(raiz)
    if falta and a.completar_fases:
        texto = ler(p).rstrip("\n") + "\n"
        for e, nome in c.FASES:
            if e in falta:
                texto += f"\n## {e} {nome}\n(nada agora)\n"
        escrever(p, texto)
        print("Fases acrescentadas no fim do STATUS.md (nada existente foi mexido): " + " ".join(falta))
        falta = []
    if falta:
        sair("STATUS.md sem as fases: " + " ".join(falta) + " (use --completar-fases para acrescentar só as que faltam)", 3)
    if a.cortar_concluidos:
        dias = a.dias if a.dias is not None else (cfg.get("corte_concluidos_dias") or 7)
        ver = (a.ver or cfg.get("arquivo_concluidos") or ver_atual(ler(p)) or ARQ_CONCLUIDOS).strip()
        if dias < 1:
            sair("--dias precisa ser 1 ou mais.")
        antes = ler(p)
        novo, tirados = cortar_concluidos(antes, dias, f"`{ver}`" if " " not in ver else ver)
        guarda = ver.lower().endswith(".md") and " " not in ver
        if tirados and guarda:
            guardar_concluidos(raiz, ver, tirados, dias)
        if novo != antes:
            escrever(p, novo)
        cfg["corte_concluidos_dias"], cfg["arquivo_concluidos"] = dias, ver
        c.gravar_config(raiz, cfg)
        print(f"✅: {len(tirados)} item(ns) com mais de {dias} dias tirado(s)"
              + (f" e guardado(s) em {ver}" if tirados and guarda else
                 (f"; não copiados para {ver} (não é .md): continuam no histórico do git" if tirados else ""))
              + f". O ✅ termina com 'Versões anteriores: ver {ver}'.")
    fases, _ = c.ler_status_arquivo(raiz)
    problemas = validar_status(fases)
    for pr in problemas:
        print("aviso: " + pr)
    if a.marcar:
        marcar(raiz, cfg, "status_md")
    print("STATUS.md ok: " + ", ".join(f"{e} {len(fases[e])}" for e, _ in c.FASES))


def validar_status(fases):
    probs = []
    if len(fases["🌐"]) > 3:
        probs.append(f"{len(fases['🌐'])} itens em 🌐 (máximo 3)")
    for it in fases["🌐"]:
        sub = " ".join(it["sub"]).lower()
        for campo in ("parei em", "próximo passo", "pendente"):
            if campo not in sub:
                probs.append(f"🌐 '{it['nome']}' sem '{campo.capitalize()}'")
    for it in fases["📦"]:
        if not it["tamanho"]:
            probs.append(f"📦 '{it['nome']}' sem tamanho [P]/[M]/[G]")
    for e, _ in c.FASES:
        for it in fases[e]:
            if not it["desde"]:
                probs.append(f"{e} '{it['nome']}' sem '(desde DD/MM)'")
    return probs


def cmd_espalhado(a):
    cfg = c.ler_config(a.raiz)
    achados = status_espalhado(a.raiz, cfg)
    if a.json:
        print(json.dumps(achados, ensure_ascii=False, indent=2))
        return
    if not achados:
        print("Nenhum outro arquivo com status encontrado.")
        return
    print("Arquivos que parecem guardar status (fora do STATUS.md):")
    fatias = [x for x in achados if x["fatia"] and not x["pelo_nome"]]
    for x in [x for x in achados if x not in fatias]:
        tag = (" [arquivo de fatia]" if x["fatia"] else "") + ("" if x["situacao"] == "versionado" else f" [{x['situacao']}]") \
            + (" [exceção registrada no CLAUDE.md]" if x["excecao"] else "") \
            + (f" [lido pelo código: {', '.join(x['lido_por'][:2])}]" if x["lido_por"] and not x["excecao"] else "")
        print(f"- {x['arquivo']}{tag}: {x['linhas_com_status']} linhas" + (" (nome de arquivo de status)" if x["pelo_nome"] else ""))
        for e in x["exemplos"]:
            print(f"    · {e}")
    if fatias:
        print(f"- e {len(fatias)} arquivos de fatia com checklist/marcas de status (normal em fatia; o status delas "
              "passa a ser o item no STATUS.md — veja `status-projeto fatias-soltas`)")


# ------------------------------------------------------------------- contradições nas fatias em 📦

RE_CAMINHO = re.compile(r"`([^`\s]+)`|(?<![\w`/.-])((?:\.?[\w*.-]+/)+[\w*.-]*|\.?[\w-]+\.(?:md|txt|json|csv)\b)")
RE_MOVER = re.compile(r"\b(git\s+mv|mv|mov[ae]r?|move[rs]?|arquiv[ae]r?|archive|transfer[ie]r?|levar?|leve)\b", re.I)
RE_APAGAR = re.compile(r"\b(apag[ae]r?|apague|delet[ae]r?|delete|exclu[ia]r?|exclua|git\s+rm|rm\s+-|remov[ae]r?)\b", re.I)
RE_OBJ_FATIA = re.compile(r"\b(fatia|slice|este arquivo|esse arquivo|this file|relat[óo]rio|report)", re.I)
RE_ARQUIVO_DESTINO = re.compile(r"(execut|conclu|done|archiv|arquiv|finaliz|antig|old|histor|feit)", re.I)
# só instrução de não versionar ("não commite o X"); "alteração não commitada" descreve o estado da árvore
RE_GITIGNORE = re.compile(r"gitignore|git\s+rm\s+--cached|untrack|don.?t\s+commit|\bn[ãa]o\s+(?:fa[çc]a\s+commit|"
                          r"commite|commitar|versione|versionar|suba|subir|envie|enviar|mande)\b", re.I)
# ...e o que concorda com a regra: "confira que X não está no .gitignore", "tire X do .gitignore"
RE_GITIGNORE_OK = re.compile(r"(n[ãa]o\s+(?:est[áa]|esteja|fique|pode\s+estar|deve\s+estar|seja)|tir[ae]r?|tire|"
                             r"remov[ae]r?|remova|fora)\b.*?gitignore|gitignore.*?\bn[ãa]o\s+(?:ignor|deve)", re.I)
RE_ALVO_STATUS = re.compile(r"(STATUS\.md|CLAUDE\.md|docs/tempo|pasta\s+d[ae]s?\s+fatias|fatias/|relat[óo]rios?\b)", re.I)
RE_GERAR = re.compile(r"\b(ger[ae]r?|gere|cri[ae]r?|salv[ae]r?|escrev[ae]r?|grav[ae]r?|generate|write|save|create|"
                      r"coloc[ae]r?|ponha)\b", re.I)
RE_RELAT = re.compile(r"relat[óo]rio|report", re.I)
RE_EXT_DOC = re.compile(r"\.(md|txt|html?|pdf)$", re.I)
RE_ATUALIZAR = re.compile(r"\b(atualiz[ae]r?|atualize|marc[ae]r?|marque|registr[ae]r?|anot[ae]r?|update|mark|check)\b", re.I)


def caminhos_da_linha(linha):
    out = []
    for m in RE_CAMINHO.finditer(linha):
        p = (m.group(1) or m.group(2) or "").strip().strip(".,;:)(\"'")
        p = re.sub(r"^\./", "", p)
        if p and not p.startswith(("http:", "https:", "//")) and ("/" in p or "." in p):
            out.append(p)
    return out


def dentro(caminho, pasta):
    return caminho.rstrip("/") == pasta or caminho.startswith(pasta + "/")


def arquivo_da_fatia(raiz, cfg, item):
    """Caminho relativo do arquivo .md de um item do STATUS.md (procura na pasta das fatias, na raiz e por nome)."""
    m = re.search(r"`([^`]+\.md)`", item["texto"])
    cands = [m.group(1)] if m else []
    nome = item["nome"]
    if nome:
        base = nome if nome.lower().endswith(".md") else nome + ".md"
        cands += [os.path.join(cfg.get("pasta_fatias", "fatias"), base), base]
    for cnd in cands:
        if os.path.isfile(os.path.join(raiz, cnd)):
            return os.path.normpath(cnd)
    alvo = c.normaliza(nome)
    for rel in arquivos_versionados(raiz):
        if rel.lower().endswith(".md") and c.normaliza(os.path.basename(rel)) == alvo:
            return rel
    return ""


def contradicoes_linha(linha, cfg):
    """[(tipo, regra, sugestão)] para uma linha de instrução de uma fatia."""
    pf = cfg.get("pasta_fatias", "fatias")
    pe = cfg.get("pasta_fatias_executadas", "fatias_executadas")
    caminhos = caminhos_da_linha(linha)
    achou = []
    # 1. onde arquivar
    if RE_OBJ_FATIA.search(linha) and RE_APAGAR.search(linha) and not RE_GITIGNORE.search(linha):
        achou.append(("arquivar", f"ao concluir, a fatia e o relatório vão com `git mv` para `{pe}/` (não são apagados)",
                      f"trocar por: ao concluir, `git mv` da fatia e do relatório para `{pe}/`"))
    elif RE_MOVER.search(linha) and (RE_OBJ_FATIA.search(linha) or any(RE_ARQUIVO_DESTINO.search(x) for x in caminhos)):
        destinos = [x for x in caminhos if RE_ARQUIVO_DESTINO.search(x) and not dentro(x, pe) and not dentro(x, pf)]
        if destinos:
            achou.append(("arquivar", f"fatia concluída vai para `{pe}/` (com o relatório dela)",
                          f"trocar `{destinos[0]}` por `{pe}/`"))
    # 2. .gitignore
    if RE_GITIGNORE.search(linha) and not RE_GITIGNORE_OK.search(linha):
        protegidos = ["STATUS.md", "CLAUDE.md", "docs/tempo", c.GUIA, ".claude-status/config.json", ".claude-status",
                      ".gitattributes", L.ARQ["ideia"], L.ARQ["erro"], pf, pe]
        alvo = [x for x in caminhos if any(dentro(x, pp) or dentro(pp, x.rstrip("/*")) or
                                            os.path.basename(x.rstrip("/")) == os.path.basename(pp) for pp in protegidos)]
        if not alvo and RE_ALVO_STATUS.search(linha):
            alvo = [RE_ALVO_STATUS.search(linha).group(1)]
        if alvo:
            achou.append(("gitignore", "STATUS.md, CLAUDE.md, docs/tempo/, o guia, o config e as pastas de fatias "
                                       "vão para o git (o claude.ai lê pelo GitHub)",
                          f"tirar a instrução de ignorar/não versionar {', '.join(alvo)}"))
    # 3. onde gerar o relatório
    if RE_RELAT.search(linha) and RE_GERAR.search(linha):
        ruins = [x for x in caminhos if (RE_EXT_DOC.search(x) or x.endswith("/")) and RE_RELAT.search(x)
                 and not dentro(x, pf)]
        ruins += [x for x in caminhos if x.endswith("/") and not dentro(x, pf) and x not in ruins
                  and re.search(r"\bem\s+`?" + re.escape(x), linha)]
        if ruins:
            achou.append(("relatorio", f"o relatório da fatia fica junto dela em `{pf}/` (e vai com ela para `{pe}/`)",
                          f"trocar `{ruins[0]}` por `{pf}/`"))
    # 4. status fora do STATUS.md
    if RE_ATUALIZAR.search(linha):
        outros = [x for x in caminhos if NOMES_STATUS.search(os.path.basename(x)) and os.path.basename(x) != "STATUS.md"]
        if outros:
            achou.append(("status", "status só no STATUS.md", f"trocar `{outros[0]}` por `STATUS.md`"))
    return achou


def id_contradicao(arquivo, tipo, linha):
    """Id estável do apontamento: não depende do número da linha nem da pasta (sobrevive a mover a fatia)."""
    chave = f"{os.path.basename(arquivo)}|{tipo}|{' '.join(linha.split()).lower()}"
    return hashlib.sha1(chave.encode("utf-8")).hexdigest()[:8]


def contradicoes_fatias(raiz, cfg):
    """(achados, sem_arquivo, ignorados): os marcados como ignorados no config não entram em achados."""
    fases, _ = c.ler_status_arquivo(raiz)
    if fases is None:
        return [], [], []
    ign = {x["id"] for x in cfg.get("contradicoes_ignoradas", [])}
    achados, sem_arquivo, ignorados = [], [], []
    for it in fases["📦"]:
        arq = arquivo_da_fatia(raiz, cfg, it)
        if not arq:
            sem_arquivo.append(it["nome"])
            continue
        for i, linha in enumerate(ler(os.path.join(raiz, arq)).splitlines(), 1):
            for tipo, regra, sug in contradicoes_linha(linha, cfg):
                x = {"id": id_contradicao(arq, tipo, linha), "fatia": it["nome"], "arquivo": arq, "linha": i,
                     "tipo": tipo, "trecho": linha.strip()[:160], "regra": regra, "sugestao": sug}
                (ignorados if x["id"] in ign else achados).append(x)
    return achados, sem_arquivo, ignorados


def cmd_contradicoes(a):
    cfg = precisa_config(a.raiz)
    achados, sem_arquivo, ignorados = contradicoes_fatias(a.raiz, cfg)
    if a.ignorar or a.desfazer:
        lista = cfg.setdefault("contradicoes_ignoradas", [])
        por_id = {x["id"]: x for x in achados + ignorados}
        for i in a.ignorar or []:
            if i not in por_id:
                sair(f"Apontamento {i} não encontrado (rode `status-projeto contradicoes` para ver os ids).")
            if not any(x["id"] == i for x in lista):
                x = por_id[i]
                lista.append({"id": i, "arquivo": x["arquivo"], "tipo": x["tipo"], "trecho": x["trecho"],
                              "em": c.agora_s(), "obs": a.obs or ""})
            print(f"Ignorado: {i} ({por_id[i]['arquivo']}:{por_id[i]['linha']}) — não volta a aparecer.")
        for i in a.desfazer or []:
            if not any(x["id"] == i for x in lista):
                sair(f"{i} não está entre os ignorados.")
            lista[:] = [x for x in lista if x["id"] != i]
            print(f"Voltou a valer: {i}.")
        c.gravar_config(a.raiz, cfg)
        return
    if a.ignoradas:
        lista = cfg.get("contradicoes_ignoradas", [])
        print("Apontamentos marcados como ignorados:" if lista else "Nenhum apontamento ignorado.")
        for x in lista:
            print(f"- {x['id']} {x['arquivo']} [{x['tipo']}] {x['trecho']}" + (f" — {x['obs']}" if x.get("obs") else ""))
        return
    if a.json:
        print(json.dumps({"contradicoes": achados, "sem_arquivo": sem_arquivo, "ignorados": len(ignorados)},
                         ensure_ascii=False, indent=2))
        return
    nomes = {"arquivar": "onde arquivar", "gitignore": ".gitignore", "relatorio": "onde gerar o relatório",
             "status": "status fora do STATUS.md"}
    if not achados:
        print("Nenhuma instrução das fatias em 📦 contradiz as regras do plugin.")
    else:
        print("Instruções nas fatias em 📦 que contradizem as regras do plugin (nada foi alterado):")
        for x in achados:
            print(f"- {x['id']} {x['arquivo']}:{x['linha']} [{nomes[x['tipo']]}] {x['trecho']}")
            print(f"    regra: {x['regra']}")
            print(f"    correção: {x['sugestao']}")
    if ignorados:
        print(f"({len(ignorados)} apontamento(s) marcado(s) como ignorado(s) não aparecem; veja com --ignoradas.)")
    if achados:
        print("Falso positivo? `status-projeto contradicoes --ignorar ID [--obs motivo]` (fica no config).")
    if sem_arquivo:
        print("Itens de 📦 sem arquivo de fatia encontrado (não conferidos): " + ", ".join(sem_arquivo))
    if achados:
        sys.exit(3)


# ------------------------------------------------------------------- estimativa pelo git

def fatia_do_commit(assunto, corpo):
    m = re.search(r"FATIA_[A-Za-z0-9_]+", assunto) or re.search(r"FATIA_[A-Za-z0-9_]+", corpo)
    if m:
        return m.group(0).rstrip("_")
    m = re.match(r"^[a-z]+\(([^)]+)\)!?:", assunto)
    if m and m.group(1).lower() not in GENERICOS and not re.fullmatch(r"\d+[a-z]?", m.group(1)):
        return m.group(1)
    return ""


def estimar_git(raiz, corte, taxas, autores=None, gap_h=2.0, antes_min=30.0):
    """Sessões estimadas pelo git log (todas as branches). Só o que veio antes de `corte` (datetime)."""
    raw = c.git(raiz, "log", "--all", "--format=%H%x1f%at%x1f%an%x1f%ae%x1f%s%x1f%b%x1e", timeout=120)
    vistos, commits = set(), []
    filtro = [x.lower() for x in (autores or []) if x]
    for reg in raw.split("\x1e"):
        p = reg.strip("\n").split("\x1f")
        if len(p) < 5 or p[0] in vistos:
            continue
        vistos.add(p[0])
        if filtro and p[2].lower() not in filtro and p[3].lower() not in filtro:
            continue
        ts = int(p[1])
        if corte and ts >= corte.timestamp():
            continue
        commits.append((ts, fatia_do_commit(p[4], p[5] if len(p) > 5 else "")))
    commits.sort()
    grupos, atual = [], []
    for cm in commits:
        if atual and cm[0] - atual[-1][0] > gap_h * 3600:
            grupos.append(atual)
            atual = []
        atual.append(cm)
    if atual:
        grupos.append(atual)
    linhas = []
    for g in grupos:
        ini = datetime.fromtimestamp(g[0][0] - antes_min * 60)
        fim = datetime.fromtimestamp(g[-1][0])
        if corte and fim > corte:
            fim = corte
        cont = collections.Counter(f for _, f in g if f)
        fatia = " + ".join(n for n, _ in cont.most_common(2)) if cont else "(sem fatia)"
        h = max(0.0, (fim - ini).total_seconds() / 3600)
        t = c.taxa_em(taxas, ini)
        linhas.append({"inicio": ini.strftime("%Y-%m-%d %H:%M"), "fim": fim.strftime("%Y-%m-%d %H:%M"),
                       "horas": f"{h:.2f}", "fatia": fatia, "tipo": "interativo", "commits": len(g),
                       "repo": c.nome_pasta(raiz), "valor_hora": f"{t:.2f}", "custo": f"{h * t:.2f}"})
    return linhas, len(commits)


def cmd_estimar(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    p = os.path.join(raiz, c.CSV_ESTIMATIVA)
    if os.path.exists(p):
        print(f"{c.CSV_ESTIMATIVA} já existe: a estimativa do git não é refeita (fica como foi gravada).")
        if "estimativa" not in cfg.get("etapas", {}):
            marcar(raiz, cfg, "estimativa")
        return
    if cfg.get("etapas", {}).get("estimativa") == "sem historico":
        print("Estimativa já feita na instalação (não havia commits antes dela); não é refeita.")
        return
    if "estimativa" in cfg.get("etapas", {}):
        sair(f"A estimativa já foi feita em {cfg['etapas']['estimativa']}, mas {c.CSV_ESTIMATIVA} sumiu. "
             f"Não refaço: recupere do git (git log --all -- {c.CSV_ESTIMATIVA}).", 3)
    if c.n_commits(raiz) == 0:
        marcar(raiz, cfg, "estimativa", "sem historico")
        print("Sem commits: não há horas anteriores à instalação para estimar.")
        return
    corte = c.para_dt(cfg.get("instalado_em")) or c.agora()
    linhas, n = estimar_git(raiz, corte, c.taxas(cfg), cfg.get("autores_git"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=c.CAMPOS_EST, lineterminator="\n")  # sempre LF
        w.writeheader()
        w.writerows(linhas)
    h = sum(float(l["horas"]) for l in linhas)
    custo = sum(float(l["custo"]) for l in linhas)
    marcar(raiz, cfg, "estimativa")
    print(f"Estimado antes da instalação: {n} commits, {len(linhas)} sessões, {c.horas_txt(h)}, "
          f"{c.dinheiro(custo, cfg['moeda'])} → {c.CSV_ESTIMATIVA}")


# ------------------------------------------------------------------- CLAUDE.md, hooks, git

def bloco_regras(cfg, raiz):
    irmaos = [f"`{r.get('caminho')}`" for r in cfg.get("repos", []) if isinstance(r, dict)]
    return template("regras-claude-md.md", {
        "versao": c.versao_plugin(),
        "usuario": cfg.get("usuario") or "o usuário",
        "pasta_fatias": cfg.get("pasta_fatias", "fatias"),
        "pasta_executadas": cfg.get("pasta_fatias_executadas", "fatias_executadas"),
        "repos_irmaos": ("Repos irmãos deste projeto (contam para o limite de 3 em 🌐 e para o relatório com --todos): "
                         + ", ".join(irmaos) + ".") if irmaos else
                        "Este projeto tem um repo só (irmãos entram em `repos` no `.claude-status/config.json`).",
        "listas_repos": ("Projeto com vários repos: cada ideia/erro leva a etiqueta do app (`--app "
                         + "|".join([c.nome_pasta(raiz)] + [r.get("nome") or os.path.basename(r.get("caminho", ""))
                                                               for r in cfg.get("repos", []) if isinstance(r, dict)])
                         + "`) e é gravado no repo dele. **Na dúvida de qual app é, pergunte.**")
                        if irmaos else "Um repo só: o app de cada ideia/erro é este repo.",
    }).strip("\n")


def cmd_claude_md(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    p = os.path.join(raiz, "CLAUDE.md")
    texto = ler(p)
    bloco = bloco_regras(cfg, raiz)
    conflitos = conflitos_claude_md(texto)
    if MARCA_INI in texto and MARCA_FIM in texto:
        novo = re.sub(re.escape(MARCA_INI) + r".*?" + re.escape(MARCA_FIM), lambda _: bloco, texto, count=1, flags=re.S)
        acao = "atualizado" if novo != texto else "já estava em dia"
    else:
        if conflitos and not a.mesmo_assim:
            print("O CLAUDE.md já tem regras de status/tempo fora do bloco do plugin:")
            for x in conflitos:
                print(f"  {x}")
            sair("Nada foi gravado. Pergunte ao usuário: tirar as seções antigas e usar o bloco do plugin, "
                 "ou gravar o bloco mesmo assim (--mesmo-assim).", 3)
        base = texto.rstrip("\n") if texto else f"# CLAUDE.md — {c.nome_pasta(raiz)}"
        novo = base + "\n\n" + bloco + "\n"
        acao = "acrescentado no fim" if texto else "criado"
    if novo != texto:
        escrever(p, novo)
    if MARCA_INI not in novo or novo.count(MARCA_INI) != 1:
        sair("Erro: bloco do plugin não ficou único no CLAUDE.md.")
    marcar(raiz, cfg, "claude_md")
    print(f"Regras no CLAUDE.md: {acao} (um bloco só, entre as marcas status-projeto).")


def hooks_manuais(raiz):
    achados = []
    for rel in (".claude/settings.json", ".claude/settings.local.json"):
        t = ler(os.path.join(raiz, rel))
        if re.search(r"tempo-hook|tempo_hook|sessoes\.csv", t):
            achados.append(rel)
    return achados


def fonte_marketplace():
    """Como o usuário adicionou o marketplace deste plugin (para registrar no projeto)."""
    nome_mk = "status-projeto"
    try:
        with open(os.path.join(c.RAIZ_PLUGIN, ".claude-plugin", "marketplace.json"), encoding="utf-8") as f:
            nome_mk = json.load(f).get("name", nome_mk)
    except Exception:
        pass
    p = os.path.join(c.pasta_config_claude(), "plugins", "known_marketplaces.json")
    try:
        with open(p, encoding="utf-8") as f:
            conhecidos = json.load(f)
    except Exception:
        conhecidos = {}
    ent = conhecidos.get(nome_mk)
    return nome_mk, (ent or {}).get("source")


def settings_projeto(raiz, estrito=True):
    """(caminho, dict) do .claude/settings.json do projeto. JSON inválido: sai sem mexer (ou {} se não estrito)."""
    p = os.path.join(raiz, ".claude", "settings.json")
    try:
        sett = json.loads(ler(p, "{}") or "{}")
    except ValueError:
        if not estrito:
            return p, {}
        sair(f"{p} não é um JSON válido; nada foi mexido.")
    return p, sett if isinstance(sett, dict) else {}


def enabled_antigo(sett):
    """As entradas status-projeto@... = true em enabledPlugins (gravadas pela etapa hooks até a 1.11.0)."""
    nome = c.nome_plugin()
    ep = sett.get("enabledPlugins")
    if not isinstance(ep, dict):
        return []
    return [k for k, v in ep.items() if k.split("@", 1)[0] == nome and v is True]


def tirar_enabled_antigo(raiz):
    """Tira do .claude/settings.json do projeto o enabledPlugins do status-projeto, mostrando antes o que sai.
    Essa entrada faz o Claude Code oferecer a instalação em escopo project (uma segunda instalação)."""
    p, sett = settings_projeto(raiz)
    chaves = enabled_antigo(sett)
    if not chaves:
        return False
    print(".claude/settings.json: tirando a entrada que fazia o Claude Code oferecer uma 2ª instalação "
          "(escopo project):")
    for k in chaves:
        print(f'    "enabledPlugins": {{ "{k}": true }}')
        del sett["enabledPlugins"][k]
    if not sett["enabledPlugins"]:
        del sett["enabledPlugins"]
    escrever(p, json.dumps(sett, ensure_ascii=False, indent=2) + "\n")
    print("  (o extraKnownMarketplaces fica; o plugin continua valendo pela instalação no escopo user)")
    return True


def cmd_hooks(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    hooks_json = os.path.join(c.RAIZ_PLUGIN, "hooks", "hooks.json")
    if not os.path.exists(hooks_json):
        sair("hooks/hooks.json do plugin não encontrado.")
    nome_mk, fonte = fonte_marketplace()
    tirar_enabled_antigo(raiz)
    p, sett = settings_projeto(raiz)
    mudou = False
    if fonte:
        # Só o marketplace. enabledPlugins aqui faria o Claude Code oferecer instalar em escopo project, e o plugin
        # ficaria instalado duas vezes (user + project), com versões diferentes.
        mks = sett.setdefault("extraKnownMarketplaces", {})
        if mks.get(nome_mk, {}).get("source") != fonte:
            mks[nome_mk] = {"source": fonte}
            mudou = True
    if mudou:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        escrever(p, json.dumps(sett, ensure_ascii=False, indent=2) + "\n")
    print("Hooks de tempo: vêm do plugin (hooks/hooks.json): SessionStart, UserPromptSubmit, PostToolUse, Stop, SessionEnd.")
    if fonte:
        print(f".claude/settings.json: marketplace {nome_mk} " + ("registrado" if mudou else "já registrado")
              + " (quem abrir o repo conhece o marketplace; instale o plugin com --scope user).")
    else:
        print("Aviso: o plugin não veio de um marketplace conhecido (ex.: --plugin-dir); "
              ".claude/settings.json do projeto não foi mexido.")
    velhos = hooks_manuais(raiz)
    if velhos:
        print("ATENÇÃO: há hooks de tempo manuais em " + ", ".join(velhos)
              + " — com o plugin, eles contariam a mesma sessão duas vezes. Pergunte ao usuário se pode tirá-los.")
    marcar(raiz, cfg, "hooks")


UNION = ["docs/tempo/sessoes.csv", L.ARQ["ideia"], L.ARQ["erro"]]


def tem_union(texto, arq):
    return bool(re.search(r"^\s*/?" + re.escape(arq) + r"\s+.*\bmerge=union\b", texto, re.M))


LINHA_LF = "docs/tempo/*.csv text eol=lf"


def tem_lf(texto):
    return bool(re.search(r"^\s*/?docs/tempo/\*\.csv\s+.*\beol=lf\b", texto, re.M))


def garantir_union(raiz):
    """Acrescenta no .gitattributes o merge=union que faltar (sessoes.csv, IDEIAS.md, ERROS.md) e o eol=lf dos CSVs
    (no Windows, com core.autocrlf=true, o checkout poria CRLF). True se mudou."""
    p = os.path.join(raiz, ".gitattributes")
    texto = ler(p)
    faltam = [x for x in UNION if not tem_union(texto, x)]
    if not faltam and tem_lf(texto):
        return False
    if not faltam:
        escrever(p, texto.rstrip("\n") + "\n" + LINHA_LF + "\n")
        return True
    novo = (texto.rstrip("\n") + "\n\n" if texto.strip() else "")
    novo += ("# status-projeto: cada sessão/registro é uma linha; no merge, junta as linhas dos dois lados\n"
             if not texto.count("status-projeto:") else "")
    novo += "".join(f"{x} merge=union\n" for x in faltam)
    if not tem_lf(texto):
        novo += LINHA_LF + "\n"
    escrever(p, novo)
    return True


def cmd_gitattributes(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    if garantir_union(raiz):
        print(".gitattributes: merge=union acrescentado (" + ", ".join(UNION) + ").")
    else:
        print(".gitattributes já tem merge=union no sessoes.csv, no IDEIAS.md e no ERROS.md.")
    marcar(raiz, cfg, "gitattributes")


DEVEM_ENTRAR = ["STATUS.md", "CLAUDE.md", ".gitattributes", c.ARQ_CFG, c.CSV_SESSOES, c.CSV_ESTIMATIVA, c.GUIA,
                L.ARQ["ideia"], L.ARQ["erro"]]
DEVEM_SAIR = [os.path.join(c.PASTA_LOCAL, "estado.json"), c.CSV_SESSOES + ".lock", c.CSV_SESSOES + ".tmp"]


def checar_gitignore(raiz):
    if not c.eh_repo_git(raiz):
        return [], []
    def ignorado(rel):
        return subprocess.run(["git", "-C", raiz, "check-ignore", "-q", "--no-index", rel]).returncode == 0
    return [r for r in DEVEM_ENTRAR if ignorado(r)], [r for r in DEVEM_SAIR if not ignorado(r)]


def gravar_bloco_gitignore(raiz, desfazer):
    p = os.path.join(raiz, ".gitignore")
    texto = ler(p)
    texto = re.sub(r"\n?" + re.escape(GI_INI) + r".*?" + re.escape(GI_FIM) + r"\n?", "\n", texto, flags=re.S)
    linhas = [GI_INI, f"{c.PASTA_LOCAL}/", "docs/tempo/*.lock", "docs/tempo/*.tmp"]
    for r in desfazer:  # só funciona se a pasta-mãe não estiver ignorada inteira
        partes = r.split("/")
        for i in range(1, len(partes)):
            linhas.append("!" + "/".join(partes[:i]) + "/")
        linhas.append("!" + r)
    linhas.append(GI_FIM)
    unicas = list(dict.fromkeys(linhas))
    novo = texto.rstrip("\n") + ("\n\n" if texto.strip() else "") + "\n".join(unicas) + "\n"
    if novo != ler(p):
        escrever(p, novo)
        return True
    return False


def cmd_gitignore(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    entram, saem = checar_gitignore(raiz)
    if saem or (entram and a.corrigir):
        # Ignorar os arquivos locais é sempre seguro; tirar algo do ignore só com --corrigir (o usuário autorizou).
        ja_desfeitos = [l[1:] for l in re.findall(r"^!.*$", ler(os.path.join(raiz, ".gitignore")), re.M)]
        desfazer = entram if a.corrigir else [r for r in ja_desfeitos if r in DEVEM_ENTRAR]
        if gravar_bloco_gitignore(raiz, desfazer):
            print(".gitignore: bloco status-projeto gravado.")
        entram, saem = checar_gitignore(raiz)
    for r in entram:
        print(f"PROBLEMA: {r} está no .gitignore (precisa ir para o git).")
    for r in saem:
        print(f"PROBLEMA: {r} não está no .gitignore (é arquivo local).")
    if not entram and not saem:
        print(".gitignore ok: STATUS.md, CLAUDE.md, docs/tempo/ e o config vão para o git; trava e estado local, não.")
        marcar(raiz, cfg, "gitignore")
    else:
        sair("Para tirar esses arquivos do ignore: --corrigir (pergunte antes ao usuário; se uma pasta-mãe inteira "
             "estiver ignorada, mostre a linha que precisa mudar).", 3)


# ------------------------------------------------------------------- guia

def itens_a_revisar(raiz):
    out = []
    for i, l in enumerate(ler(os.path.join(raiz, "STATUS.md")).splitlines(), 1):
        if not l.lstrip().startswith("- "):
            continue  # só itens (a legenda do arquivo também fala de "(?)")
        if "(?)" in l or "(desde ?)" in l:
            out.append(f"STATUS.md:{i} — {l.strip()[:110]}")
    return out


SEM_GITHUB = 4  # código de saída: não deu para saber DONO/REPO → o /instalar-status pergunta ao usuário


def textos_claude_ai(raiz, cfg):
    gh = c.remoto_github(raiz)
    if not gh:
        url = c.git(raiz, "remote", "get-url", c.nome_remoto(raiz)) if c.nome_remoto(raiz) else ""
        sair("Não consegui saber o repositório no GitHub (DONO/REPO) pelo remote"
             + (f" ({re.sub(r'//[^@/]+@', '//', url)})" if url else " (nenhum remote)") + ". Pergunte ao usuário e rode "
             "`status-projeto github DONO/REPO`; depois rode este comando de novo.", SEM_GITHUB)
    usuario = cfg.get("usuario") or "o usuário"
    instrucoes = template("instrucoes-claude-ai.md", {"repo_github": gh, "usuario": usuario,
                                                      "pasta_fatias": cfg.get("pasta_fatias", "fatias")}).strip()
    frase = f"Abre o repo {gh} e me diz o que tem no STATUS.md"
    return gh, instrucoes, frase


FRASE_GRAVACAO = "anota a ideia: teste de gravação pelo claude.ai"


def montar_guia(raiz, cfg):
    gh, instrucoes, frase = textos_claude_ai(raiz, cfg)
    revisar = itens_a_revisar(raiz)
    return template("COMO_USAR_STATUS.md", {
        "projeto": c.nome_pasta(raiz),
        "repo_github": gh,
        "usuario": cfg.get("usuario") or "o usuário",
        "valor": c.dinheiro(c.taxas(cfg)[-1][1], cfg.get("moeda", "R$")),
        "pasta_fatias": cfg.get("pasta_fatias", "fatias"),
        "pasta_executadas": cfg.get("pasta_fatias_executadas", "fatias_executadas"),
        "instrucoes_claude_ai": "\n".join("    " + l for l in instrucoes.splitlines()),
        "frase_teste": frase,
        "frase_gravacao": FRASE_GRAVACAO,
        "itens_revisar": "\n".join(f"   - {x}" for x in revisar) if revisar else "   - nenhum item com (?) no STATUS.md.",
        "versao": c.versao_plugin(),
    })


def cmd_guia(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    if a.marcar and not a.gravar:
        sair("--marcar só junto com --gravar (a etapa guia é gravar o arquivo).")
    texto = montar_guia(raiz, cfg)
    if a.gravar:  # mostrar é o padrão; gravar só quando pedido (o /instalar-status pede)
        escrever(os.path.join(raiz, c.GUIA), texto)
        if a.marcar:
            marcar(raiz, cfg, "guia")
    print(texto)


# ------------------------------------------------------------------- atualizar / reparar / etapa / repos

def cmd_etapa(a):
    cfg = precisa_config(a.raiz)
    if a.nome not in c.ETAPAS:
        sair("Etapa desconhecida. Etapas: " + ", ".join(c.ETAPAS))
    marcar(a.raiz, cfg, a.nome, a.valor)
    print(f"Etapa '{a.nome}' marcada como feita.")


def diagnostico(raiz, cfg):
    """O que falta ou quebrou (sem mexer em nada)."""
    falta = []
    et = cfg.get("etapas", {})
    for e in c.ETAPAS:
        if e not in et:
            falta.append((e, "etapa não concluída"))
    if "status_md" in et:
        f = fases_faltando(raiz)
        if f is None:
            falta.append(("status_md", "STATUS.md sumiu (restaure pelo git; não é recriado por cima)"))
        elif f:
            falta.append(("status_md", "STATUS.md sem as fases " + " ".join(f)))
    if "claude_md" in et and MARCA_INI not in ler(os.path.join(raiz, "CLAUDE.md")):
        falta.append(("claude_md", "bloco de regras sumiu do CLAUDE.md"))
    if "gitattributes" in et:
        ga = ler(os.path.join(raiz, ".gitattributes"))
        sem = [x for x in UNION if not tem_union(ga, x)]
        if sem:
            falta.append(("gitattributes", "merge=union faltando no .gitattributes para " + ", ".join(sem)))
        if not tem_lf(ga):
            falta.append(("gitattributes", f"falta `{LINHA_LF}` no .gitattributes (CSVs com LF também no Windows)"))
    sem_listas = [L.ARQ[t] for t in ("ideia", "erro") if not os.path.exists(L.caminho(raiz, t))]
    if sem_listas and "status_md" in et:
        falta.append(("listas", " e ".join(sem_listas) + " não existem (rode `status-projeto listas`)"))
    if "gitignore" in et:
        e1, e2 = checar_gitignore(raiz)
        if e1 or e2:
            falta.append(("gitignore", "regras do .gitignore mudaram"))
    if "guia" in et and not os.path.exists(os.path.join(raiz, c.GUIA)):
        falta.append(("guia", f"{c.GUIA} sumiu"))
    if "guia" in et and "<dono>/" in ler(os.path.join(raiz, c.GUIA)):
        falta.append(("guia", f"{c.GUIA} com <dono> no lugar do repo do GitHub (rode `status-projeto github` e o guia)"))
    if et.get("estimativa") not in (None, "sem historico") and not os.path.exists(os.path.join(raiz, c.CSV_ESTIMATIVA)):
        falta.append(("estimativa", "estimativa_git.csv sumiu (não é refeita; recupere pelo git)"))
    return falta


def cmd_reparar(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)  # só consulta: o config já vem migrado na memória, nada é gravado
    falta = diagnostico(raiz, cfg)
    if a.json:
        print(json.dumps([{"etapa": e, "motivo": m} for e, m in falta], ensure_ascii=False))
        return
    if not falta:
        print("Nada faltando: a instalação está completa.")
        return
    print("Falta ou quebrou:")
    for e, m in falta:
        print(f"- {e}: {m}")


def cmd_atualizar(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    antes = cfg.get("versao_plugin", "?")
    cfg, _ = c.migrar(cfg)
    cfg["versao_plugin"] = c.versao_plugin()
    c.gravar_config(raiz, cfg)
    print(f"Config migrado ({antes} → {cfg['versao_plugin']}); nada foi apagado.")
    tirar_enabled_antigo(raiz)
    texto = ler(os.path.join(raiz, "CLAUDE.md"))
    if MARCA_INI in texto:
        novo = re.sub(re.escape(MARCA_INI) + r".*?" + re.escape(MARCA_FIM), lambda _: bloco_regras(cfg, raiz), texto,
                      count=1, flags=re.S)
        if novo != texto:
            escrever(os.path.join(raiz, "CLAUDE.md"), novo)
            print("CLAUDE.md: bloco de regras atualizado (só o que está entre as marcas).")
        else:
            print("CLAUDE.md: bloco já em dia.")
    if os.path.exists(os.path.join(raiz, c.GUIA)):
        if c.remoto_github(raiz):
            escrever(os.path.join(raiz, c.GUIA), montar_guia(raiz, cfg))
            print(f"{c.GUIA} regenerado.")
        else:
            print(f"{c.GUIA} NÃO regenerado: falta DONO/REPO do GitHub (pergunte ao usuário e rode "
                  "`status-projeto github DONO/REPO`, depois `status-projeto guia --gravar`).")
    criados = L.criar_arquivos(raiz)
    if criados:
        print("Criados (ideias e erros): " + ", ".join(criados))
    if "gitattributes" in cfg.get("etapas", {}) and garantir_union(raiz):
        print(".gitattributes: merge=union no IDEIAS.md e no ERROS.md acrescentado.")
    print("STATUS.md, sessoes.csv, estimativa_git.csv, IDEIAS.md e ERROS.md não foram reescritos.")


def cmd_github(a):
    """Mostra o DONO/REPO usado no guia; com argumento, grava no config (quando o remote não diz)."""
    raiz = a.raiz
    if not a.dono_repo:
        gh = c.remoto_github(raiz)
        if not gh:
            textos_claude_ai(raiz, {})  # sai com SEM_GITHUB e a mensagem
        print(gh)
        return
    cfg = precisa_config(raiz)
    v = a.dono_repo.strip()
    v = c.dono_repo_da_url(v) or v
    if not re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", v):
        sair("Formato esperado: DONO/REPO (ex.: BrunoEstevao/zapai).")
    cfg["repo_github"] = v
    c.gravar_config(raiz, cfg)
    print(f"Repositório no GitHub gravado no config: {v}")


def cmd_repos(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    lst = cfg.setdefault("repos", [])
    for r in [c.barra(x) for x in a.adicionar or []]:
        if not any(isinstance(x, dict) and x.get("caminho") == r for x in lst):
            lst.append({"nome": c.nome_pasta(r), "caminho": r})
    for r in a.remover or []:
        lst[:] = [x for x in lst if not (isinstance(x, dict) and (x.get("caminho") == r or x.get("nome") == r))]
    if a.adicionar or a.remover:
        c.gravar_config(raiz, cfg)
    for nome, cam in c.repos_do_projeto(raiz, cfg):
        inst = "instalado" if c.ler_config(cam) else "sem status-projeto (horas só pelo git)"
        print(f"- {nome}: {cam} ({inst})")
    faltando = [x.get("caminho") for x in lst if isinstance(x, dict)
                and not os.path.isdir(os.path.normpath(os.path.join(raiz, x.get("caminho", ""))))]
    for f in faltando:
        print(f"- {f}: pasta não encontrada nesta máquina")


# =================================================================== dados de horas

class Bloco:
    __slots__ = ("repo", "fonte", "tipo", "fatia", "ini", "fim", "h", "taxa", "custo_fixo")

    def __init__(self, repo, fonte, tipo, fatia, ini, fim, taxa):
        self.repo, self.fonte, self.tipo, self.fatia = repo, fonte, tipo, fatia
        self.ini, self.fim, self.taxa = ini, fim, taxa
        self.h = max(0.0, (fim - ini).total_seconds() / 3600)
        self.custo_fixo = None  # custo gravado no CSV (calculado com as horas sem arredondar): vale ele

    @property
    def custo(self):
        return self.custo_fixo if self.custo_fixo is not None else self.h * self.taxa

    @property
    def taxa_efetiva(self):
        return self.custo / self.h if self.h > 0 else self.taxa


def custo_da_linha(r):
    try:
        return float(str(r.get("custo") or "").replace(",", ".")) if str(r.get("custo") or "").strip() else None
    except ValueError:
        return None


def blocos_do_repo(nome, cam, cfg_principal):
    """(blocos, info) de um repo: estimado pelo git + medido pelos hooks."""
    cfg = c.ler_config(cam) or cfg_principal
    txs = c.taxas(cfg)
    blocos, info = [], {"repo": nome, "instalado": c.ler_config(cam) is not None, "n_commits_est": 0,
                        "corte": None, "estimativa_gravada": False}
    sess = c.ler_sessoes(os.path.join(cam, c.CSV_SESSOES))
    agora = c.agora()
    for l in sess:
        ini = c.para_dt(l["inicio"])
        fim = c.para_dt(l["fim"])
        if ini is None:
            continue
        if fim is None:
            continue  # teste ainda aberto: entra quando fechar
        tipo = l["tipo"] if l["tipo"] in c.TIPOS else "interativo"
        blocos.append(Bloco(nome, "hooks", tipo, l["fatia"], ini, min(fim, agora), c.taxa_em(txs, ini)))
    est = c.ler_estimativa(os.path.join(cam, c.CSV_ESTIMATIVA))
    if est is not None:
        info["estimativa_gravada"] = True
        for r in est:
            ini, fim = c.para_dt(r.get("inicio")), c.para_dt(r.get("fim"))
            if not ini or not fim:
                continue
            b = Bloco(nome, "git", r.get("tipo") or "interativo", r.get("fatia", ""), ini, fim,
                      float(r.get("valor_hora") or c.taxa_em(txs, ini)))
            if r.get("horas"):
                b.h = float(r["horas"])
            b.custo_fixo = custo_da_linha(r)
            blocos.append(b)
            info["n_commits_est"] += int(r.get("commits") or 0)
        info["corte"] = c.para_dt(cfg.get("instalado_em")) if c.ler_config(cam) else None
    else:
        primeiros = [b.ini for b in blocos if b.fonte == "hooks" and b.tipo != "teste"]
        corte = c.para_dt(c.ler_config(cam).get("instalado_em")) if c.ler_config(cam) else (min(primeiros) if primeiros else None)
        linhas, n = estimar_git(cam, corte, txs, cfg.get("autores_git"))
        info["n_commits_est"], info["corte"] = n, corte
        for r in linhas:
            b = Bloco(nome, "git", "interativo", r["fatia"], c.para_dt(r["inicio"]), c.para_dt(r["fim"]),
                      float(r["valor_hora"]))
            b.h = float(r["horas"])
            b.custo_fixo = custo_da_linha(r)
            blocos.append(b)
    return blocos, info


def coletar(raiz, cfg, todos=False, extras=None):
    repos = c.repos_do_projeto(raiz, cfg) if todos else [(c.nome_pasta(raiz), raiz)]
    for e in extras or []:
        cam = c.raiz_principal(e)
        if all(cam != x[1] for x in repos):
            repos.append((c.nome_pasta(cam), cam))
    blocos, infos = [], []
    for nome, cam in repos:
        b, i = blocos_do_repo(nome, cam, cfg)
        blocos += b
        infos.append(i)
    return blocos, infos


def uniao(blocos, txs):
    """Horas e custo de relógio, sem contar duas vezes o tempo simultâneo."""
    ivs = sorted((b.ini, b.ini + timedelta(hours=b.h), b.taxa_efetiva) for b in blocos if b.h > 0)
    h = custo = 0.0
    fim_ate = None
    for a, b, taxa in ivs:
        if fim_ate is None or a >= fim_ate:
            seg_ini, seg_fim = a, b
        elif b > fim_ate:
            seg_ini, seg_fim = fim_ate, b
        else:
            continue
        dh = (seg_fim - seg_ini).total_seconds() / 3600
        h += dh
        custo += dh * taxa  # valor por hora do próprio bloco (o do CSV, quando gravado)
        fim_ate = seg_fim if fim_ate is None else max(fim_ate, seg_fim)
    return h, custo


def soma(blocos):
    return sum(b.h for b in blocos), sum(b.custo for b in blocos)


def por_fatia(blocos):
    """{nome: {'git': h, 'hooks': h, 'custo': x, 'ini': dt, 'fim': dt, 'tipos': {tipo: h}}}; 'A + B' divide igual."""
    d = {}
    for b in blocos:
        nomes = [n.strip() for n in (b.fatia or "").split(" + ") if n.strip()] or ["(sem fatia)"]
        for n in nomes:
            chave = next((k for k in d if c.mesma_fatia(k, n)), n)
            x = d.setdefault(chave, {"git": 0.0, "hooks": 0.0, "custo": 0.0, "ini": b.ini, "fim": b.ini,
                                     "tipos": collections.Counter(), "repos": set()})
            parte = b.h / len(nomes)
            x[b.fonte] += parte
            x["custo"] += b.custo / len(nomes)
            x["tipos"][b.tipo] += parte
            x["ini"] = min(x["ini"], b.ini)
            x["fim"] = max(x["fim"], b.ini + timedelta(hours=b.h))
            x["repos"].add(b.repo)
    return d


def fase_de(nome, fases_por_repo):
    for repo, fases in fases_por_repo.items():
        if not fases:
            continue
        for e, _ in c.FASES:
            for it in fases[e]:
                if c.mesma_fatia(nome, it["nome"]):
                    return e, it
    return "", None


def linha_h(rotulo, h, custo, moeda, largura=26):
    print(f"  {rotulo:<{largura}} {c.horas_txt(h):>10}   {c.dinheiro(custo, moeda):>16}   {c.dias_txt(h):>6} dias de 8h")


# =================================================================== relatórios

def cmd_relatorio(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    moeda = cfg.get("moeda", "R$")
    txs = c.taxas(cfg)
    blocos, infos = coletar(raiz, cfg, a.todos, a.repo)
    repos = [i["repo"] for i in infos]
    if len(repos) > 1:
        print(f"Horas e custo — projeto com os repos: {', '.join(repos)}")
    else:
        irmaos = len(c.repos_do_projeto(raiz, cfg)) - 1
        print(f"Horas e custo — só o repo {repos[0]}" + (f" (para somar os {irmaos} irmãos: --todos)" if irmaos else ""))
    print("  valor da hora: " + "; ".join(f"{c.dinheiro(v, moeda)}/h desde {c.data_br(d)}" for d, v in txs)
          + " (cada sessão usa o valor vigente quando começou)")

    git_b = [b for b in blocos if b.fonte == "git"]
    hk = [b for b in blocos if b.fonte == "hooks"]
    cortes = ", ".join(f"{i['repo']} até {c.data_br(i['corte'].strftime(c.FMT))}" for i in infos if i["corte"])
    print(f"\nEstimado pelo git — antes da instalação{(' (' + cortes + ')') if cortes else ''}")
    print(f"  {sum(i['n_commits_est'] for i in infos)} commits, {len(git_b)} sessões "
          "(mais de 2 h entre commits = sessão nova; +30 min antes do 1º commit). É estimativa.")
    if len(repos) > 1:
        for r in repos:
            linha_h(r, *soma([b for b in git_b if b.repo == r]), moeda)
    linha_h("subtotal estimado", *soma(git_b), moeda)

    print("\nMedido pelos hooks — depois da instalação (docs/tempo/sessoes.csv)")
    for t in ("interativo", "autonomo", "planejamento", "teste"):
        linha_h(c.NOME_TIPO[t], *soma([b for b in hk if b.tipo == t]), moeda)
    if len(repos) > 1:
        for r in repos:
            linha_h(f"  {r}", *soma([b for b in hk if b.repo == r]), moeda)
    linha_h("subtotal medido", *soma(hk), moeda)

    print("\nTotal (estimado + medido)")
    for t, rot in (("interativo", "codando interativo"), ("autonomo", "codando autônomo"),
                   ("planejamento", "planejamento"), ("teste", "testando")):
        linha_h(rot, *soma([b for b in blocos if b.tipo == t]), moeda)
    th, tc = soma(blocos)
    linha_h("TOTAL", th, tc, moeda)
    uh, uc = uniao(blocos, txs)
    if th - uh > 0.05:
        print(f"  descontando sobreposição (sessões ou repos ao mesmo tempo): {c.horas_txt(uh)} de relógio, "
              f"{c.dinheiro(uc, moeda)} — {c.horas_txt(th - uh)} eram simultâneas")

    fases_por_repo = {}
    for nome, cam in (c.repos_do_projeto(raiz, cfg) if a.todos else [(c.nome_pasta(raiz), raiz)]):
        fases_por_repo[nome], _ = c.ler_status_arquivo(cam)
    pf = por_fatia(blocos)
    if pf:
        print("\nPor fatia (estimado | medido | total | custo | fase)")
        for nome, x in sorted(pf.items(), key=lambda kv: -(kv[1]["git"] + kv[1]["hooks"])):
            if x["git"] + x["hooks"] < 0.01:
                continue
            e, it = fase_de(nome, fases_por_repo)
            tam = f"[{it['tamanho']}] " if it and it.get("tamanho") else ""
            print(f"  {(tam + nome)[:40]:<40} {c.horas_txt(x['git']):>9} {c.horas_txt(x['hooks']):>9} "
                  f"{c.horas_txt(x['git'] + x['hooks']):>9} {c.dinheiro(x['custo'], moeda):>14}  {e}")
        print("  (sessão com duas fatias 'A + B' divide as horas igualmente entre elas)")


def cmd_valor(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    moeda = cfg.get("moeda", "R$")
    try:
        valor = float(str(a.valor).replace("R$", "").replace(".", "").replace(",", ".")) if "," in str(a.valor) \
            else float(str(a.valor).replace("R$", ""))
    except ValueError:
        sair("Valor inválido. Exemplo: status-projeto valor 180")
    if valor <= 0:
        sair("O valor precisa ser maior que zero.")
    desde = c.agora()
    if a.desde:
        d = c.para_dt(a.desde) or (c.data_do_desde(a.desde) if "/" in a.desde else None)
        if not d:
            sair("Data inválida (use AAAA-MM-DD ou DD/MM/AAAA).")
        if d < desde.replace(hour=0, minute=0, second=0) or d < c.para_dt(c.taxas(cfg)[-1][0]):
            sair("Sem efeito retroativo: a data precisa ser hoje ou depois (e depois do último valor).")
        desde = max(d, desde) if d.date() == desde.date() else d
    atual = c.taxa_em(cfg, desde)
    cfg["valor_hora"].append({"desde": desde.strftime(c.FMT), "valor": valor, "obs": a.obs or ""})
    if c.ler_taxa_csv(raiz):
        c.acrescentar_taxa_csv(raiz, desde, valor, a.obs or "")
        print(f"{c.CSV_TAXA}: linha nova no fim (as antigas não mudaram).")
    c.gravar_config(raiz, cfg)
    print(f"Valor da hora: {c.dinheiro(atual, moeda)} → {c.dinheiro(valor, moeda)} a partir de {c.data_br(desde.strftime(c.FMT))}.")
    print("Sessões anteriores continuam com o valor da época (estimativa do git grava o valor de cada sessão).")
    print("Histórico: " + "; ".join(f"{c.dinheiro(v, moeda)} desde {c.data_br(d)}" for d, v in c.taxas(cfg)))


def cmd_historico(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    moeda = cfg.get("moeda", "R$")
    blocos, infos = coletar(raiz, cfg, a.todos)
    fases_por_repo = {nome: c.ler_status_arquivo(cam)[0]
                      for nome, cam in (c.repos_do_projeto(raiz, cfg) if a.todos else [(c.nome_pasta(raiz), raiz)])}
    pf = por_fatia(blocos)
    # Itens do STATUS.md que ainda não têm horas também entram na linha do tempo.
    for repo, fases in fases_por_repo.items():
        if not fases:
            continue
        for e, _ in c.FASES:
            for it in fases[e]:
                if not any(c.mesma_fatia(k, it["nome"]) for k in pf):
                    dt = c.data_do_desde(it["desde"])
                    pf[it["nome"]] = {"git": 0.0, "hooks": 0.0, "custo": 0.0, "ini": dt, "fim": dt,
                                      "tipos": collections.Counter(), "repos": {repo}, "_sem_horas": True}
    print("Linha do tempo das fatias (primeira → última sessão | horas | custo | fase atual)\n")
    total_h = total_c = 0.0
    for nome, x in sorted(pf.items(), key=lambda kv: (kv[1]["ini"] or datetime.max)):
        e, it = fase_de(nome, fases_por_repo)
        h = x["git"] + x["hooks"]
        total_h += h
        total_c += x["custo"]
        periodo = f"{c.ddmm(x['ini'])} → {c.ddmm(x['fim'])}" if not x.get("_sem_horas") else "sem horas      "
        fase_txt = f"{e} desde {it['desde']}" if it and it["desde"] else e or "(fora do STATUS.md)"
        tam = f"[{it['tamanho']}] " if it and it.get("tamanho") else ""
        fonte = "medido" if x["hooks"] and not x["git"] else "estimado" if x["git"] and not x["hooks"] else \
            "est.+med." if h else ""
        repos = f" ({', '.join(sorted(x['repos']))})" if a.todos else ""
        print(f"  {periodo:<15} {(tam + nome)[:42]:<42} {c.horas_txt(h):>9} {c.dinheiro(x['custo'], moeda):>14}"
              f"  {fase_txt}  {fonte}{repos}")
    print(f"\n  Total: {c.horas_txt(total_h)} · {c.dinheiro(total_c, moeda)} · {c.dias_txt(total_h)} dias de 8h")


def cmd_cronograma(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    moeda = cfg.get("moeda", "R$")
    fases, _ = c.ler_status_arquivo(raiz)
    if not fases:
        sair("STATUS.md não encontrado.")
    blocos, _ = coletar(raiz, cfg, True)
    pf = por_fatia(blocos)
    amostras = {"P": [], "M": [], "G": []}
    for it in fases["✅"]:
        if not it["tamanho"]:
            continue
        x = next((v for k, v in pf.items() if c.mesma_fatia(k, it["nome"])), None)
        if x and x["git"] + x["hooks"] > 0:
            amostras[it["tamanho"]].append((x["git"] + x["hooks"], x["hooks"] > 0 and x["git"] == 0))
    media, avisos = {}, []
    for t, lst in amostras.items():
        medidas = [h for h, med in lst if med]
        if lst:
            media[t] = sum(h for h, _ in lst) / len(lst)
        else:
            media[t] = c.PADRAO_TAMANHO_H[t]
        if not lst:
            avisos.append(f"[{t}] sem nenhuma fatia concluída com horas: uso {c.horas_txt(media[t])} (padrão).")
        elif len(medidas) < 3:
            avisos.append(f"[{t}] média de {len(lst)} fatia(s), só {len(medidas)} medida(s) pelos hooks "
                          "(o resto é estimativa do git): pouco dado medido, trate como palpite.")
    # Ritmo: horas por dia corrido nos últimos 28 dias (mín. 1 h/dia); sem dado, horas_dia em dias úteis.
    agora = c.agora()
    recentes = [b for b in blocos if b.ini >= agora - timedelta(days=28)]
    hdia = sum(b.h for b in recentes) / 28 if recentes else 0
    ritmo_txt = f"{hdia:.1f} h por dia corrido (média dos últimos 28 dias)" if hdia >= 1 else \
        f"{cfg.get('horas_dia', 8)} h por dia útil (sem ritmo recente medido)"
    print(f"Cronograma das fatias em 📦 (na ordem do STATUS.md) — ritmo: {ritmo_txt}")
    print("  médias por tamanho (fatias ✅): " + ", ".join(
        f"[{t}] {c.horas_txt(media[t])} ({len(amostras[t])} fatia(s))" for t in "PMG"))
    acum = 0.0
    data = agora
    for it in fases["📦"]:
        t = it["tamanho"]
        h = media.get(t, c.PADRAO_TAMANHO_H["M"])
        acum += h
        if hdia >= 1:
            data = agora + timedelta(days=acum / hdia)
        else:
            dias = acum / float(cfg.get("horas_dia", 8))
            data, n = agora, 0
            while n < dias:
                data += timedelta(days=1)
                if data.weekday() < 5:
                    n += 1
        custo = h * c.taxa_em(cfg, agora)
        sem = "" if t else " (sem tamanho: contei como [M])"
        print(f"  {('[' + t + '] ' if t else '') + it['nome']:<45} {c.horas_txt(h):>9} {c.dinheiro(custo, moeda):>13}"
              f"   acumulado {c.horas_txt(acum):>9} → por volta de {data:%d/%m/%Y}{sem}")
    if not fases["📦"]:
        print("  (nenhuma fatia em 📦)")
    print(f"\n  Total em 📦: {c.horas_txt(acum)} · {c.dias_txt(acum)} dias de 8h · "
          f"{c.dinheiro(acum * c.taxa_em(cfg, agora), moeda)}")
    for av in avisos:
        print("  AVISO: " + av)


def status_em(raiz, quando):
    """Texto do STATUS.md commitado antes de `quando`."""
    h = c.git(raiz, "rev-list", "-1", f"--before={quando.strftime(c.FMT)}", "HEAD", "--", "STATUS.md")
    return c.git(raiz, "show", f"{h}:STATUS.md") if h else ""


def cmd_resumo(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    moeda = cfg.get("moeda", "R$")
    agora = c.agora()
    ini = (agora - timedelta(days=a.dias)).replace(hour=0, minute=0, second=0)
    fases, _ = c.ler_status_arquivo(raiz)
    if not fases:
        sair("STATUS.md não encontrado.")
    antigo_txt = status_em(raiz, ini)
    antigas = c.ler_status(antigo_txt)[0] if antigo_txt else None
    print(f"O que mudou desde {ini:%d/%m} ({a.dias} dias), por fase\n")
    algo = False
    for e, nome in c.FASES:
        entrou = [it for it in fases[e] if (c.data_do_desde(it["desde"]) or datetime.min) >= ini]
        if antigas:
            entrou += [it for it in fases[e] if it not in entrou and not any(
                c.mesma_fatia(it["nome"], x["nome"]) for x in antigas[e])]
            saiu = [x for x in antigas[e] if not any(c.mesma_fatia(x["nome"], it["nome"]) for it in fases[e])]
        else:
            saiu = []
        if not entrou and not saiu:
            continue
        algo = True
        print(f"{e} {nome}")
        for it in entrou:
            print(f"  + {it['texto'][:120]}")
            for s in it["sub"]:
                if re.match(r"(parei em|próximo passo|pendente)", s.lstrip("- ").lower()):
                    print(f"      {s[:120]}")
        for x in saiu:
            destino = fase_de(x["nome"], {"r": fases})[0]
            print(f"  − {x['nome']}" + (f" (foi para {destino})" if destino else " (saiu do STATUS.md)"))
    if not algo:
        print("  Nada mudou no STATUS.md nesse período.")
    blocos, _ = coletar(raiz, cfg)
    rec = [b for b in blocos if b.ini >= ini]
    if rec:
        h, cu = soma(rec)
        print(f"\nHoras no período: {c.horas_txt(h)} ({c.dinheiro(cu, moeda)}) — "
              + ", ".join(f"{c.NOME_TIPO[t]} {c.horas_txt(soma([b for b in rec if b.tipo == t])[0])}"
                          for t in c.TIPOS if any(b.tipo == t for b in rec)))
    print("\n" + L.contagem_txt(raiz, cfg) + " (/status-ideias, /status-erros)")
    if not antigas:
        print("\n(sem versão do STATUS.md no git de antes do período: comparei só pelas datas \"(desde DD/MM)\")")


def cmd_ajuda(a):
    raiz = a.raiz
    cfg = c.ler_config(raiz)
    if cfg is None:
        print("Este repositório ainda não tem o status-projeto. Rode /instalar-status.\n")
        print(ler(os.path.join(TEMPLATES, "AJUDA_CURTA.md")))
        return
    moeda = cfg.get("moeda", "R$")
    fases, _ = c.ler_status_arquivo(raiz)
    print(f"Projeto {c.nome_pasta(raiz)} — estado agora\n")
    if fases:
        for e, nome in c.FASES:
            print(f"  {e} {nome}: {len(fases[e])}")
        for it in fases["🌐"]:
            print(f"\n  🌐 {it['texto'][:110]}")
            for s in it["sub"]:
                print(f"     {s[:110]}")
        if fases["📦"]:
            print(f"\n  Próxima fatia (primeira de 📦): {fases['📦'][0]['texto'][:110]}")
        for pr in validar_status(fases):
            print(f"  aviso: {pr}")
    else:
        print("  STATUS.md não encontrado.")
    sess = c.ler_sessoes(os.path.join(raiz, c.CSV_SESSOES))
    teste = next((l for l in sess if l["tipo"] == "teste" and l["estado"] != "fechada"), None)
    print("\n  " + L.contagem_txt(raiz, cfg))
    if teste:
        print(f"\n  Teste aberto desde {c.data_br(teste['inicio'])}: {teste['fatia']} (diga 'terminei o teste às HH:MM')")
    blocos, _ = coletar(raiz, cfg)
    sem = [b for b in blocos if b.ini >= c.agora() - timedelta(days=7)]
    h, cu = soma(sem)
    print(f"\n  Últimos 7 dias: {c.horas_txt(h)} ({c.dinheiro(cu, moeda)}). Valor da hora: "
          f"{c.dinheiro(c.taxas(cfg)[-1][1], moeda)}.")
    falta = diagnostico(raiz, cfg)
    if falta:
        print("  Instalação: falta " + "; ".join(f"{e} ({m})" for e, m in falta) + " → /instalar-status")
    print("\n" + "-" * 70 + "\n")
    print(ler(os.path.join(raiz, c.GUIA)) or montar_guia(raiz, cfg))


def cmd_verificar(a):
    raiz = a.raiz
    cfg = c.ler_config(raiz)
    res = []

    def ok(cond, txt, dica=""):
        res.append((bool(cond), txt, dica))

    info = c.instalacoes_plugin(raiz)
    print("\n".join(c.texto_instalacoes(info)) + "\n")
    ok(len(info["validas"]) <= 1, f"uma instalação só do plugin valendo aqui ({len(info['validas'])})",
       "veja os comandos acima (o plugin não desinstala sozinho)")
    ok(cfg is not None, "config .claude-status/config.json", "rode /instalar-status")
    if cfg is None:
        for b, t, d in res:
            print(("✅ " if b else "❌ ") + t + ("" if b else f" — {d}"))
        sys.exit(1)
    falta = diagnostico(raiz, cfg)
    ok(not falta, "instalação completa", "; ".join(f"{e}: {m}" for e, m in falta))
    f = fases_faltando(raiz)
    ok(f == [], "STATUS.md com as 5 fases", "faltam " + " ".join(f or []) if f else "STATUS.md não existe")
    fases, _ = c.ler_status_arquivo(raiz)
    if fases:
        probs = validar_status(fases)
        ok(not probs, "STATUS.md segue as regras (🌐 ≤ 3, Parei em/Próximo passo/Pendente, tamanho, datas)",
           "; ".join(probs[:5]))
        total = sum(len(c.fatias_codando(cam)) for _, cam in c.repos_do_projeto(raiz, cfg))
        ok(total <= 3, f"🌐 somando os repos do projeto: {total} (máx. 3)", "tire itens de 🌐")
    texto = ler(os.path.join(raiz, "CLAUDE.md"))
    ok(texto.count(MARCA_INI) == 1, "regras no CLAUDE.md (um bloco só)", "rode /instalar-status → reparar")
    ok(not conflitos_claude_md(texto), "sem regras de status duplicadas fora do bloco",
       "; ".join(conflitos_claude_md(texto)))
    ok(os.path.exists(os.path.join(c.RAIZ_PLUGIN, "hooks", "hooks.json")), "hooks do plugin presentes")
    sess = c.ler_sessoes(os.path.join(raiz, c.CSV_SESSOES))
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    recente = [l for l in sess if (c.para_dt(l["fim"]) or datetime.min) >= c.agora() - timedelta(minutes=15)]
    ok(any(l["sessao"] == sid for l in sess) if sid else bool(recente),
       "hooks gravando esta sessão em docs/tempo/sessoes.csv",
       "o plugin está ativo? (/plugin → status-projeto habilitado; depois /reload-plugins)")
    ok(not hooks_manuais(raiz), "sem hooks de tempo manuais duplicados", ", ".join(hooks_manuais(raiz)))
    ok(not enabled_antigo(settings_projeto(raiz, estrito=False)[1]), "sem enabledPlugins do plugin no .claude/settings.json",
       "faz o Claude Code oferecer uma 2ª instalação (project): rode /instalar-status → Atualizar")
    ga = ler(os.path.join(raiz, ".gitattributes"))
    ok(all(tem_union(ga, x) for x in UNION), ".gitattributes com merge=union no sessoes.csv, IDEIAS.md e ERROS.md",
       "rode /instalar-status → reparar")
    ok(all(os.path.exists(L.caminho(raiz, t)) for t in ("ideia", "erro")), "IDEIAS.md e ERROS.md na raiz",
       "rode `status-projeto listas`")
    e1, e2 = checar_gitignore(raiz)
    ok(not e1 and not e2, ".gitignore certo", "; ".join([f"{x} ignorado" for x in e1] + [f"{x} não ignorado" for x in e2]))
    ok(os.path.exists(os.path.join(raiz, c.GUIA)), f"guia {c.GUIA}")
    gh = c.remoto_github(raiz)
    ok(gh, f"remote no GitHub ({gh or 'nenhum'})", "o claude.ai lê o repo pelo GitHub: crie o remote e faça push")
    if gh:
        rn = c.nome_remoto(raiz) or "origin"
        c.git(raiz, "fetch", "-q", rn, timeout=30)
        br = c.git(raiz, "rev-parse", "--abbrev-ref", "HEAD")
        remoto = c.git(raiz, "show", f"{rn}/{br}:STATUS.md")
        local = ler(os.path.join(raiz, "STATUS.md"))
        ok(remoto and remoto.strip() == local.strip(), f"STATUS.md igual no GitHub ({rn}/{br})",
           "o claude.ai vai ler uma versão velha: commit e push do STATUS.md (só com 'pode commitar')")
    for b, t, d in res:
        print(("✅ " if b else "❌ ") + t + ("" if b or not d else f" — {d}"))
    if not gh:
        print("\nSem DONO/REPO do GitHub não há frase de teste: pergunte ao usuário e rode "
              "`status-projeto github DONO/REPO`.")
        sys.exit(2)
    _, instrucoes, frase = textos_claude_ai(raiz, cfg)
    print("\nPara testar no claude.ai (no projeto com o repo conectado), mande:\n")
    print(f"  {frase}\n")
    print("Resposta certa: os mesmos itens que estão no STATUS.md do GitHub agora.")
    print(f"\nPara testar a gravação (só IDEIAS.md e ERROS.md), mande:\n\n  {FRASE_GRAVACAO}\n")
    print("Resposta certa: uma linha nova no fim do IDEIAS.md no GitHub (e nada no STATUS.md), ou \"NÃO GRAVEI\" com a "
          "linha pronta para `status-projeto colar`. Depois descarte a ideia de teste: "
          "`status-projeto ideia estado ID --para descartada`.")
    sys.exit(0 if all(b for b, _, _ in res) else 2)


# =================================================================== ideias e erros (IDEIAS.md, ERROS.md)

def _recusa(f):
    def g(a):
        try:
            return f(a)
        except L.Recusa as e:
            sair(str(e), e.codigo)
    return g


def cmd_listas(a):
    """Cria IDEIAS.md e ERROS.md (se faltarem) e o merge=union deles no .gitattributes."""
    raiz = a.raiz
    precisa_config(raiz)
    criados = L.criar_arquivos(raiz)
    print(("Criados: " + ", ".join(criados)) if criados else "IDEIAS.md e ERROS.md já existem; nada foi mexido.")
    if garantir_union(raiz):
        print(".gitattributes: merge=union no IDEIAS.md e no ERROS.md acrescentado.")


def _det(a):
    return {"tela": getattr(a, "tela", ""), "aparelho": getattr(a, "aparelho", ""), "versao": getattr(a, "versao", "")}


def mostrar_ideias(raiz, cfg, todas, como_json):
    if todas:
        lst = L.itens_do_projeto(raiz, cfg, "ideia")
    else:
        lst = L.ideias_pendentes(raiz, cfg)
    if como_json:
        print(json.dumps([{k: v for k, v in x.items() if k not in ("repo_raiz", "linha", "ordem")} for x in lst],
                         ensure_ascii=False, indent=2))
        return
    if not lst:
        print("Nenhuma ideia pendente." if not todas else "Nenhuma ideia registrada.")
        return
    print(("Ideias (todas, com o estado)" if todas else f"Ideias pendentes ({len(lst)})") + " — IDEIAS.md")
    for x in lst:
        estado = f" · {x['estado']}" if todas else ""
        aviso = ""
        if x["estado"] == "pendente" and L.dias_desde(x["data"]) > L.DIAS_IDEIA_VELHA:
            aviso = f"\n    ⚠ pendente há {L.dias_desde(x['data'])} dias: pergunte se mantém ou descarta"
        print(f"- {x['id']} · {x['app']} · {c.data_br(x['criado'])}{estado} · {x['texto']}{aviso}")


def mostrar_erros(raiz, cfg, todos, como_json):
    lst = L.itens_do_projeto(raiz, cfg, "erro") if todos else L.erros_a_corrigir(raiz, cfg)
    for x in lst:
        x["falta"] = L.faltando(x)
    if como_json:
        print(json.dumps([{k: v for k, v in x.items() if k not in ("repo_raiz", "linha", "ordem")} for x in lst],
                         ensure_ascii=False, indent=2))
        return
    if not lst:
        print("Nenhum erro a corrigir." if not todos else "Nenhum erro registrado.")
        return
    grupos = collections.OrderedDict()
    for x in sorted(lst, key=lambda x: (x["estado"] != "aberto", x["estado"], x["gravidade"] != "grave", x["criado"])):
        grupos.setdefault(x["estado"], []).append(x)
    ab = len(grupos.get("aberto", []))
    print(f"Erros {'(todos)' if todos else 'a corrigir'} — ERROS.md: {ab} aberto(s)"
          + "".join(f", {len(v)} {k}" for k, v in grupos.items() if k != "aberto"))
    for estado, xs in grupos.items():
        print(f"\n{estado}:")
        for x in xs:
            g = " · GRAVE" if x["gravidade"] == "grave" else ""
            print(f"- {x['id']} · {x['app']} · {c.data_br(x['criado'])}{g} · {x['texto']}")
            print(f"    tela: {x.get('tela', '?')} · aparelho: {x.get('aparelho', '?')} · versão: {x.get('versao', '?')}")
            if x["falta"] and estado == "aberto":
                print(f"    ⚠ incompleto: falta {', '.join(x['falta'])} — pergunte agora "
                      f"(status-projeto erro completar {x['id']} --tela ... --aparelho ... --versao ...)")


@_recusa
def cmd_ideia(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    if a.acao == "anotar":
        it, cam = L.anotar(raiz, cfg, "ideia", " ".join(a.texto), app=a.app)
        print(f"Ideia anotada em {c.rel(L.caminho(cam, 'ideia'), raiz)}: {it['id']} · {it['app']} · {it['texto']}")
    elif a.acao == "estado":
        if not a.texto or not a.para:
            sair("Use: status-projeto ideia estado ID [ID...] --para 'virou FATIA_X' | descartada | pendente")
        for i, antes, depois in L.mudar(raiz, cfg, "ideia", a.texto, estado=a.para):
            print(f"{i}: {antes} → {depois}" + (" (mantida; conta 60 dias de novo)" if antes == depois == "pendente" else ""))
    else:
        mostrar_ideias(raiz, cfg, a.todas, a.json)


@_recusa
def cmd_erro(a):
    raiz = a.raiz
    cfg = precisa_config(raiz)
    if a.acao == "anotar":
        it, cam = L.anotar(raiz, cfg, "erro", " ".join(a.texto), app=a.app, grave=a.grave, det=_det(a),
                           fora_do_teste=a.fora_do_teste)
        print(f"Erro anotado em {c.rel(L.caminho(cam, 'erro'), raiz)}: {it['id']} · {it['app']} · "
              f"{it['gravidade']} · {it['texto']}")
        falta = L.faltando(it)
        if falta:
            print(f"Ficou incompleto (falta {', '.join(falta)}): pergunte quando a lista de erros for pedida.")
        if it["gravidade"] == "grave":
            print(f"ERRO GRAVE: ofereça montar a fatia de correção agora, no topo do 📦: "
                  f"status-projeto erro fatia --ids {it['id']} --gravar")
    elif a.acao in ("estado", "completar"):
        ids = list(a.texto or [])
        if a.fatia:
            ids += [x["id"] for x in L.itens_do_projeto(raiz, cfg, "erro") if x["estado"] == f"em {a.fatia}"]
            if not ids:
                sair(f"Nenhum erro em {a.fatia}.")
        if not ids:
            sair("Diga os ids (ou --fatia FATIA_CORRECOES_N).")
        if a.acao == "estado" and not a.para:
            sair("Use --para aberto | 'em FATIA_CORRECOES_N' | corrigido")
        det = _det(a)
        if a.acao == "completar" and not any(det.values()) and not a.grave and not a.normal:
            sair("Use --tela, --aparelho, --versao (e/ou --grave / --normal).")
        grav = "grave" if a.grave else "normal" if a.normal else None
        for i, antes, depois in L.mudar(raiz, cfg, "erro", ids, estado=a.para or None, det=det, gravidade=grav):
            it = L.achar(raiz, cfg, "erro", i)
            falta = L.faltando(it)
            print(f"{i}: {antes}" + (f" → {depois}" if antes != depois else "") +
                  (f" · ainda falta {', '.join(falta)}" if falta else " · completo"))
    elif a.acao == "fatia":
        plano = L.montar_fatia(raiz, cfg, ids=a.ids, topo=a.topo, app=a.app, gravar=a.gravar)
        if a.json:
            print(json.dumps(plano, ensure_ascii=False, indent=2))
            return
        print(("Fatia de correção gravada" if a.gravar else "Fatia de correção (prévia; nada gravado — confirme e rode com --gravar)")
              + f": {plano['arquivo']} [{plano['tamanho']}] com {len(plano['erros'])} erro(s), "
              + ("no TOPO do 📦 (vira a próxima)" if plano["topo"] else "no fim do 📦"))
        for ar, ids in plano["areas"].items():
            print(f"  {ar}: {', '.join(ids)}")
        if plano["incompletos"]:
            print("  incompletos (pergunte os dados): " + "; ".join(f"{k} falta {', '.join(v)}"
                                                                    for k, v in plano["incompletos"].items()))
        print(f"  STATUS.md 📦: {plano['item_status']}")
        if a.gravar:
            print(f"  erros marcados: em {plano['fatia']}. Mostre o git diff (commit só com 'pode commitar').")
    else:
        mostrar_erros(raiz, cfg, a.todos, a.json)


@_recusa
def cmd_colar(a):
    cfg = precisa_config(a.raiz)
    tipo, cam, gravou = L.colar(a.raiz, cfg, " ".join(a.linha))
    arq = c.rel(L.caminho(cam, tipo), a.raiz)
    print(f"Linha gravada no fim de {arq}." if gravou else f"Essa linha já está em {arq}; nada mudou.")


# =================================================================== main

def main():
    p = argparse.ArgumentParser(prog="status-projeto", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--raiz", default=None, help="pasta do repositório (padrão: a atual)")
    s = p.add_subparsers(dest="cmd")

    s.add_parser("estado", help="diagnóstico em JSON para o /instalar-status")
    x = s.add_parser("init", help="cria o config (primeira instalação)")
    x.add_argument("--usuario", required=True)
    x.add_argument("--valor", type=float, default=None, help="valor da hora (padrão 150; com taxa.csv, o dele)")
    x.add_argument("--valor-desde", default="", help="com taxa.csv e valor diferente: a partir de quando vale")
    x.add_argument("--pasta-fatias", default="fatias")
    x.add_argument("--pasta-executadas", default="")
    x.add_argument("--autor", action="append", help="só commits deste autor na estimativa (pode repetir)")
    x.add_argument("--repo", action="append", help="repo irmão (caminho relativo, pode repetir)")
    x = s.add_parser("status-md", help="cria (vazio) ou confere o STATUS.md")
    x.add_argument("--vazio", action="store_true", help="cria o STATUS.md com as 5 fases se não existir")
    x.add_argument("--completar-fases", action="store_true", help="acrescenta só as fases que faltam")
    x.add_argument("--cortar-concluidos", action="store_true",
                   help="mantém no ✅ só os últimos N dias e fecha com 'Versões anteriores: ver <arquivo>'")
    x.add_argument("--dias", type=int, default=None, help="com --cortar-concluidos: quantos dias (padrão 7)")
    x.add_argument("--ver", default="", help=f"para onde a linha aponta (padrão {ARQ_CONCLUIDOS}; .md recebe os itens tirados)")
    x.add_argument("--ajustar", action="append", metavar="TITULO=FASE",
                   help="troca uma seção fora do padrão pela fase padrão, juntando os itens (pode repetir)")
    x.add_argument("--marcar", action="store_true", help="marca a etapa status_md como feita")
    x = s.add_parser("excecao", help="registra no CLAUDE.md (fora do bloco) um arquivo de status lido por código")
    x.add_argument("arquivo", nargs="?", default="")
    x.add_argument("--motivo", default="", help="ex.: \"lido pelo versao:fechar\" (padrão: onde o código cita)")
    x.add_argument("--listar", action="store_true")
    x = s.add_parser("autonomo", help="scripts que chamam 'claude -p': confere/inclui STATUS_PROJETO_TIPO=autonomo")
    x.add_argument("--json", action="store_true")
    x.add_argument("--aplicar", action="append", metavar="ARQUIVO:LINHA", help="inclui a variável nessa chamada")
    x = s.add_parser("fatias-soltas", help="arquivos FATIA_* fora da pasta das fatias (versionados ou não)")
    x.add_argument("--json", action="store_true")
    x = s.add_parser("espalhado", help="lista status espalhado em outros arquivos")
    x.add_argument("--json", action="store_true")
    x = s.add_parser("contradicoes", help="instruções das fatias em 📦 que contradizem as regras do plugin")
    x.add_argument("--json", action="store_true")
    x.add_argument("--ignorar", action="append", metavar="ID", help="marca o apontamento como ignorado (no config)")
    x.add_argument("--desfazer", action="append", metavar="ID", help="volta a valer um apontamento ignorado")
    x.add_argument("--obs", default="", help="motivo (com --ignorar)")
    x.add_argument("--ignoradas", action="store_true", help="lista os ignorados")
    s.add_parser("estimar", help="estimativa de horas pelo git (uma vez só)")
    x = s.add_parser("claude-md", help="grava o bloco de regras no CLAUDE.md")
    x.add_argument("--mesmo-assim", action="store_true")
    s.add_parser("hooks", help="registra o plugin no projeto e confere hooks antigos")
    s.add_parser("gitattributes", help="merge=union no sessoes.csv")
    x = s.add_parser("gitignore", help="confere (e com --corrigir, ajusta) o .gitignore")
    x.add_argument("--corrigir", action="store_true")
    x = s.add_parser("guia", help="mostra o bloco ATENÇÃO (com --gravar, grava docs/COMO_USAR_STATUS.md)")
    x.add_argument("--gravar", action="store_true", help="grava o guia em docs/COMO_USAR_STATUS.md")
    x.add_argument("--marcar", action="store_true", help="com --gravar, marca a etapa guia como feita")
    x = s.add_parser("etapa", help="marca uma etapa como feita")
    x.add_argument("nome")
    x.add_argument("--valor", default=None)
    x = s.add_parser("reparar", help="lista o que falta ou quebrou")
    x.add_argument("--json", action="store_true")
    s.add_parser("atualizar", help="migra o config e atualiza o bloco do CLAUDE.md e o guia")
    x = s.add_parser("github", help="mostra (ou grava) o DONO/REPO do GitHub usado no guia")
    x.add_argument("dono_repo", nargs="?", default="")
    x = s.add_parser("repos", help="lista/adiciona/remove repos irmãos")
    x.add_argument("--adicionar", action="append")
    x.add_argument("--remover", action="append")
    x = s.add_parser("relatorio", help="horas e custo")
    x.add_argument("--todos", action="store_true", help="soma os repos irmãos do config")
    x.add_argument("--repo", action="append", help="soma também este repo")
    x = s.add_parser("valor", help="muda o valor da hora (sem efeito retroativo)")
    x.add_argument("valor")
    x.add_argument("--desde", default="")
    x.add_argument("--obs", default="")
    x = s.add_parser("historico", help="linha do tempo das fatias")
    x.add_argument("--todos", action="store_true")
    s.add_parser("cronograma", help="projeção das fatias em 📦")
    x = s.add_parser("resumo", help="o que mudou nos últimos dias")
    x.add_argument("--dias", type=int, default=3)
    s.add_parser("ajuda", help="estado do projeto + guia")
    s.add_parser("listas", help="cria IDEIAS.md e ERROS.md (se faltarem) com merge=union")
    x = s.add_parser("ideia", help="ideias pendentes (IDEIAS.md): listar, anotar, estado")
    x.add_argument("acao", nargs="?", default="listar", choices=["listar", "anotar", "estado"])
    x.add_argument("texto", nargs="*", help="anotar: o texto; estado: os ids")
    x.add_argument("--app", default="", help="app/repo do item (obrigatório em projeto com vários repos)")
    x.add_argument("--para", default="", help="estado: 'virou FATIA_X' | descartada | pendente (mantém)")
    x.add_argument("--todas", action="store_true", help="listar: também as que viraram fatia ou foram descartadas")
    x.add_argument("--json", action="store_true")
    x = s.add_parser("erro", help="erros a corrigir (ERROS.md): listar, anotar, completar, estado, fatia")
    x.add_argument("acao", nargs="?", default="listar", choices=["listar", "anotar", "completar", "estado", "fatia"])
    x.add_argument("texto", nargs="*", help="anotar: o texto; completar/estado/fatia: os ids")
    x.add_argument("--app", default="")
    x.add_argument("--grave", action="store_true")
    x.add_argument("--normal", action="store_true", help="completar: volta a gravidade para normal")
    x.add_argument("--tela", default="")
    x.add_argument("--aparelho", default="")
    x.add_argument("--versao", default="")
    x.add_argument("--para", default="", help="estado: aberto | 'em FATIA_CORRECOES_N' | corrigido")
    x.add_argument("--fatia", default="", help="estado/completar: todos os erros em FATIA_CORRECOES_N")
    x.add_argument("--ids", nargs="+", default=None, help="fatia: só estes erros")
    x.add_argument("--topo", action="store_true", help="fatia: no topo do 📦 (com erro grave, vai no topo sempre)")
    x.add_argument("--gravar", action="store_true", help="fatia: grava (sem isso, só mostra a prévia)")
    x.add_argument("--fora-do-teste", action="store_true", help="anotar com teste aberto: o erro não é da fatia em teste")
    x.add_argument("--todos", action="store_true", help="listar: também os corrigidos e testados")
    x.add_argument("--json", action="store_true")
    x = s.add_parser("colar", help="grava em IDEIAS.md/ERROS.md uma linha pronta (a que o claude.ai mostra)")
    x.add_argument("linha", nargs="+")
    s.add_parser("verificar", help="confere a integração")
    x = s.add_parser("instalacoes", help="instalações do plugin que valem aqui (user/project) e como ficar com uma")
    x.add_argument("--json", action="store_true")

    c.utf8_io()
    a = p.parse_args()
    if not a.cmd:
        p.print_help()
        return
    a.raiz = c.raiz_principal(a.raiz or os.getcwd())
    globals()["cmd_" + a.cmd.replace("-", "_")](a)


if __name__ == "__main__":
    main()
