"""Funções comuns do status-projeto (hook de tempo e comandos).

Só biblioteca padrão do Python 3.8+. Nada aqui grava texto de mensagens do usuário.
"""
import csv
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timedelta

FMT = "%Y-%m-%d %H:%M:%S"
PASTA_CFG = ".claude-status"
ARQ_CFG = os.path.join(PASTA_CFG, "config.json")
PASTA_LOCAL = os.path.join(PASTA_CFG, "local")  # estado da máquina, fora do git
PASTA_TEMPO = os.path.join("docs", "tempo")
CSV_SESSOES = os.path.join(PASTA_TEMPO, "sessoes.csv")
CSV_ESTIMATIVA = os.path.join(PASTA_TEMPO, "estimativa_git.csv")
CSV_TAXA = os.path.join(PASTA_TEMPO, "taxa.csv")  # opcional: quando o projeto já tem, é a fonte do valor da hora
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


def nome_plugin():
    try:
        with open(os.path.join(RAIZ_PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            return json.load(f).get("name", "status-projeto")
    except Exception:
        return "status-projeto"


# ---------------------------------------------------------------- instalações do plugin (installed_plugins.json)

ORDEM_ESCOPO = {"user": 0, "project": 1, "local": 2}  # no empate de versão, vence a user


def pasta_config_claude():
    """$CLAUDE_CONFIG_DIR ou ~/.claude."""
    d = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    return os.path.expanduser(d) if d else os.path.join(os.path.expanduser("~"), ".claude")


def chave_versao(v):
    """'1.11.0' → (1, 11, 0); '1.1.1-73c8cf' → (1, 1, 1). Comparável; o que não for número vira 0."""
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.]", re.split(r"[-+ ]", str(v or "0"))[0]))


def mesmo_caminho(a, b):
    if not a or not b:
        return False
    try:
        return os.path.normcase(os.path.realpath(barra(a))) == os.path.normcase(os.path.realpath(barra(b)))
    except Exception:
        return False


def _ler_json(p):
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _ativado(arq_settings, chave):
    """False só quando o settings.json daquele escopo diz enabledPlugins[chave] = false."""
    return _ler_json(arq_settings).get("enabledPlugins", {}).get(chave) is not False


def instalacoes_plugin(raiz, plugin_root=None):
    """As instalações do plugin que valem para o projeto `raiz`, lidas do installed_plugins.json.

    Vale a do escopo user e as project/local cujo projectPath é a raiz. Descarta (com motivo) a sem pasta e a
    desativada (enabledPlugins = false no settings do escopo). Vence a versão mais nova; no empate, a user.
    Devolve {arquivo, todas, validas, vencedora, esta, no_json, esta_vence}: `esta` é a entrada desta cópia do
    plugin entre as que valem aqui, `no_json` diz se a cópia aparece no JSON (não aparece com --plugin-dir) e
    `esta_vence` diz se o hook desta cópia deve gravar."""
    plugin_root = plugin_root or RAIZ_PLUGIN
    cfgdir = pasta_config_claude()
    arq = os.path.join(cfgdir, "plugins", "installed_plugins.json")
    nome = nome_plugin()
    todas, no_json = [], False
    for chave, lst in (_ler_json(arq).get("plugins") or {}).items():
        if chave.split("@", 1)[0] != nome or not isinstance(lst, list):
            continue
        for e in lst:
            if not isinstance(e, dict):
                continue
            no_json = no_json or mesmo_caminho(e.get("installPath"), plugin_root)
            escopo = e.get("scope") or "user"
            proj = e.get("projectPath") or ""
            if escopo != "user" and not mesmo_caminho(proj, raiz):
                continue  # instalação de outro projeto
            pasta = e.get("installPath") or ""
            if escopo == "user":
                sett = os.path.join(cfgdir, "settings.json")
            else:
                sett = os.path.join(proj, ".claude", "settings.local.json" if escopo == "local" else "settings.json")
            motivo = ""
            if not pasta or not os.path.isdir(pasta):
                motivo = "sem pasta"
            elif not _ativado(sett, chave):
                motivo = "desativada"
            todas.append({"chave": chave, "escopo": escopo, "versao": str(e.get("version") or "?"),
                          "pasta": pasta, "projeto": proj, "descartada": motivo,
                          "esta": mesmo_caminho(pasta, plugin_root)})
    validas = [x for x in todas if not x["descartada"]]
    validas.sort(key=lambda x: (tuple(-n for n in chave_versao(x["versao"])), ORDEM_ESCOPO.get(x["escopo"], 9)))
    vencedora = validas[0] if validas else None
    for x in todas:
        x["vence"] = x is vencedora
    esta = next((x for x in todas if x["esta"]), None)
    # fora do JSON (--plugin-dir): roda sempre; no JSON (mesmo que como instalação de outro projeto): só se vencer
    esta_vence = not no_json or vencedora is None or mesmo_caminho(vencedora["pasta"], plugin_root)
    return {"arquivo": arq, "todas": todas, "validas": validas, "vencedora": vencedora, "esta": esta,
            "no_json": no_json, "esta_vence": esta_vence}


def comandos_corrigir_instalacoes(info):
    """Comandos para ficar com uma instalação só (a user, na versão mais nova). [] se já há uma só."""
    validas = info["validas"]
    if len(validas) <= 1:
        return []
    chave = info["vencedora"]["chave"]
    mk = chave.split("@", 1)[1] if "@" in chave else nome_plugin()
    mais_nova = max(chave_versao(x["versao"]) for x in validas)
    user = next((x for x in validas if x["escopo"] == "user"), None)
    cmds = []
    if user is None:
        cmds += [f"claude plugin marketplace update {mk}", f"claude plugin install {chave} --scope user"]
    elif chave_versao(user["versao"]) < mais_nova:
        cmds += [f"claude plugin marketplace update {mk}", f"claude plugin update {chave} --scope user"]
    for x in validas:
        if x["escopo"] != "user":
            pref = f'cd "{x["projeto"]}" && ' if x["projeto"] else ""
            cmds.append(f"{pref}claude plugin uninstall {x['chave']} --scope {x['escopo']}")
    return cmds


def texto_instalacoes(info):
    """Linhas para mostrar ao usuário: cada instalação e, se houver mais de uma valendo, como corrigir."""
    if not info["todas"]:
        return ["Instalações do plugin: nenhuma no installed_plugins.json (esta cópia roda por --plugin-dir)."]
    linhas = ["Instalações do plugin que valem aqui:"]
    for x in info["todas"]:
        onde = f" em {x['projeto']}" if x["projeto"] else ""
        marca = "vence" if x["vence"] else (f"descartada: {x['descartada']}" if x["descartada"] else "perde: os hooks dela não gravam")
        linhas.append(f"  - {x['escopo']} {x['versao']}{onde} ({marca})" + (" ← esta" if x["esta"] else ""))
    if not info["no_json"]:
        linhas.append("  - esta cópia não está no installed_plugins.json (--plugin-dir): os hooks dela rodam")
    cmds = comandos_corrigir_instalacoes(info)
    if cmds:
        linhas.append(f"ATENÇÃO: {len(info['validas'])} instalações valendo ao mesmo tempo. Só a que vence grava o "
                      "tempo (versões anteriores à 1.12.0 não sabem disso e gravam também). Para ficar com uma só, "
                      "no escopo user, rode no terminal (o plugin não desinstala sozinho):")
        linhas += [f"    {cmd}" for cmd in cmds]
        linhas.append("  Depois, numa sessão aberta: /reload-plugins.")
    return linhas


# ---------------------------------------------------------------- Windows: texto e caminhos

def utf8_io():
    """stdout/stderr em UTF-8 (no Windows o padrão é cp1252, que quebra nos emojis das fases)."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def ler_stdin():
    """stdin em UTF-8 qualquer que seja o idioma do sistema (o JSON do hook traz acentos: 'vou começar a codar')."""
    try:
        return sys.stdin.buffer.read().decode("utf-8-sig", "replace")
    except Exception:
        return ""


def barra(p):
    """Caminho com '/' (o git e o STATUS.md usam '/'; no Windows pode vir 'fatias\\FATIA_X.md')."""
    return (p or "").replace("\\", "/")


def nome_pasta(p):
    """Nome da última pasta, aceitando '/' e '\\': 'Z:\\proj' → 'proj', '\\\\srv\\share\\app' → 'app',
    'Z:\\' → 'Z' (projeto na raiz da unidade)."""
    n = barra(p).rstrip("/")
    return n.rsplit("/", 1)[-1].rstrip(":") or "raiz"


def rel(p, base):
    """Caminho relativo com '/'; em outra unidade do Windows (C: × Z:) não há relativo: devolve o absoluto."""
    try:
        return os.path.relpath(p, base).replace(os.sep, "/")
    except ValueError:
        return p


def pasta_do_git_dir(git_dir, mod=os.path):
    """'C:/proj/.git' → 'C:\\proj'; 'Z:/.git' → 'Z:\\' (raiz da unidade); '//srv/share/app/.git' → '\\\\srv\\share\\app'.
    `mod` é o os.path do sistema (o teste passa ntpath para conferir o Windows no Linux)."""
    g = mod.normpath(git_dir)
    if mod.basename(g) != ".git":
        return ""
    return mod.dirname(g)


def eh_pasta_pessoal(p):
    try:
        casa = os.path.expanduser("~")
        return bool(casa) and os.path.normcase(os.path.realpath(p)) == os.path.normcase(os.path.realpath(casa))
    except Exception:
        return False


# ---------------------------------------------------------------- git

def git(cwd, *args, timeout=15):
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace", env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def raiz_principal(cwd):
    """Pasta do repositório principal (uma worktree grava no CSV do repositório principal)."""
    comum = pasta_do_git_dir(git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    if comum and os.path.isdir(comum):
        return comum
    top = git(cwd, "rev-parse", "--show-toplevel")
    return os.path.normpath(top) if top else os.path.abspath(cwd)


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
        "corte_concluidos_dias": 0,      # 0 = não corta o ✅; N = mantém só os últimos N dias
        "arquivo_concluidos": "",        # para onde aponta a linha "Versões anteriores: ver ..."
        "link_no_status": False,         # true: o link do roteiro de teste vai para o STATUS.md (só repo privado)
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
    for k in ("pasta_fatias", "pasta_fatias_executadas"):  # 'docs\\fatias' (config feito no Windows) → 'docs/fatias'
        if isinstance(cfg.get(k), str):
            cfg[k] = barra(cfg[k]).strip("/")
    tx = ler_taxa_csv(raiz)
    if tx:  # o taxa.csv do projeto manda; o config guarda uma cópia
        cfg["valor_hora"] = tx
    return cfg


def _coluna(campos, *pedacos):
    for k in campos:
        if any(p in k.lower() for p in pedacos):
            return k
    return None


def ler_taxa_csv(raiz):
    """[{desde, valor, obs}] do docs/tempo/taxa.csv (colunas tipo vigente_desde,valor_hora,observacao), ou None."""
    try:
        with open(os.path.join(raiz, CSV_TAXA), newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            campos = r.fieldnames or []
            cd, cv, co = _coluna(campos, "desde", "vigente", "data"), _coluna(campos, "valor"), _coluna(campos, "obs")
            if not cd or not cv:
                return None
            out = []
            for l in r:
                try:
                    v = float(str(l.get(cv) or "").replace(",", "."))
                except ValueError:
                    continue
                out.append({"desde": normaliza_desde(l.get(cd)), "valor": v, "obs": (l.get(co) or "") if co else ""})
            return sorted(out, key=lambda x: x["desde"]) or None
    except FileNotFoundError:
        return None


def acrescentar_taxa_csv(raiz, desde, valor, obs=""):
    """Acrescenta uma linha no fim do taxa.csv (as antigas não mudam), no formato de data que o arquivo já usa."""
    p = os.path.join(raiz, CSV_TAXA)
    with open(p, newline="", encoding="utf-8") as f:
        texto = f.read()
    campos = next(csv.reader([texto.splitlines()[0]]))
    cd, cv, co = _coluna(campos, "desde", "vigente", "data"), _coluna(campos, "valor"), _coluna(campos, "obs")
    d = desde.strftime("%Y-%m-%d") if desde.time() == datetime.min.time() else desde.strftime("%Y-%m-%d %H:%M")
    linha = {cd: d, cv: f"{valor:.2f}"}
    if co:
        linha[co] = obs
    fim = "\r\n" if texto.endswith("\r\n") else "\n"
    with open(p, "a", newline="", encoding="utf-8") as f:
        if texto and not texto.endswith(("\n", "\r")):
            f.write(fim)
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore", lineterminator=fim)
        w.writerow(linha)


def gravar_config(raiz, cfg):
    os.makedirs(os.path.join(raiz, PASTA_CFG), exist_ok=True)
    cfg["atualizado_em"] = agora_s()
    tmp = caminho_cfg(raiz) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
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
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
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
    # [1.15.0] Linhas de correção ficam sempre no fim (na ordem em que foram feitas): o hook regrava o arquivo nesta
    # ordem, e assim o nº de linha das sessões (o de 'status-projeto sessao listar') não muda depois de uma correção.
    return sorted(unicas.values(), key=lambda l: (e_correcao(l), l["sessao"].split("|", 2)[1] if e_correcao(l)
                                                  else l["inicio"]))


# ---------------------------------------------------------------- correção de sessão (1.15.0)
# Uma correção é uma LINHA A MAIS no sessoes.csv; nenhuma linha é apagada nem reescrita. Os dados dela vão no campo
# "sessao" (que os hooks nunca reescrevem): correcao|<quando>|<anular|ajustar>|<sessao>|<inicio>|<tipo>|<motivo>.
# inicio/fim/fatia/tipo da linha de correção = os valores corrigidos (anular: fim = inicio, tempo zero).
# A última correção (pelo <quando>) vale sobre a linha original, mesmo que o fim original seja mais tarde.
CORRECAO = "correcao"


def e_correcao(l):
    return (l.get("sessao") or "").startswith(CORRECAO + "|")


def ler_correcao(l):
    p = (l.get("sessao") or "").split("|", 6)
    if len(p) < 7 or p[0] != CORRECAO:
        return None
    return {"quando": p[1], "acao": p[2], "sessao": p[3], "inicio": p[4], "tipo": p[5], "motivo": p[6],
            "novo": {k: l.get(k, "") for k in ("inicio", "fim", "fatia", "tipo")}}


def chave_sessao(l):
    return (l.get("sessao", ""), l.get("inicio", ""), l.get("tipo", ""))


def correcoes(linhas):
    """{chave da linha original: a correção que vale (a mais recente)}."""
    out = {}
    for l in linhas:
        k = ler_correcao(l) if e_correcao(l) else None
        if k:
            chave = (k["sessao"], k["inicio"], k["tipo"])
            if chave not in out or k["quando"] >= out[chave]["quando"]:
                out[chave] = k
    return out


def aplicar_correcoes(linhas):
    """Linhas para relatório: sem as linhas de correção e com cada correção aplicada na linha original
    (marca 'corrigida' = motivo e, ao anular, 'anulada' = True). A leitura crua (ler_sessoes) não muda."""
    corr = correcoes(linhas)
    out = []
    for l in linhas:
        if e_correcao(l):
            continue
        k = corr.get(chave_sessao(l))
        if k:
            l = dict(l)
            if k["acao"] == "anular":
                l["fim"], l["anulada"] = l["inicio"], True
            else:
                for campo in ("inicio", "fim", "fatia", "tipo"):
                    if k["novo"].get(campo):
                        l[campo] = k["novo"][campo]
            l["estado"], l["corrigida"] = "fechada", k["motivo"]
        out.append(l)
    return sorted(out, key=lambda l: l["inicio"])


def ler_sessoes_corrigidas(caminho):
    return aplicar_correcoes(ler_sessoes(caminho))


def acrescentar_correcao(caminho, original, acao, motivo, novo=None, quando=None):
    """Acrescenta (no fim do arquivo, sem reescrever nada) a linha de correção da sessão 'original'."""
    novo = novo or {}
    motivo = re.sub(r"\s+", " ", str(motivo or "")).replace("|", "/").strip()[:200]
    quando = quando or agora_s()
    ini = novo.get("inicio") or original["inicio"]
    fim = ini if acao == "anular" else (novo.get("fim") or original["fim"] or ini)
    linha = {"inicio": ini, "fim": fim, "repo": original.get("repo", ""),
             "fatia": novo.get("fatia") or original.get("fatia", ""), "tipo": novo.get("tipo") or original["tipo"],
             "sessao": "|".join([CORRECAO, quando, acao, original["sessao"], original["inicio"], original["tipo"], motivo]),
             "estado": "fechada"}
    precisa_nl = False
    try:
        with open(caminho, "rb") as f:
            f.seek(0, 2)
            if f.tell():
                f.seek(-1, 2)
                precisa_nl = f.read(1) != b"\n"
    except FileNotFoundError:
        pass
    with open(caminho, "a", newline="", encoding="utf-8") as f:
        if precisa_nl:
            f.write("\n")
        csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore", lineterminator="\n").writerow(linha)
    return linha


def gravar_sessoes(caminho, linhas):
    tmp = caminho + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore", lineterminator="\n")  # sempre LF
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
# linha que fecha o ✅ depois do corte ("- Versões anteriores: ver docs/CONCLUIDOS.md"): não é item, não pede data
RE_VERSOES_ANT = re.compile(r"^(?:-\s+)?\**vers[õo]es\s+anteriores\**\s*:", re.I)


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
        if linha.startswith("- ") and RE_VERSOES_ANT.match(linha):
            item = None
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
        return re.sub(r"\.md$", "", nome_pasta(m.group(1)))
    primeira = re.split(r"\s+[—–]\s+|\s+-\s+|\(desde|;", t)[0]
    m = re.search(r"FATIA_[A-Za-z0-9_]+", primeira)
    if m:
        return m.group(0)
    nome = re.split(r"\s+\(|`", primeira)[0].strip(" *_:")
    if nome:
        return nome[:60]
    m = re.search(r"`([^`]+)`", t)
    return re.sub(r"\.md$", "", nome_pasta(m.group(1))) if m else t[:60]


def normaliza(nome):
    n = unicodedata.normalize("NFKD", (nome or "").strip().lower())
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    n = barra(n).split("/")[-1]
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
    lst = [(nome_pasta(raiz), raiz)]
    for r in cfg.get("repos", []) or []:
        cam = r.get("caminho") if isinstance(r, dict) else str(r)
        if not cam:
            continue
        cam = os.path.normpath(os.path.join(raiz, barra(cam)))  # '..\\outro' gravado no Windows vale no Linux
        if os.path.isdir(cam) and os.path.normcase(cam) != os.path.normcase(raiz):
            nome = (r.get("nome") if isinstance(r, dict) else "") or nome_pasta(cam)
            lst.append((nome, cam))
    return lst
