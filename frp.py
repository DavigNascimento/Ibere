"""
Módulo FRP — Funções Recursivas Primitivas.

Regra de ouro deste módulo: TUDO aqui é construído com laços `for` de tamanho
conhecido ANTES de o laço começar. Nenhum `while`, nenhuma busca sem limite.
Consequência: toda função deste arquivo é total (sempre para e devolve valor).
"""

# Contador didático de passos elementares (só para os gráficos).
PASSOS = {"n": 0}


def zerar_contador():
    PASSOS["n"] = 0


def passos():
    return PASSOS["n"]


# ---------------------------------------------------------------------------
# 1. Funções básicas
# ---------------------------------------------------------------------------

def Z(*_args):
    """Função zero: Z(x1..xn) = 0."""
    PASSOS["n"] += 1
    return 0


def S(x):
    """Função sucessor: S(x) = x + 1."""
    PASSOS["n"] += 1
    return x + 1


def P(n, i):
    """Projeção P_i^n(x1,...,xn) = xi  (i começa em 1)."""
    def projecao(*args):
        PASSOS["n"] += 1
        assert len(args) == n, f"P_{i}^{n} esperava {n} argumentos"
        return args[i - 1]
    projecao.__name__ = f"P_{i}^{n}"
    return projecao


# ---------------------------------------------------------------------------
# 2. Operadores
# ---------------------------------------------------------------------------

def composicao(f, *gs):
    """h(x) = f( g1(x), ..., gk(x) )."""
    def h(*args):
        return f(*[g(*args) for g in gs])
    return h


def recursao_primitiva(f, g):
    """
    h(x, 0)   = f(x)
    h(x, y+1) = g(x, y, h(x, y))

    Implementado com `for` porque `y` é conhecido antes de o laço começar:
    são exatamente `y` iterações, nem uma a mais.
    """
    def h(*args):
        x, y = args[:-1], args[-1]
        r = f(*x)
        for i in range(y):          # <<< LAÇO LIMITADO: range(y)
            r = g(*x, i, r)
        return r
    return h


# ---------------------------------------------------------------------------
# 3. Aritmética construída estritamente como FRP
# ---------------------------------------------------------------------------

# soma(x, 0)   = x                -> P_1^1
# soma(x, y+1) = S(soma(x, y))    -> S(P_3^3)
soma = recursao_primitiva(P(1, 1), composicao(S, P(3, 3)))

# mult(x, 0)   = 0
# mult(x, y+1) = soma(mult(x, y), x)
mult = recursao_primitiva(Z, composicao(soma, P(3, 3), P(3, 1)))

# pot(x, 0)   = 1
# pot(x, y+1) = mult(pot(x, y), x)          -> x^y
pot = recursao_primitiva(composicao(S, Z), composicao(mult, P(3, 3), P(3, 1)))

# fat(0)   = 1
# fat(y+1) = mult(S(y), fat(y))             -> aridade 1 (sem parâmetros extras)
fatorial = recursao_primitiva(
    composicao(S, Z),
    composicao(mult, composicao(S, P(2, 1)), P(2, 2)),
)

# --- auxiliares para construir predicados (também FRP) ---------------------

# pred(0) = 0 ; pred(y+1) = y
predecessor = recursao_primitiva(Z, P(2, 1))

# sub(x, 0) = x ; sub(x, y+1) = pred(sub(x, y))     -> subtração truncada x ∸ y
sub = recursao_primitiva(P(1, 1), composicao(predecessor, P(3, 3)))

# sg(0) = 0 ; sg(y+1) = 1      -> "sinal"
sinal = recursao_primitiva(Z, composicao(S, composicao(Z, P(2, 1))))

# maior(a, b) = sg(a ∸ b)  -> 1 se a > b, senão 0
maior = composicao(sinal, sub)


# ---------------------------------------------------------------------------
# 4. Minimização LIMITADA:  mu y <= b [ pred(x, y) ]
# ---------------------------------------------------------------------------

def minimizacao_limitada(predicado, b, *x):
    """
    Devolve o MENOR y <= b tal que predicado(x, y) seja verdadeiro (valor 1).
    Se nenhum y <= b satisfaz, devolve b + 1 (convenção de "não achou").

    O laço é um `for` sobre range(b + 1): no máximo b + 1 testes.
    É impossível esta função não terminar.
    """
    for y in range(b + 1):          # <<< LAÇO LIMITADO: no máximo b+1 voltas
        if predicado(*x, y):
            return y
    return b + 1


def raiz_quadrada_piso(x):
    """
    floor(sqrt(x)) = mu y <= x [ (y+1)^2 > x ]

    O limite b = x é seguro porque (x+1)^2 > x para todo x natural,
    então a resposta sempre aparece dentro do intervalo.
    """
    def quadrado_do_proximo_passa(x, y):
        return maior(mult(S(y), S(y)), x) == 1

    return minimizacao_limitada(quadrado_do_proximo_passa, x, x)


def raiz_quadrada_piso_com_custo(x):
    """Mesma função, devolvendo também quantos testes foram feitos e o teto b+1."""
    testes = {"n": 0}

    def quadrado_do_proximo_passa(x, y):
        testes["n"] += 1
        return maior(mult(S(y), S(y)), x) == 1

    r = minimizacao_limitada(quadrado_do_proximo_passa, x, x)
    return r, testes["n"], x + 1
