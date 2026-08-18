"""
Módulo FRG — Funções Recursivas Gerais.

Aqui aparece o que o módulo FRP não consegue expressar: laços cujo número de
voltas NÃO é conhecido antes de começar (`while`). Preço: as funções podem
não terminar, estourar a pilha, ou rodar para sempre.
"""

import sys


# ---------------------------------------------------------------------------
# 1. Função de Ackermann
# ---------------------------------------------------------------------------

def ackermann(m, n):
    """
    A(0, n) = n + 1
    A(m, 0) = A(m-1, 1)
    A(m, n) = A(m-1, A(m, n-1))

    Total (sempre termina em teoria), mas NÃO é primitiva recursiva:
    cresce mais rápido que qualquer FRP.
    """
    if m == 0:
        return n + 1
    if n == 0:
        return ackermann(m - 1, 1)
    return ackermann(m - 1, ackermann(m, n - 1))


# Versão instrumentada: conta chamadas e mede a profundidade da pilha.
MONITOR = {"chamadas": 0, "prof": 0, "prof_max": 0, "teto_chamadas": None}


class TempoEsgotado(Exception):
    """Teto de chamadas atingido — usado só para a medição não travar."""


def zerar_monitor(teto_chamadas=None):
    MONITOR.update(chamadas=0, prof=0, prof_max=0, teto_chamadas=teto_chamadas)


def ackermann_monitorado(m, n):
    MONITOR["chamadas"] += 1
    if MONITOR["teto_chamadas"] and MONITOR["chamadas"] > MONITOR["teto_chamadas"]:
        raise TempoEsgotado(f"passou de {MONITOR['teto_chamadas']:,} chamadas")
    MONITOR["prof"] += 1
    if MONITOR["prof"] > MONITOR["prof_max"]:
        MONITOR["prof_max"] = MONITOR["prof"]
    try:
        if m == 0:
            return n + 1
        if n == 0:
            return ackermann_monitorado(m - 1, 1)
        return ackermann_monitorado(m - 1, ackermann_monitorado(m, n - 1))
    finally:
        MONITOR["prof"] -= 1


# ---------------------------------------------------------------------------
# 2. Minimização NÃO-LIMITADA:  mu y [ pred(x, y) ]
# ---------------------------------------------------------------------------

class BuscaInterrompida(Exception):
    """Levantada só para o programa não travar na demonstração."""


def minimizacao_ilimitada(predicado, *x, teto_seguranca=None):
    """
    Devolve o menor y >= 0 com predicado(x, y) verdadeiro.

    Não existe limite: o `while` roda até achar. Se nunca achar, o programa
    fica preso para sempre — é exatamente isso que separa FRG de FRP.
    (`teto_seguranca` existe apenas para a demonstração não travar o terminal.)
    """
    y = 0
    while True:                     # <<< LAÇO INDEFINIDO
        if predicado(*x, y):
            return y
        y += 1
        if teto_seguranca is not None and y > teto_seguranca:
            raise BuscaInterrompida(
                f"nenhum y encontrado ate {teto_seguranca}; "
                "sem o teto de seguranca isto rodaria para sempre"
            )


def raiz_quadrada_piso_frg(x):
    """Mesma raiz do módulo FRP, mas com busca sem limite (usa `while`)."""
    return minimizacao_ilimitada(lambda x, y: (y + 1) * (y + 1) > x, x)


def configurar_pilha(limite):
    """Ajusta o limite de recursão do interpretador."""
    sys.setrecursionlimit(limite)
    return limite
