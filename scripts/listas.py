"""Ideias pendentes (IDEIAS.md) e erros a corrigir (ERROS.md) do status-projeto.

Cada arquivo é um registro só de acréscimo: uma linha por registro, nunca apagada. Mudar o estado de um item é
acrescentar uma linha nova com o mesmo id; vale a última de cada id. Assim o merge=union junta o que veio do
Claude Code e do claude.ai sem conflito.

  IDEIAS.md: - ID | AAAA-MM-DD HH:MM | app | estado | texto
  ERROS.md:  - ID | AAAA-MM-DD HH:MM | app | estado | gravidade | completo/incompleto | tela: X · aparelho: Y · versão: Z | texto
"""
import os
import re
import random
from datetime import timedelta

import comum as c

ARQ = {"ideia": "IDEIAS.md", "erro": "ERROS.md"}
PREFIXO = {"ideia": "I", "erro": "E"}
N_CAMPOS = {"ideia": 5, "erro": 8}
DETALHES = (("tela", "tela"), ("aparelho", "aparelho"), ("versao", "versão"))
DIAS_IDEIA_VELHA = 60
RE_REG = re.compile(r"^- ([IE]-\d{6}-\d{4}[a-z0-9]{0,4}) \| ")
RE_FATIA_COR = re.compile(r"FATIA_CORRECOES_(\d+)")

CABECALHO = {
    "ideia": """# IDEIAS — {projeto}

Ideias pendentes do projeto (plugin status-projeto). Não é status: o status fica só no `STATUS.md`.
Uma linha por registro, sempre acrescentada no fim; **nada é apagado**. Para mudar o estado, acrescenta-se uma linha
nova com o mesmo id (vale a última de cada id).
Formato: `- ID | AAAA-MM-DD HH:MM | app | estado | texto` (id: `I-AAMMDD-HHMM` + 2 letras).
Estados: `pendente` → `virou FATIA_X` | `descartada`.
No Claude Code: "anota a ideia: ...", "quais ideias pendentes?" ou `/status-ideias`.

## Registros
""",
    "erro": """# ERROS — {projeto}

Erros a corrigir (plugin status-projeto). Não é status: o status fica só no `STATUS.md`.
Uma linha por registro, sempre acrescentada no fim; **nada é apagado**. Para mudar o estado ou completar os dados,
acrescenta-se uma linha nova com o mesmo id (vale a última de cada id).
Formato: `- ID | AAAA-MM-DD HH:MM | app | estado | gravidade | completo/incompleto | tela: X · aparelho: Y · versão: Z | texto`
(id: `E-AAMMDD-HHMM` + 2 letras; o que não se sabe fica `?` e o item fica `incompleto`).
Estados: `aberto` → `em FATIA_CORRECOES_N` → `corrigido e testado`. Gravidade: `grave` ou `normal`.
Erro achado no teste de uma fatia em 🧪 não entra aqui: é teste reprovado e a fatia volta para 🌐.
No Claude Code: "anota o erro: ...", "quais erros a corrigir?", "monta a fatia de correção" ou `/status-erros`.

## Registros
""",
}


class Recusa(Exception):
    """Pedido que não dá para cumprir; `codigo` 3 = precisa de decisão do usuário."""

    def __init__(self, msg, codigo=1):
        super().__init__(msg)
        self.codigo = codigo


# ---------------------------------------------------------------- arquivos

def caminho(raiz, tipo):
    return os.path.join(raiz, ARQ[tipo])


def criar_arquivos(raiz):
    """Cria IDEIAS.md e ERROS.md se faltarem (nunca sobrescreve). Devolve os criados."""
    criados = []
    for tipo in ("ideia", "erro"):
        p = caminho(raiz, tipo)
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(CABECALHO[tipo].format(projeto=c.nome_pasta(raiz)))
            criados.append(ARQ[tipo])
    return criados


def acrescentar(raiz, tipo, linha):
    p = caminho(raiz, tipo)
    if not os.path.exists(p):
        criar_arquivos(raiz)
    with open(p, encoding="utf-8") as f:
        texto = f.read()
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        if texto and not texto.endswith("\n"):
            f.write("\n")
        f.write(linha + "\n")


def limpa(s):
    """Um campo numa linha só e sem o separador ' | '."""
    return " ".join(str(s or "").split()).replace(" | ", " / ").strip()


# ---------------------------------------------------------------- leitura

def ler_registros(raiz, tipo):
    """[registro] na ordem do arquivo; registro = dict com os campos (e 'ordem')."""
    try:
        with open(caminho(raiz, tipo), encoding="utf-8") as f:
            linhas = f.read().splitlines()
    except FileNotFoundError:
        return []
    out = []
    for i, l in enumerate(linhas):
        if not RE_REG.match(l):
            continue
        p = [x.strip() for x in l[2:].split(" | ", N_CAMPOS[tipo] - 1)]
        if len(p) < N_CAMPOS[tipo] or p[0][0] != PREFIXO[tipo]:
            continue
        r = {"id": p[0], "data": p[1], "app": p[2], "estado": p[3], "ordem": i, "linha": l}
        if tipo == "ideia":
            r["texto"] = p[4]
        else:
            r["gravidade"], r["marca"], r["texto"] = p[4], p[5], p[7]
            r.update(ler_detalhes(p[6]))
        out.append(r)
    return out


def ler_detalhes(s):
    d = {k: "?" for k, _ in DETALHES}
    for parte in s.split("·"):
        k, _, v = parte.partition(":")
        k = c.normaliza(k)
        for chave, _ in DETALHES:
            if k == chave:
                d[chave] = v.strip() or "?"
    return d


def itens(raiz, tipo):
    """{id: item}: o estado atual de cada id (a última linha; empate de data → a que vem depois no arquivo)."""
    regs = ler_registros(raiz, tipo)
    por_id = {}
    for r in sorted(regs, key=lambda r: (r["data"], r["ordem"])):
        velho = por_id.get(r["id"])
        r["criado"] = velho["criado"] if velho else r["data"]
        r["registros"] = (velho["registros"] if velho else 0) + 1
        r["repo_raiz"] = raiz
        por_id[r["id"]] = r
    return por_id


def itens_do_projeto(raiz, cfg, tipo):
    out = []
    for nome, cam in c.repos_do_projeto(raiz, cfg):
        for it in itens(cam, tipo).values():
            it["repo"] = nome
            out.append(it)
    return sorted(out, key=lambda it: it["criado"])


def achar(raiz, cfg, tipo, ident):
    for it in itens_do_projeto(raiz, cfg, tipo):
        if it["id"] == ident:
            return it
    raise Recusa(f"{ident} não encontrado em {ARQ[tipo]} (nem nos repos irmãos). Ids: `status-projeto {tipo} listar --todas`.")


# ---------------------------------------------------------------- escrita

def novo_id(raiz, tipo, agora):
    """Data e hora + 2 letras ao acaso: dois registros no mesmo minuto em lugares diferentes (dois ramos, Claude Code
    e claude.ai) não ganham o mesmo id depois do merge=union."""
    base = f"{PREFIXO[tipo]}-{agora:%y%m%d-%H%M}"
    usados = {r["id"] for r in ler_registros(raiz, tipo)}
    while True:
        ident = base + "".join(random.choice("abcdefghijkmnpqrstuvwxyz") for _ in range(2))
        if ident not in usados:
            return ident


def destino(raiz, cfg, app):
    """(raiz do repo, etiqueta do app). Projeto com vários repos: o app tem de ser um deles (na dúvida, perguntar)."""
    repos = c.repos_do_projeto(raiz, cfg)
    if len(repos) == 1:
        return raiz, limpa(app) or repos[0][0]
    if not app:
        raise Recusa("Projeto com vários repos (" + ", ".join(n for n, _ in repos) + "): de qual app é? "
                     "Se não der para saber pelo que foi dito, pergunte ao usuário e rode de novo com --app NOME.", 3)
    for nome, cam in repos:
        if c.normaliza(nome) == c.normaliza(app):
            return cam, nome
    raise Recusa(f"App '{app}' não é um dos repos do projeto (" + ", ".join(n for n, _ in repos) + "). "
                 "Pergunte ao usuário qual é.", 3)


def detalhes_txt(d):
    return " · ".join(f"{rot}: {limpa(d.get(k)) or '?'}" for k, rot in DETALHES)


def faltando(d):
    return [rot for k, rot in DETALHES if (d.get(k) or "?").strip() in ("", "?")]


def linha_ideia(ident, data, app, estado, texto):
    return f"- {ident} | {data} | {limpa(app)} | {estado} | {limpa(texto)}"


def linha_erro(ident, data, app, estado, gravidade, det, texto):
    marca = "incompleto" if faltando(det) else "completo"
    return f"- {ident} | {data} | {limpa(app)} | {estado} | {gravidade} | {marca} | {detalhes_txt(det)} | {limpa(texto)}"


def teste_aberto(raiz):
    sess = c.ler_sessoes_corrigidas(os.path.join(raiz, c.CSV_SESSOES))  # [1.15.0] teste anulado não está aberto
    return next((l for l in sess if l["tipo"] == "teste" and l["estado"] != "fechada"), None)


def anotar(raiz, cfg, tipo, texto, app="", grave=False, det=None, fora_do_teste=False):
    """Grava na hora, do jeito que foi dito. Devolve (item, repo)."""
    texto = limpa(texto)
    if not texto:
        raise Recusa("Falta o texto (o que foi dito depois de 'anota a ideia:' / 'anota o erro:').")
    cam, app = destino(raiz, cfg, app)
    if tipo == "erro" and not fora_do_teste:
        t = teste_aberto(cam)
        if t:
            raise Recusa(f"Há um teste aberto de {t['fatia'] or 'uma fatia'} (desde {c.data_br(t['inicio'])}). Erro "
                         "achado no teste de uma fatia em 🧪 não entra no ERROS.md: é teste reprovado e a fatia volta "
                         "para 🌐 (com o erro em Pendente:). Se o erro não for dessa fatia, rode de novo com "
                         "--fora-do-teste.", 3)
    agora = c.agora()
    ident = novo_id(cam, tipo, agora)
    data = agora.strftime("%Y-%m-%d %H:%M")
    if tipo == "ideia":
        linha = linha_ideia(ident, data, app, "pendente", texto)
    else:
        linha = linha_erro(ident, data, app, "aberto", "grave" if grave else "normal", det or {}, texto)
    acrescentar(cam, tipo, linha)
    return itens(cam, tipo)[ident], cam


def colar(raiz, cfg, linha):
    """Grava uma linha já pronta (a que o claude.ai mostra quando não consegue gravar), sem mudar id nem data."""
    linha = linha.strip()
    if not linha.startswith("- "):
        linha = "- " + linha
    tipo = "ideia" if linha.startswith("- I-") else "erro" if linha.startswith("- E-") else ""
    if not tipo or not RE_REG.match(linha):
        raise Recusa("Linha fora do formato: começa com '- I-AAMMDDHHMM... | ' (ideia) ou '- E-... | ' (erro), ex.: '- I-261121-1430ca | '.")
    p = [x.strip() for x in linha[2:].split(" | ", N_CAMPOS[tipo] - 1)]
    if len(p) < N_CAMPOS[tipo] or not c.para_dt(p[1]):
        raise Recusa(f"Linha fora do formato de {ARQ[tipo]}: precisa de {N_CAMPOS[tipo]} campos separados por ' | ' "
                     "e a data como AAAA-MM-DD HH:MM.")
    cam, app = destino(raiz, cfg, p[2])
    if any(r["linha"].strip() == linha for r in ler_registros(cam, tipo)):
        return tipo, cam, False
    if tipo == "ideia":
        nova = linha_ideia(p[0], p[1], app, p[3], p[4])
    else:
        nova = linha_erro(p[0], p[1], app, p[3], p[4], ler_detalhes(p[6]), p[7])
    acrescentar(cam, tipo, nova)
    return tipo, cam, True


ESTADOS_IDEIA = "pendente · virou FATIA_X · descartada"
ESTADOS_ERRO = "aberto · em FATIA_CORRECOES_N · corrigido e testado"


def normaliza_estado(tipo, s):
    t = " ".join((s or "").split())
    b = c.normaliza(t)
    if tipo == "ideia":
        if b in ("pendente", "manter", "mantem", "mantida"):
            return "pendente"
        if b in ("descartada", "descartar", "descarta", "descartado"):
            return "descartada"
        m = re.match(r"^(?:virou\s+)?(FATIA_[A-Za-z0-9_]+)$", t)
        if m:
            return f"virou {m.group(1)}"
        raise Recusa(f"Estado de ideia inválido: '{s}'. Use: {ESTADOS_IDEIA}.")
    if b in ("aberto", "reabrir", "aberta"):
        return "aberto"
    if b in ("corrigido", "corrigido_e_testado", "corrigida", "testado"):
        return "corrigido e testado"
    m = re.match(r"^(?:em\s+)?(FATIA_CORRECOES_\d+)$", t)
    if m:
        return f"em {m.group(1)}"
    raise Recusa(f"Estado de erro inválido: '{s}'. Use: {ESTADOS_ERRO}.")


def mudar(raiz, cfg, tipo, idents, estado=None, det=None, gravidade=None):
    """Acrescenta uma linha por id com o estado (e/ou os dados) novos. Devolve [(id, antes, depois)]."""
    if estado:
        estado = normaliza_estado(tipo, estado)
    agora = c.agora().strftime("%Y-%m-%d %H:%M")
    feitos = []
    for ident in idents:
        it = achar(raiz, cfg, tipo, ident)
        novo_estado = estado or it["estado"]
        data = max(agora, it["data"])  # nunca antes da última linha do id
        if tipo == "ideia":
            linha = linha_ideia(it["id"], data, it["app"], novo_estado, it["texto"])
        else:
            d = {k: it.get(k, "?") for k, _ in DETALHES}
            for k, v in (det or {}).items():
                if v:
                    d[k] = v
            linha = linha_erro(it["id"], data, it["app"], novo_estado, gravidade or it["gravidade"], d, it["texto"])
        acrescentar(it["repo_raiz"], tipo, linha)
        feitos.append((it["id"], it["estado"], novo_estado))
    return feitos


# ---------------------------------------------------------------- consultas

def dias_desde(s, agora=None):
    dt = c.para_dt(s)
    return ((agora or c.agora()) - dt).days if dt else 0


def ideias_pendentes(raiz, cfg):
    out = []
    for it in itens_do_projeto(raiz, cfg, "ideia"):
        if it["estado"] == "pendente":
            it["dias"] = dias_desde(it["data"])
            it["velha"] = it["dias"] > DIAS_IDEIA_VELHA
            out.append(it)
    return out


def erros_a_corrigir(raiz, cfg):
    out = []
    for it in itens_do_projeto(raiz, cfg, "erro"):
        if it["estado"] != "corrigido e testado":
            it["falta"] = faltando(it)
            out.append(it)
    return out


def contagem(raiz, cfg):
    ids = ideias_pendentes(raiz, cfg)
    err = erros_a_corrigir(raiz, cfg)
    ab = [e for e in err if e["estado"] == "aberto"]
    return {"ideias_pendentes": len(ids), "ideias_velhas": sum(i["velha"] for i in ids),
            "erros_abertos": len(ab), "erros_graves": sum(e["gravidade"] == "grave" for e in ab),
            "erros_incompletos": sum(bool(e["falta"]) for e in ab),
            "erros_em_correcao": len(err) - len(ab)}


def contagem_txt(raiz, cfg):
    n = contagem(raiz, cfg)
    t = f"Ideias pendentes: {n['ideias_pendentes']}"
    if n["ideias_velhas"]:
        t += f" ({n['ideias_velhas']} há mais de {DIAS_IDEIA_VELHA} dias)"
    t += f" · Erros abertos: {n['erros_abertos']}"
    extra = [f"{n['erros_graves']} grave(s)"] * bool(n["erros_graves"]) + \
            [f"{n['erros_incompletos']} incompleto(s)"] * bool(n["erros_incompletos"])
    if extra:
        t += " (" + ", ".join(extra) + ")"
    if n["erros_em_correcao"]:
        t += f" · em fatia de correção: {n['erros_em_correcao']}"
    return t


# ---------------------------------------------------------------- fatia de correção

def proximo_n(raiz, cfg):
    textos = [os.path.basename(x) for d in (cfg.get("pasta_fatias", "fatias"), cfg.get("pasta_fatias_executadas",
                                                                                         "fatias_executadas"))
              if os.path.isdir(os.path.join(raiz, d)) for x in os.listdir(os.path.join(raiz, d))]
    for arq in ("STATUS.md", ARQ["erro"]):
        try:
            with open(os.path.join(raiz, arq), encoding="utf-8") as f:
                textos.append(f.read())
        except FileNotFoundError:
            pass
    ns = [int(n) for t in textos for n in RE_FATIA_COR.findall(t)]
    return max(ns, default=0) + 1


def tamanho_por_qtd(n):
    return "P" if n <= 3 else "M" if n <= 8 else "G"


def area(it):
    return it.get("tela") if it.get("tela") not in ("", "?", None) else "sem tela definida"


def inserir_no_pacote(texto, linha, topo):
    """Põe `linha` como item da fase 📦: no topo (vira a próxima) ou no fim. Tira o '(nada agora)'."""
    linhas = texto.split("\n")
    ini = next((i for i, l in enumerate(linhas) if c.RE_FASE.match(l) and "📦" in l), None)
    if ini is None:
        raise Recusa("STATUS.md sem a fase 📦 (rode `status-projeto status-md --completar-fases`).")
    fim = next((i for i in range(ini + 1, len(linhas)) if linhas[i].startswith("## ")), len(linhas))
    corpo = [l for l in linhas[ini + 1:fim] if l.strip() != "(nada agora)"]
    itens_idx = [i for i, l in enumerate(corpo) if l.startswith("- ")]
    if topo and itens_idx:
        pos = itens_idx[0]
    else:
        pos = len(corpo)
        while pos > 0 and not corpo[pos - 1].strip():
            pos -= 1
    corpo.insert(pos, linha)
    if not corpo or corpo[-1].strip():
        corpo.append("")
    return "\n".join(linhas[:ini + 1] + corpo + linhas[fim:])


def montar_fatia(raiz, cfg, ids=None, topo=False, app="", gravar=False):
    """Agrupa os erros abertos por área (tela) numa FATIA_CORRECOES_N. Sem `gravar`, só mostra o plano."""
    cam, app = destino(raiz, cfg, app) if (app or len(c.repos_do_projeto(raiz, cfg)) > 1) else (raiz, "")
    abertos = [e for e in itens(cam, "erro").values() if e["estado"] == "aberto"]
    if ids:
        por_id = {e["id"]: e for e in itens(cam, "erro").values()}
        for i in ids:
            if i not in por_id:
                raise Recusa(f"{i} não está no ERROS.md de {c.nome_pasta(cam)}.")
            if por_id[i]["estado"] != "aberto":
                raise Recusa(f"{i} não está aberto (está '{por_id[i]['estado']}').")
        abertos = [e for e in abertos if e["id"] in ids]
    if not abertos:
        raise Recusa("Nenhum erro aberto no ERROS.md" + (f" de {c.nome_pasta(cam)}" if app else "") + ".")
    abertos.sort(key=lambda e: (e["gravidade"] != "grave", e["criado"]))
    grupos = {}
    for e in abertos:
        grupos.setdefault(area(e), []).append(e)
    ordem = sorted(grupos, key=lambda a: (a == "sem tela definida", min(e["gravidade"] != "grave" for e in grupos[a]), a))
    n = proximo_n(cam, cfg)
    nome = f"FATIA_CORRECOES_{n}"
    tam = tamanho_por_qtd(len(abertos))
    pf = cfg.get("pasta_fatias", "fatias")
    rel = f"{pf}/{nome}.md"
    graves = sum(e["gravidade"] == "grave" for e in abertos)
    incompletos = [e for e in abertos if faltando(e)]
    topo = topo or bool(graves)
    hoje = c.agora()
    md = [f"[{tam}] {nome} — correção de {len(abertos)} erro(s)" + (f" ({graves} grave(s))" if graves else ""), "",
          f"Gerada em {hoje:%d/%m/%Y} a partir do `ERROS.md`" + (f" ({c.nome_pasta(cam)})" if app else "") +
          ", com os erros abertos agrupados por área (tela). Tamanho pela quantidade de erros "
          "(até 3 = P, até 8 = M, mais = G).", ""]
    for a in ordem:
        md.append(f"## {a}")
        for e in grupos[a]:
            det = f"aparelho: {e.get('aparelho', '?')} · versão: {e.get('versao', '?')}"
            md.append(f"- {e['id']}" + (" **(grave)**" if e["gravidade"] == "grave" else "") + f" — {e['texto']} ({det})")
        md.append("")
    if incompletos:
        md += ["## Dados que faltam (perguntar antes de corrigir)"] + \
              [f"- {e['id']}: falta {', '.join(faltando(e))}" for e in incompletos] + [""]
    md += ["## Como fechar",
           "- Reproduzir cada erro na tela, aparelho e versão indicados antes de mexer no código.",
           f"- Ao terminar, \"finalizado\": a fatia vai para 🧪 com o roteiro de teste (um item por erro).",
           f"- Teste passou → ✅, a fatia vai com `git mv` para `{cfg.get('pasta_fatias_executadas', 'fatias_executadas')}/`"
           f" e os erros ficam `corrigido e testado` (`status-projeto erro estado --fatia {nome} --para corrigido`).",
           "- Teste não passou → a fatia volta para 🌐 com o que falhou em `Pendente:`; os erros continuam "
           f"`em {nome}`.", ""]
    item = f"- [{tam}] `{rel}` — correção de {len(abertos)} erro(s): {', '.join(ordem)} (desde {hoje:%d/%m})"
    plano = {"fatia": nome, "arquivo": rel, "repo": c.nome_pasta(cam), "tamanho": tam, "topo": topo,
             "erros": [e["id"] for e in abertos], "areas": {a: [e["id"] for e in grupos[a]] for a in ordem},
             "incompletos": {e["id"]: faltando(e) for e in incompletos}, "item_status": item,
             "conteudo": "\n".join(md)}
    if not gravar:
        return plano
    p = os.path.join(cam, rel)
    if os.path.exists(p):
        raise Recusa(f"{rel} já existe; nada foi gravado.")
    sp = os.path.join(cam, "STATUS.md")
    try:
        with open(sp, encoding="utf-8") as f:
            st = f.read()
    except FileNotFoundError:
        raise Recusa("STATUS.md não existe neste repo.")
    novo_st = inserir_no_pacote(st, item, topo)  # confere o STATUS.md antes de gravar qualquer coisa
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(plano["conteudo"])
    with open(sp, "w", encoding="utf-8", newline="\n") as f:
        f.write(novo_st)
    mudar(cam, {"repos": []}, "erro", plano["erros"], estado=nome)
    return plano
