"""Funções comuns do status-projeto (hook de tempo e comandos).

Só biblioteca padrão do Python 3.8+. Nada aqui grava texto de mensagens do usuário.
"""
import csv
import json
import os
import re
import subprocess
import unicodedata
from datetime import datetime, timedelta

FMT = "%Y-%m-%d %H:%M:%S"
PASTA_CFG = ".claude-status"
ARQ_CFG = os.path.join(PASTA_CFG, "config.json")
PASTA_LOCAL = os.path.join(PASTA_CFG, "local")  # estado da máquina, fora do git
PASTA_TEMPO = os.path.join("docs", "tempo")
CSV_SESSOES = os.path.join(PASTA_TEMPO, "sessoes.csv")
CSV_ESTIMATIVA = os.path.join(PASTA_TEMPO, "estimativa_git.csv")
GUIA = os.path.join("docs", "COMO_USAR_STATUS.md")
CAMPOS = ["inicio", "fim", "repo", "fatia", "tipo", "sessao", "estado"]
CAMPOS_EST = ["inicio", "fim", "horas", "fatia", "tipo", "commits", "repo", "valor_hora", "custo"]
TIPOS = ("interativo", "autonomo", "teste", "planejamento")
NOME_TIPO = {"interativo": "interativo", "autonomo": "autônomo", "teste": "testando", "planejamento": "planejamento"}
INICIO_DOS_TEMPOS = "0001-01-01 00:00:00"

FASES = [
    ("🌐", "Codando"),
    ("📦", "Fatia pronta, não iniciada"),
    ("🧪", "Aguardando teste"),
    ("⏸️", "Bloqueado (externo)"),
    ("✅", "Concluído"),
]
ETAPAS = ["config", "status_md", "estimativa", "claude_md", "hooks", "gitattributes", "gitignore", "guia"]
VERSAO_CONFIG = 1
TAMANHOS = {"P": (0, 3), "M": (3, 10), "G": (10, None)}
PADRAO_TAMANHO_H = {"P": 2.0, "M": 6.0, "G": 14.0}  # só quando não há dado nenhum
RAIZ_PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def versao_plugin():
    try:
        with open(os.path.join(RAIZ_PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            return json.load(f).get("version", "0.0.0")
    except Exception:
        return "0.0.0"


# ---------------------------------------------------------------- git

def git(cwd, *args, timeout=15):
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def raiz_principal(cwd):
    """Pasta do repositório principal (uma worktree grava no CSV do repositório principal)."""
    comum = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if comum.endswith("/.git") and os.path.isdir(comum[:-5]):
        return comum[:-5]
    return git(cwd, "rev-parse", "--show-toplevel") or os.path.abspath(cwd)


def eh_repo_git(cwd):
    return git(cwd, "rev-parse", "--is-inside-work-tree") == "true"


def n_commits(raiz):
    out = git(raiz, "rev-list", "--all", "--count")
    return int(out) if out.isdigit() else 0


def dono_repo_da_url(url):
    """'DONO/REPO' de uma URL de remote, com qualquer host: git@github.com:D/R.git, git@github-zapai:D/R.git
    (apelido do ~/.ssh/config), https://github.com/D/R, ssh://git@host:22/D/R.git... Ou ''."""
    url = (url or "").strip()
    if url.lower().startswith("file:"):
        return ""
    m = re.match(r"^[a-z][a-z0-9+.-]*://[^/]+/(.+)$", url, re.I)  # esquema://[usuario@]host[:porta]/caminho
    if not m:
        m = re.match(r"^(?:[^@/\s]+@)?[^:/\s]+:/?(.+)$", url)    # [usuario@]host:caminho (estilo scp)
    if not m:
        return ""
    partes = [x for x in m.group(1).strip("/").split("/") if x]
    if len(partes) < 2:
        return ""
    dono, repo = partes[-2], re.sub(r"\.git$", "", partes[-1])
    ok = re.compile(r"^[A-Za-z0-9_.-]+$")
    return f"{dono}/{repo}" if repo and ok.match(dono) and ok.match(repo) else ""


def nome_remoto(raiz):
    """'origin' se existir; senão o primeiro remote do repo; ou ''."""
    nomes = git(raiz, "remote").split()
    return "origin" if "origin" in nomes else (nomes[0] if nomes else "")


def remoto_github(raiz):
    """'dono/repo': o informado no config (`repo_github`) ou o lido do remote (qualquer host); ou ''."""
    cfg = ler_config(raiz) or {}
    if cfg.get("repo_github"):
        return cfg["repo_github"]
    nome = nome_remoto(raiz)
    return dono_repo_da_url(git(raiz, "remote", "get-url", nome)) if nome else ""


def branch_padrao(raiz):
    ref = git(raiz, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    return ref.split("/", 1)[1] if "/" in ref else ""


# ---------------------------------------------------------------- config

def caminho_cfg(raiz):
    return os.path.join(raiz, ARQ_CFG)


def config_padrao():
    return {
        "versao_config": VERSAO_CONFIG,
        "versao_plugin": versao_plugin(),
        "instalado_em": "",
        "atualizado_em": "",
        "usuario": "",
        "moeda": "R$",
        "valor_hora": [],
        "repo_github": "",
        "pasta_fatias": "fatias",
        "pasta_fatias_executadas": "fatias_executadas",
        "projeto_novo": False,
        "repos": [],
        "autores_git": [],
        "ocioso_min": 30,
        "horas_dia": 8,
        "autonomo_processos": [],
        "contradicoes_ignoradas": [],
        "etapas": {},
    }


def migrar(cfg):
    """Completa um config antigo com os campos novos, sem apagar nada. Devolve (cfg, mudou)."""
    mudou = False
    base = config_padrao()
    for k, v in base.items():
        if k not in cfg:
            cfg[k] = v
            mudou = True
    # versões futuras: transformar campos aqui, conforme cfg["versao_config"]
    if not isinstance(cfg.get("valor_hora"), list):
        cfg["valor_hora"] = [{"desde": INICIO_DOS_TEMPOS, "valor": float(cfg["valor_hora"] or 0), "obs": "migrado"}]
        mudou = True
    if cfg.get("versao_config", 0) < VERSAO_CONFIG:
        cfg["versao_config"] = VERSAO_CONFIG
        mudou = True
    return cfg, mudou


def ler_config(raiz):
    try:
        with open(caminho_cfg(raiz), encoding="utf-8") as f:
            cfg = json.load(f)
    except (FileNotFoundError, ValueError):
        return None
    cfg, _ = migrar(cfg)
    return cfg


def gravar_config(raiz, cfg):
    os.makedirs(os.path.join(raiz, PASTA_CFG), exist_ok=True)
    cfg["atualizado_em"] = agora_s()
    tmp = caminho_cfg(raiz) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, caminho_cfg(raiz))


def estado_local(raiz):
    p = os.path.join(raiz, PASTA_LOCAL, "estado.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def gravar_estado_local(raiz, est):
    pasta = os.path.join(raiz, PASTA_LOCAL)
    os.makedirs(pasta, exist_ok=True)
    tmp = os.path.join(pasta, "estado.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(est, f, ensure_ascii=False)
    os.replace(tmp, os.path.join(pasta, "estado.json"))


# ---------------------------------------------------------------- datas e dinheiro

def agora():
    return datetime.now().replace(microsecond=0)


def agora_s():
    return agora().strftime(FMT)


def para_dt(s):
    s = (s or "").strip()
    for fmt in (FMT, "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def normaliza_desde(s):
    dt = para_dt(s)
    return dt.strftime(FMT) if dt and dt.year >= 1900 else INICIO_DOS_TEMPOS


def ddmm(dt):
    return dt.strftime("%d/%m") if dt else "?"


def data_br(s):
    dt = para_dt(s) if s else None
    if not s or s.startswith("0001") or (dt and dt.year < 1900):
        return "o início"
    if not dt:
        return s
    return dt.strftime("%d/%m/%Y") if dt.time() == datetime.min.time() else dt.strftime("%d/%m/%Y %H:%M")


def dinheiro(v, moeda="R$"):
    return f"{moeda} " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def dias_txt(h, por_dia=8):
    return f"{h / por_dia:.1f}".replace(".", ",")


def horas_txt(h):
    return f"{h:.1f}".replace(".", ",") + " h"


def taxas(cfg):
    lst = sorted(((normaliza_desde(t.get("desde")), float(t.get("valor", 0))) for t in cfg.get("valor_hora", [])))
    return lst or [(INICIO_DOS_TEMPOS, 0.0)]


def taxa_em(cfg_ou_taxas, dt):
    lst = cfg_ou_taxas if isinstance(cfg_ou_taxas, list) else taxas(cfg_ou_taxas)
    s = dt.strftime(FMT) if isinstance(dt, datetime) else str(dt)
    vale = [v for d, v in lst if d <= s]
    return vale[-1] if vale else lst[0][1]


# ---------------------------------------------------------------- sessões (CSV)

def ler_sessoes(caminho):
    """Lê o sessoes.csv. Depois de um merge=union a mesma sessão pode vir em duas versões:
    fica a de fim mais tarde (e, empatando, a fechada)."""
    try:
        with open(caminho, newline="", encoding="utf-8") as f:
            linhas = [l for l in csv.DictReader(f) if l.get("inicio") and l.get("inicio") != "inicio"]
    except FileNotFoundError:
        return []
    unicas = {}
    for l in linhas:
        for k in CAMPOS:
            l[k] = l.get(k) or ""
        chave = (l["sessao"], l["inicio"], l["tipo"])
        velha = unicas.get(chave)
        nova = (l["fim"], l["estado"] == "fechada")
        if velha is None or nova > (velha["fim"], velha["estado"] == "fechada"):
            unicas[chave] = l
    return sorted(unicas.values(), key=lambda l: l["inicio"])


def gravar_sessoes(caminho, linhas):
    tmp = caminho + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore")
        w.writeheader()
        for l in linhas:
            w.writerow({k: l.get(k, "") for k in CAMPOS})
    os.replace(tmp, caminho)


def ler_estimativa(caminho):
    try:
        with open(caminho, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return None


# ---------------------------------------------------------------- STATUS.md

RE_FASE = re.compile(r"^##\s*(🌐|📦|🧪|⏸️|⏸|✅)")
RE_DESDE = re.compile(r"\(desde\s+(\d{1,2}/\d{1,2}(?:/\d{2,4})?|\?)\s*\)")
RE_TAM = re.compile(r"^\[(P|M|G)\]\s*")


def emoji_fase(e):
    return "⏸️" if e.startswith("⏸") else e


def ler_status(texto):
    """{emoji: [item]}; item = {texto, sub, tamanho, desde, nome, linha}. Só itens '- ' na coluna 0."""
    fases = {e: [] for e, _ in FASES}
    presentes = set()
    atual, item = None, None
    for i, linha in enumerate(texto.splitlines(), 1):
        m = RE_FASE.match(linha)
        if m:
            atual, item = emoji_fase(m.group(1)), None
            presentes.add(atual)
            continue
        if linha.startswith("## "):
            atual, item = None, None
            continue
        if atual is None:
            continue
        if linha.startswith("- "):
            t = linha[2:].strip()
            item = {"texto": t, "sub": [], "linha": i}
            fases[atual].append(item)
        elif item is not None and linha[:1] in (" ", "\t") and linha.strip():
            item["sub"].append(linha.strip())
            item["texto_completo"] = True
        elif not linha.strip():
            continue
        else:
            item = None
    for e, itens in fases.items():
        for it in itens:
            tudo = " ".join([it["texto"]] + it["sub"])
            m = RE_TAM.match(it["texto"]) or re.search(r"\[(P|M|G)\]", it["texto"])
            it["tamanho"] = m.group(1) if m else ""
            ds = RE_DESDE.findall(tudo)
            it["desde"] = ds[-1] if ds else ""
            it["nome"] = nome_item(it["texto"])
    return fases, presentes


def ler_status_arquivo(raiz):
    try:
        with open(os.path.join(raiz, "STATUS.md"), encoding="utf-8") as f:
            return ler_status(f.read())
    except FileNotFoundError:
        return None, set()


def nome_item(texto):
    """Nome da fatia de um item: caminho entre crases no começo → FATIA_X da primeira parte → começo do texto."""
    t = re.sub(r"\[(P|M|G)\]\s*", "", texto).replace("**", "").strip()
    m = re.match(r"`([^`]+)`", t)
    if m:
        return re.sub(r"\.md$", "", os.path.basename(m.group(1).rstrip("/")))
    primeira = re.split(r"\s+[—–]\s+|\s+-\s+|\(desde|;", t)[0]
    m = re.search(r"FATIA_[A-Za-z0-9_]+", primeira)
    if m:
        return m.group(0)
    nome = re.split(r"\s+\(|`", primeira)[0].strip(" *_:")
    if nome:
        return nome[:60]
    m = re.search(r"`([^`]+)`", t)
    return re.sub(r"\.md$", "", os.path.basename(m.group(1).rstrip("/"))) if m else t[:60]


def normaliza(nome):
    n = unicodedata.normalize("NFKD", (nome or "").strip().lower())
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    n = n.split("/")[-1]
    n = re.sub(r"\.md$", "", n)
    n = re.sub(r"^(fatia|feat|feature|fix|slice)[_\-]+", "", n)
    n = re.sub(r"[^0-9a-z]+", "_", n).strip("_")
    return n


def mesma_fatia(a, b):
    na, nb = normaliza(a), normaliza(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    curto, longo = sorted((na, nb), key=len)
    return len(curto) >= 4 and longo.startswith(curto)


def data_do_desde(desde, hoje=None):
    """'20/11' → datetime (ano atual; se ficar no futuro, ano anterior)."""
    hoje = hoje or agora()
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", desde or "")
    if not m:
        return None
    d, mes, ano = int(m.group(1)), int(m.group(2)), m.group(3)
    try:
        if ano:
            a = int(ano)
            return datetime(a + 2000 if a < 100 else a, mes, d)
        dt = datetime(hoje.year, mes, d)
        return dt.replace(year=hoje.year - 1) if dt > hoje + timedelta(days=1) else dt
    except ValueError:
        return None


def fatias_codando(raiz):
    fases, _ = ler_status_arquivo(raiz)
    return fases["🌐"] if fases else []


def fatia_atual(cwd, raiz):
    """Branch de trabalho (fora da principal) ou os itens em 🌐 do STATUS.md. Só o nome."""
    branch = git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    principais = {"main", "master", "HEAD", "develop", "trunk", branch_padrao(raiz)}
    if branch and branch not in principais:
        return branch[:60]
    nomes = [it["nome"] for it in fatias_codando(raiz)]
    return " + ".join(n for n in nomes if n)[:120] or ""


def repos_do_projeto(raiz, cfg):
    """[(nome, caminho)] deste repo + irmãos que existirem."""
    lst = [(os.path.basename(raiz), raiz)]
    for r in cfg.get("repos", []) or []:
        cam = r.get("caminho") if isinstance(r, dict) else str(r)
        if not cam:
            continue
        cam = os.path.normpath(os.path.join(raiz, cam))
        if os.path.isdir(cam) and cam != raiz:
            nome = (r.get("nome") if isinstance(r, dict) else "") or os.path.basename(cam)
            lst.append((nome, cam))
    return lst
