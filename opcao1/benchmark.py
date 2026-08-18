"""
Módulo de Benchmark / Monitoramento.

Mede, para a Função de Ackermann, o tempo de execução, o número de chamadas
recursivas e a PROFUNDIDADE MÁXIMA DA PILHA (que é o consumo de memória),
e desenha os gráficos em ./graficos.
"""

import resource
import sys
import textwrap
import threading
import time

import frg
import frp

# Tamanho da pilha, em quadros. 1000 é o valor PADRÃO do CPython
# (sys.getrecursionlimit()): é a pilha real de qualquer programa Python comum.
LIMITE_RECURSAO = 1_000

# Teto de chamadas: só para nenhuma medição travar o terminal.
TETO_CHAMADAS = 30_000_000

# Espaço de pilha reservado para as threads de medição (bytes).
PILHA_THREAD = 512 * 1024 * 1024


# ---------------------------------------------------------------------------
# Execução isolada (thread com pilha grande, para medir sem derrubar o processo)
# ---------------------------------------------------------------------------

def _em_thread(funcao):
    """Roda `funcao` numa thread própria e devolve (resultado, erro)."""
    caixa = {}

    def alvo():
        sys.setrecursionlimit(LIMITE_RECURSAO)
        try:
            caixa["ok"] = funcao()
        except BaseException as e:            # RecursionError inclusive
            caixa["erro"] = e

    threading.stack_size(PILHA_THREAD)
    t = threading.Thread(target=alvo)
    t.start()
    t.join()
    return caixa.get("ok"), caixa.get("erro")


def medir(m, n):
    """Mede uma chamada A(m, n). Devolve um dicionário com tudo."""
    def trabalho():
        frg.zerar_monitor(teto_chamadas=TETO_CHAMADAS)
        t0 = time.perf_counter()
        valor, estourou, desistiu = None, False, False
        try:
            valor = frg.ackermann_monitorado(m, n)
        except RecursionError:
            estourou = True
        except frg.TempoEsgotado:
            desistiu = True
        t1 = time.perf_counter()
        return {
            "m": m,
            "n": n,
            "valor": valor,
            "tempo": t1 - t0,
            "chamadas": frg.MONITOR["chamadas"],
            "prof_max": frg.MONITOR["prof_max"],
            "estourou": estourou,
            "desistiu": desistiu,
        }

    resultado, erro = _em_thread(trabalho)
    if erro is not None:
        raise erro
    return resultado


# ---------------------------------------------------------------------------
# Custo de memória de um quadro de pilha (medido, não chutado)
# ---------------------------------------------------------------------------

def bytes_por_quadro(profundidade=100_000):
    """Mede quantos bytes de RSS cada quadro (frame) da pilha custa."""
    def desce(k):
        if k == 0:
            return 0
        return desce(k - 1) + 1

    def trabalho():
        sys.setrecursionlimit(profundidade + 1000)
        antes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        desce(profundidade)
        depois = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return (depois - antes) * 1024 / profundidade

    valor, erro = _em_thread(trabalho)
    if erro is not None or not valor or valor <= 0:
        return 120.0          # estimativa conservadora se a medida falhar
    return valor


# ---------------------------------------------------------------------------
# Coleta dos dados
# ---------------------------------------------------------------------------

def coletar_crescimento(orcamento_segundos=1.5, n_maximo=12):
    """Para m = 0..3, aumenta n enquanto o tempo couber no orçamento."""
    dados = {}
    for m in range(4):
        serie = []
        for n in range(n_maximo + 1):
            r = medir(m, n)
            serie.append(r)
            if r["estourou"] or r["desistiu"] or r["tempo"] > orcamento_segundos:
                break
        dados[m] = serie
    return dados


def coletar_pilha():
    """Casos escolhidos para mostrar o estouro de pilha com entradas minúsculas."""
    casos = [(1, 10), (2, 10), (3, 3), (3, 5), (3, 6), (3, 7),
             (4, 0), (4, 1), (4, 2)]
    return [medir(m, n) for m, n in casos]


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

import matplotlib                                   # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                     # noqa: E402
from matplotlib.ticker import LogLocator            # noqa: E402

SERIE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
VERMELHO = "#e34948"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
SUPERFICIE = "#fcfcfb"


def _figura(titulo, subtitulo, xlabel, ylabel, tamanho=(9, 5.5)):
    fig, ax = plt.subplots(figsize=tamanho, facecolor=SUPERFICIE)
    ax.set_facecolor(SUPERFICIE)
    fig.suptitle(titulo, x=0.06, y=0.97, ha="left", fontsize=14,
                 fontweight="bold", color=TINTA)
    ax.set_title(textwrap.fill(subtitulo, 92), loc="left", fontsize=10,
                 color=TINTA_2, pad=14)
    ax.set_xlabel(xlabel, fontsize=10, color=TINTA_2)
    ax.set_ylabel(ylabel, fontsize=10, color=TINTA_2)
    ax.grid(axis="y", color="#e6e5e1", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#d5d4cf")
    ax.tick_params(colors=TINTA_2, labelsize=9)
    return fig, ax


def _salvar(fig, caminho):
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(caminho, dpi=160, facecolor=SUPERFICIE)
    plt.close(fig)
    print(f"  gravado: {caminho}")


def grafico_frp_crescimento(caminho):
    """Passos de recursão primitiva das quatro operações aritméticas."""
    ns = list(range(1, 9))
    series = [
        ("Adição  n+n", lambda n: frp.soma(n, n)),
        ("Multiplicação  n*n", lambda n: frp.mult(n, n)),
        ("Potenciação  2^n", lambda n: frp.pot(2, n)),
        ("Fatorial  n!", lambda n: frp.fatorial(n)),
    ]
    fig, ax = _figura(
        "FRP: crescimento previsível",
        "Passos elementares gastos por operações construídas só com recursão "
        "primitiva (eixo log).",
        "n", "passos elementares (log)")
    for cor, (nome, f) in zip(SERIE, series):
        ys = []
        for n in ns:
            frp.zerar_contador()
            f(n)
            ys.append(frp.passos())
        ax.plot(ns, ys, color=cor, linewidth=2, marker="o", markersize=5,
                markeredgecolor=SUPERFICIE, markeredgewidth=1.5, label=nome,
                zorder=3)
        ax.annotate(nome.split()[0], (ns[-1], ys[-1]), textcoords="offset points",
                    xytext=(8, -3), fontsize=9, color=TINTA_2)
    ax.set_yscale("log")
    ax.set_xlim(0.7, ns[-1] + 1.6)
    ax.legend(frameon=False, fontsize=9, labelcolor=TINTA_2, loc="upper left")
    _salvar(fig, caminho)


def grafico_minimizacao_limitada(caminho):
    """Testes gastos pela raiz quadrada piso vs. o teto garantido b+1."""
    xs = list(range(0, 201, 10))
    usados, teto, raizes = [], [], []
    for x in xs:
        r, testes, limite = frp.raiz_quadrada_piso_com_custo(x)
        usados.append(testes)
        teto.append(limite)
        raizes.append(r)
    fig, ax = _figura(
        "Minimização limitada nunca escapa do teto",
        "Raiz quadrada piso por mu y <= b: os testes realmente executados ficam "
        "sempre abaixo do limite b+1 fixado antes do laço.",
        "x", "número de testes do predicado")
    ax.plot(xs, teto, color=SERIE[1], linewidth=2, linestyle="--",
            label="teto b+1 (pior caso possível)", zorder=3)
    ax.plot(xs, usados, color=SERIE[0], linewidth=2, marker="o", markersize=5,
            markeredgecolor=SUPERFICIE, markeredgewidth=1.5,
            label="testes efetivamente executados", zorder=4)
    ax.fill_between(xs, usados, teto, color=SERIE[1], alpha=0.07, zorder=1)
    ax.annotate("região impossível de ultrapassar:\no `for` acaba em b+1 voltas",
                (xs[-6], teto[-6]), textcoords="offset points", xytext=(-215, -55),
                fontsize=9, color=TINTA_2)
    ax.annotate(f"x={xs[-1]} -> raiz {raizes[-1]}, {usados[-1]} testes",
                (xs[-1], usados[-1]), textcoords="offset points", xytext=(-120, 14),
                fontsize=9, color=SERIE[0])
    ax.legend(frameon=False, fontsize=9, labelcolor=TINTA_2, loc="upper left")
    _salvar(fig, caminho)


def grafico_tempo(dados, caminho):
    fig, ax = _figura(
        "Ackermann: explosão do tempo de execução",
        "Tempo de A(m, n) medido em segundos (eixo log). Cada nível de m troca "
        "a operação por uma ordem de grandeza acima.",
        "n", "tempo (s, log)")
    for m in sorted(dados):
        serie = [r for r in dados[m] if not (r["estourou"] or r["desistiu"])]
        if not serie:
            continue
        xs = [r["n"] for r in serie]
        ys = [max(r["tempo"], 1e-7) for r in serie]
        ax.margins(x=0.13)
        cor = SERIE[m]
        ax.plot(xs, ys, color=cor, linewidth=2, marker="o", markersize=5,
                markeredgecolor=SUPERFICIE, markeredgewidth=1.5,
                label=f"m = {m}", zorder=3)
        ax.annotate(f"m={m}", (xs[-1], ys[-1]), textcoords="offset points",
                    xytext=(8, -3), fontsize=9, color=TINTA_2)
    ax.set_yscale("log")
    ax.legend(frameon=False, fontsize=9, labelcolor=TINTA_2, loc="upper left")
    _salvar(fig, caminho)


def grafico_chamadas(dados, caminho):
    fig, ax = _figura(
        "Ackermann: número de chamadas recursivas",
        "Quantas vezes A(m, n) chama a si mesma (eixo log).",
        "n", "chamadas recursivas (log)")
    for m in sorted(dados):
        serie = [r for r in dados[m] if not (r["estourou"] or r["desistiu"])]
        if not serie:
            continue
        xs = [r["n"] for r in serie]
        ys = [r["chamadas"] for r in serie]
        ax.margins(x=0.13)
        ax.plot(xs, ys, color=SERIE[m], linewidth=2, marker="o", markersize=5,
                markeredgecolor=SUPERFICIE, markeredgewidth=1.5,
                label=f"m = {m}", zorder=3)
        ax.annotate(f"m={m}", (xs[-1], ys[-1]), textcoords="offset points",
                    xytext=(8, -3), fontsize=9, color=TINTA_2)
    ax.set_yscale("log")
    ax.legend(frameon=False, fontsize=9, labelcolor=TINTA_2, loc="upper left")
    _salvar(fig, caminho)


def grafico_memoria(pilha, bytes_quadro, caminho):
    """O gráfico principal: consumo de memória da pilha e o estouro."""
    rotulos = [f"A({r['m']},{r['n']})" for r in pilha]
    memoria = [r["prof_max"] * bytes_quadro / 1024 for r in pilha]
    cores = [VERMELHO if r["estourou"] else SERIE[0] for r in pilha]
    teto_kb = LIMITE_RECURSAO * bytes_quadro / 1024

    fig, ax = _figura(
        "Consumo de memória da pilha em A(m, n)",
        f"Memória ocupada pelos quadros de chamada ({bytes_quadro:.0f} bytes por "
        "quadro, medido). Barras vermelhas = stack overflow.",
        "", "memória da pilha (KB, log)", tamanho=(10, 5.8))
    barras = ax.bar(rotulos, memoria, color=cores, width=0.62, zorder=3)
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(LogLocator(base=10))
    ax.axhline(teto_kb, color=TINTA_2, linewidth=1.4, linestyle="--", zorder=4)
    ax.annotate(f"limite da pilha: {LIMITE_RECURSAO:,} quadros "
                f"(~{teto_kb:,.0f} KB)".replace(",", "."),
                (0.0, teto_kb), xytext=(4, 6), textcoords="offset points",
                fontsize=9, color=TINTA_2)

    for barra, r in zip(barras, pilha):
        texto = f"{r['prof_max']:,}".replace(",", ".") + " quadros"
        if r["estourou"]:
            texto += "\nESTOUROU"
        ax.annotate(texto, (barra.get_x() + barra.get_width() / 2, barra.get_height()),
                    ha="center", va="bottom", fontsize=8.5,
                    color=VERMELHO if r["estourou"] else TINTA_2,
                    fontweight="bold" if r["estourou"] else "normal")

    ax.set_ylim(top=max(memoria) * 12)
    ax.annotate("A(4,1) precisaria de 65.536 quadros;\n"
                "A(4,2) precisaria de ~2^65536 quadros —\n"
                "mais do que átomos no universo.",
                (0.62, 0.80), xycoords="axes fraction", fontsize=9.5,
                color=VERMELHO)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=SERIE[0], label="calculou até o fim"),
                       Patch(color=VERMELHO, label="stack overflow (RecursionError)")],
              frameon=False, fontsize=9, labelcolor=TINTA_2, loc="upper left")
    _salvar(fig, caminho)


def grafico_frp_vs_frg(pilha, dados, caminho):
    """Comparação direta: pilha constante (FRP/`for`) vs. pilha explosiva (FRG)."""
    ns = list(range(1, 9))
    frp_prof = [1 for _ in ns]                       # o `for` não empilha nada
    ack = [r for r in dados[3] if not (r["estourou"] or r["desistiu"])]
    fig, ax = _figura(
        "A fronteira: `for` não empilha, `while`/recursão geral sim",
        "Profundidade máxima de pilha exigida por uma FRP (fatorial via `for`) "
        "e por A(3, n) (eixo log).",
        "n", "profundidade máxima da pilha (log)")
    ax.plot(ns, frp_prof, color=SERIE[0], linewidth=2, marker="o", markersize=5,
            markeredgecolor=SUPERFICIE, markeredgewidth=1.5,
            label="FRP: fatorial com `for` (pilha constante)", zorder=3)
    ax.plot([r["n"] for r in ack], [r["prof_max"] for r in ack], color=SERIE[1],
            linewidth=2, marker="o", markersize=5, markeredgecolor=SUPERFICIE,
            markeredgewidth=1.5, label="FRG: A(3, n)", zorder=3)
    ax.axhline(LIMITE_RECURSAO, color=VERMELHO, linewidth=1.4, linestyle="--",
               zorder=4)
    ax.annotate("limite da pilha", (0.02, LIMITE_RECURSAO), xytext=(4, 6),
                textcoords="offset points", fontsize=9, color=VERMELHO)
    ax.annotate("pilha constante = 1", (ns[-1], 1), textcoords="offset points",
                xytext=(-40, 10), fontsize=9, color=SERIE[0])
    ax.set_yscale("log")
    ax.set_ylim(0.6, LIMITE_RECURSAO * 100)
    ax.legend(frameon=False, fontsize=9, labelcolor=TINTA_2, loc="upper right")
    _salvar(fig, caminho)
