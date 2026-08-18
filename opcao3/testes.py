"""
Conferência do interpretador contra os operadores nativos do Python.

Execute com:  python3 testes.py

Duas partes:
  1. Semântica — cada função da biblioteca dá o mesmo resultado que a conta
     equivalente feita em Python.
  2. Verificador — cada programa que deveria ser recusado é mesmo recusado,
     e pelo motivo certo.
"""

import math
import sys
import time

import interpretador
from analisador import ErroDeSintaxe
from interpretador import carregar
from verificador import ErroDeAridade, ErroDeTotalidade

FALHAS = []


def confere(rotulo, obtido, esperado):
    if obtido != esperado:
        FALHAS.append(f"{rotulo}: obtive {obtido}, esperava {esperado}")


def primo(n):
    return int(n > 1 and all(n % d for d in range(2, int(n ** 0.5) + 1)))


# ---------------------------------------------------------------------------
# 1. Semântica
# ---------------------------------------------------------------------------

def testar_semantica(p):
    for x in range(8):
        for y in range(8):
            confere(f"ADD({x},{y})", p["ADD"](x, y), x + y)
            confere(f"MULT({x},{y})", p["MULT"](x, y), x * y)
            confere(f"SUB({x},{y})", p["SUB"](x, y), max(0, x - y))
            confere(f"POT({x},{y})", p["POT"](x, y), x ** y)
            confere(f"LEQ({x},{y})", p["LEQ"](x, y), int(x <= y))
            confere(f"GEQ({x},{y})", p["GEQ"](x, y), int(x >= y))
            confere(f"LT({x},{y})", p["LT"](x, y), int(x < y))
            confere(f"GT({x},{y})", p["GT"](x, y), int(x > y))
            confere(f"EQ({x},{y})", p["EQ"](x, y), int(x == y))
            confere(f"NEQ({x},{y})", p["NEQ"](x, y), int(x != y))
            confere(f"E({x},{y})", p["E"](x, y), x * y)          # E = MULT
            confere(f"OU({x},{y})", p["OU"](x, y), int(bool(x) or bool(y)))
            # os três problemas do enunciado
            confere(f"DIV({x},{y})", p["DIV"](x, y), x // y if y else 0)
            confere(f"RESTO({x},{y})", p["RESTO"](x, y), x % y if y else x)

    # divisão inteira numa faixa maior
    for x in range(0, 41):
        for y in range(1, 13):
            confere(f"DIV({x},{y})", p["DIV"](x, y), x // y)
            confere(f"RESTO({x},{y})", p["RESTO"](x, y), x % y)
            confere(f"x=y*q+r ({x},{y})", p["MULT"](y, p["DIV"](x, y)) + p["RESTO"](x, y), x)

    for n in range(9):
        confere(f"FAT({n})", p["FAT"](n), math.factorial(n))

    for n in range(50):
        confere(f"PRED({n})", p["PRED"](n), max(0, n - 1))
        confere(f"SG({n})", p["SG"](n), int(n != 0))
        confere(f"NSG({n})", p["NSG"](n), int(n == 0))
        confere(f"RAIZ({n})", p["RAIZ"](n), math.isqrt(n))
        confere(f"NUMDIV({n})", p["NUMDIV"](n),
                sum(1 for d in range(1, n + 1) if n % d == 0))
        confere(f"PRIMO({n})", p["PRIMO"](n), primo(n))
        confere(f"CONTAPRIMOS({n})", p["CONTAPRIMOS"](n),
                sum(primo(k) for k in range(n + 1)))
        confere(f"PERFEITO({n})", p["PERFEITO"](n),
                int(n > 0 and sum(d for d in range(1, n) if n % d == 0) == n))

    fib = [0, 1]
    while len(fib) < 13:
        fib.append(fib[-1] + fib[-2])
    for n in range(13):
        confere(f"FIB({n})", p["FIB"](n), fib[n])
        confere(f"BASE({n}) > F(n+1)", p["BASE"](n) > fib[n + 1] if n + 1 < len(fib) else True, True)

    for c in range(3):
        for a in range(4):
            for b in range(4):
                confere(f"SE({c},{a},{b})", p["SE"](c, a, b), a if c else b)


def testar_memoria_nao_muda_resultado(p):
    """Ligar ou desligar as tabelas não pode alterar nenhum valor."""
    interpretador.TABELAS = False
    puro = carregar("biblioteca.prf")
    # FIB fica em 6: sem as tabelas o custo é ~50x maior e o teste demoraria
    for nome, args in [("SUB", (40, 17)), ("DIV", (100, 7)), ("RESTO", (100, 7)),
                       ("PRIMO", (91,)), ("FIB", (6,)), ("RAIZ", (99,))]:
        confere(f"tabelas: {nome}{args}", puro[nome](*args), p[nome](*args))
    interpretador.TABELAS = True


# ---------------------------------------------------------------------------
# 2. Verificador
# ---------------------------------------------------------------------------

RECUSAS = [
    ("X = MIN(P1_2)", ErroDeTotalidade),
    ("X = MIN(COMP(EQ,[P1_2,P2_2]))", ErroDeTotalidade),
    ("X = WHILE(P1_1)", ErroDeSintaxe),
    ("X = LOOP(P1_1)", ErroDeSintaxe),
    ("X = COMP(S, [X])", ErroDeAridade),                 # auto-referência
    ("A = COMP(S,[B])\nB = COMP(S,[A])", ErroDeAridade),  # referência mútua
    ("X = COMP(ADD, [P1_1])", ErroDeAridade),            # aridade de f
    ("X = COMP(ADD, [P1_1, P1_2])", ErroDeAridade),      # aridades diferentes
    ("X = COMP(ADD, [])", ErroDeAridade),                # lista vazia
    ("X = P4_3", ErroDeAridade),                         # índice fora da faixa
    ("X = P0_3", ErroDeAridade),
    ("X = REC(P1_1, COMP(S,[P1_2]))", ErroDeAridade),    # passo com aridade errada
    ("X = REC(P1_2, S)", ErroDeAridade),                 # passo de aridade 1 < 2
    ("X = MINLIM(P1_1, P1_1)", ErroDeAridade),           # predicado precisa de n+1
    ("ADD = Z", ErroDeAridade),                          # redefinição
    ("X = COMP(S, [P1_1]", ErroDeSintaxe),               # parêntese faltando
    ("X = COMP(S, P1_1)", ErroDeSintaxe),                # colchetes faltando
    ("X =", ErroDeSintaxe),
    ("X = P1", ErroDeAridade),                           # vira nome indefinido
]

ACEITOS = [
    "X = REC(P1_1, COMP(S,[P2_3]))",       # o exemplo do enunciado: total, aridades ok
    "X = COMP(MULT, [P1_1, 2])",           # literal elevado à aridade 1
    "X = MINLIM(COMP(GT,[P2_2,P1_2]), P1_1)",
    "X = Z_3",
    "X = 7",
]


def testar_verificador(p):
    for codigo, esperado in RECUSAS:
        rotulo = "recusa: " + codigo.replace("\n", " ; ")
        try:
            p.estender(codigo)
            FALHAS.append(f"{rotulo}: foi ACEITO, deveria falhar com {esperado.__name__}")
        except esperado:
            pass
        except (ErroDeSintaxe, ErroDeAridade, ErroDeTotalidade) as erro:
            FALHAS.append(f"{rotulo}: falhou com {type(erro).__name__}, "
                          f"esperava {esperado.__name__}")

    for codigo in ACEITOS:
        try:
            p.estender(codigo)
        except (ErroDeSintaxe, ErroDeAridade, ErroDeTotalidade) as erro:
            FALHAS.append(f"aceite: {codigo}: foi recusado ({type(erro).__name__}: {erro})")


def testar_erros_de_execucao(p):
    from interpretador import ErroDeExecucao
    for args in [(1,), (1, 2, 3), (-1, 2), (1.5, 2)]:
        try:
            p["ADD"](*args)
            FALHAS.append(f"ADD{args} deveria ter sido recusado em execução")
        except ErroDeExecucao:
            pass


# ---------------------------------------------------------------------------

def main():
    inicio = time.time()
    p = carregar("biblioteca.prf")

    print("conferindo semântica contra o Python...")
    testar_semantica(p)
    print("conferindo que a memória de recursão não altera resultados...")
    testar_memoria_nao_muda_resultado(p)
    print("conferindo o verificador...")
    testar_verificador(p)
    testar_erros_de_execucao(p)

    print()
    if FALHAS:
        print(f"{len(FALHAS)} FALHA(S):")
        for f in FALHAS[:40]:
            print("  -", f)
        sys.exit(1)
    print(f"tudo certo ({time.time() - inicio:.1f}s)")


if __name__ == "__main__":
    main()
