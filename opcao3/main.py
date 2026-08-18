"""
Mini-interpretador da linguagem PRF (Funções Recursivas Primitivas).

Execute com:  python3 main.py
              python3 main.py --repl     (modo interativo)

Não depende de nenhuma biblioteca externa.
"""

import os
import sys
import time

import interpretador
from analisador import ErroDeSintaxe, analisar
from interpretador import Programa, carregar, carregar_texto
from verificador import ErroDeAridade, ErroDeTotalidade

AQUI = os.path.dirname(os.path.abspath(__file__))
BIBLIOTECA = os.path.join(AQUI, "biblioteca.prf")


def mil(n):
    """12345 -> '12.345' (separador de milhar brasileiro)."""
    return f"{n:,}".replace(",", ".")


def titulo(texto):
    print("\n" + "=" * 76)
    print(texto)
    print("=" * 76)


def subtitulo(texto):
    print("\n" + texto)
    print("-" * len(texto))


# ---------------------------------------------------------------------------
# 1. A linguagem e o verificador
# ---------------------------------------------------------------------------

GRAMATICA = """
    programa  := { definicao }
    definicao := NOME '=' expr
    expr      := 'COMP'   '(' expr ',' '[' expr { ',' expr } ']' ')'
               | 'REC'    '(' expr ',' expr ')'
               | 'MINLIM' '(' expr ',' expr ')'
               | 'MIN'    '(' expr ')'        <- lido só para ser RECUSADO
               | NUMERO                        (literal = constante)
               | NOME                          (S | Z | Z_n | Pi_n | definição anterior)
"""


def apresentar_linguagem(programa):
    titulo("1. A LINGUAGEM PRF E O SEU VERIFICADOR")

    print("\nA gramática inteira cabe em sete linhas:")
    print(GRAMATICA)
    print("  Não há atribuição, não há sequência de comandos, não há `while`,")
    print("  não há `if` como desvio de fluxo e não há chamada a um nome que")
    print("  ainda não foi definido. Tudo o que falta aí é proposital.")

    subtitulo("Definições carregadas de biblioteca.prf, já verificadas")
    print(f"  {'função':<12} {'tipo':<12} {'prof':>4}  {'construtores usados':<28} busca")
    for f in programa:
        c = f.certificado
        tipo = f"N^{f.aridade} -> N"
        busca = "MINLIM" if c.usa_busca_limitada else "-"
        print(f"  {f.nome:<12} {tipo:<12} {c.profundidade:>4}  "
              f"{c.resumo_operadores():<28} {busca}")
    print(f"\n  {len(programa)} definições verificadas: aridades fecham, nenhum MIN,")
    print("  nenhuma referência a nome não definido. Todas totais por construção.")


# ---------------------------------------------------------------------------
# 2. Problema 1 — teste de primalidade
# ---------------------------------------------------------------------------

def problema_primalidade(p):
    titulo("2. PROBLEMA 1 — TESTE DE PRIMALIDADE")

    print("""
  Definição na linguagem (nenhuma linha de Python envolvida):

      DIVISOR  = COMP(MULT, [COMP(SG,[P1_2]),
                             COMP(NSG, [COMP(RESTO,[P2_2, P1_2])])])
      CONTADIV = REC(Z, COMP(ADD, [P3_3, COMP(DIVISOR,[COMP(S,[P2_3]), P1_3])]))
      NUMDIV   = COMP(CONTADIV, [P1_1, P1_1])
      PRIMO    = COMP(EQ, [NUMDIV, 2])

  CONTADIV(n,k) conta os divisores de n em 1..k por recursão em k, e
  NUMDIV(n) = CONTADIV(n,n). Primo é ter exatamente 2 divisores — a
  definição já trata 0 e 1 sem nenhum caso especial.
""")

    print("      n | divisores | PRIMO(n)          n | divisores | PRIMO(n)")
    print("  " + "-" * 66)
    esquerda = list(range(0, 16))
    direita = list(range(16, 32))
    for a, b in zip(esquerda, direita):
        la = f"  {a:5} | {p['NUMDIV'](a):9} | {p['PRIMO'](a):8}"
        lb = f"  {b:5} | {p['NUMDIV'](b):9} | {p['PRIMO'](b):8}"
        print(la + lb)

    primos = [n for n in range(2, 60) if p["PRIMO"](n)]
    print(f"\n  Primos até 59 segundo a linguagem: {primos}")
    print(f"  CONTAPRIMOS(59) = {p['CONTAPRIMOS'](59)}  (a função pi de contagem)")

    r, passos = p["PRIMO"].com_passos(97)
    print(f"\n  PRIMO(97) = {r}  em {mil(passos)} aplicações de Z, S e P.")


# ---------------------------------------------------------------------------
# 3. Problema 2 — Fibonacci
# ---------------------------------------------------------------------------

def problema_fibonacci(p, ate=12):
    titulo("3. PROBLEMA 2 — FIBONACCI")

    print("""
  F(n+2) = F(n+1) + F(n) precisa de DOIS valores anteriores, mas REC só
  entrega UM (o h(x,y) do passo). Não dá para "guardar uma variável a
  mais": não existem variáveis. A saída é a clássica — carregar o par
  (F(k), F(k+1)) codificado num único número, na base B:

      z_k = F(k)*B + F(k+1)          com B > F(n+1)
      z_(k+1) = b*B + (a+b)          a = DIV(z,B), b = RESTO(z,B)
      FIB(n) = DIV(z_n, B)

  É por isso que Fibonacci depende do problema 3: sem divisão inteira não
  se desempacota o par. E o teto B tem que ser calculável de antemão —
  aqui B(n) = 2^teto(0,7n) + 1, que supera F(n+1) ~ 1,618^n.
""")

    print("      n | FIB(n) |  base B | passos básicos |  tempo")
    print("  " + "-" * 56)
    total = 0.0
    valores = []
    for n in range(ate + 1):
        t = time.time()
        r, passos = p["FIB"].com_passos(n)
        dt = time.time() - t
        total += dt
        valores.append(r)
        print(f"  {n:5} | {r:6} | {p['BASE'](n):7} | {mil(passos):>14} | {dt:6.2f}s")
    print(f"\n  Sequência obtida: {valores}")
    print(f"  Tempo total: {total:.1f}s")
    print("""
  O tempo multiplicando-se por ~4 a cada n não é defeito do interpretador:
  é o preço de ter só o sucessor como operação primitiva. MULT(a,b) custa
  a*b passos porque soma b vezes, e DIV custa uma busca. Totalidade sai de
  graça; eficiência, não.""")


# ---------------------------------------------------------------------------
# 4. Problema 3 — divisão inteira
# ---------------------------------------------------------------------------

def problema_divisao(p):
    titulo("4. PROBLEMA 3 — DIVISÃO INTEIRA")

    print("""
  QUOC = MINLIM(COMP(LT, [P1_3, COMP(MULT,[COMP(S,[P3_3]), P2_3])]), P1_2)

  Em notação matemática:  QUOC(x,y) = mu z <= x [ x < (z+1)*y ]

  O teto é P1_2, isto é, o próprio x: o quociente de x por um y >= 1 nunca
  passa de x, então a resposta certamente aparece dentro da faixa. O laço
  do avaliador é `for z in range(b+1)` — no máximo x+1 testes, decididos
  antes da primeira volta.

  Divisão por zero: em vez de "indefinido" (que quebraria a totalidade),
  a linguagem devolve DIV(x,0) = 0 e RESTO(x,0) = x. Uma função total não
  tem o direito de não responder.
""")

    print("      x |  y | DIV | RESTO | conferência x = y*q + r")
    print("  " + "-" * 56)
    casos = [(0, 0), (7, 0), (0, 3), (7, 2), (6, 2), (100, 7), (144, 12), (97, 10)]
    for x, y in casos:
        q, r = p["DIV"](x, y), p["RESTO"](x, y)
        conf = f"{y}*{q} + {r} = {y * q + r}" if y else "(y = 0: convenção)"
        print(f"  {x:5} | {y:2} | {q:3} | {r:5} | {conf}")

    print("\n  Comparação com o operador nativo do Python (0..30 por 1..12):")
    erros = [(x, y) for x in range(31) for y in range(1, 13)
             if (p["DIV"](x, y), p["RESTO"](x, y)) != (x // y, x % y)]
    print(f"    {31 * 12} pares testados, divergências: {len(erros)}")

    q, passos = p["DIV"].com_passos(100, 7)
    print(f"\n  DIV(100,7) = {q} em {mil(passos)} aplicações básicas.")


# ---------------------------------------------------------------------------
# 5. Extras
# ---------------------------------------------------------------------------

def extras(p):
    titulo("5. OUTROS PROGRAMAS NA MESMA LINGUAGEM")

    subtitulo("RAIZ(x) = mu y <= x [ (y+1)^2 > x ]   — raiz quadrada inteira")
    linha = "  " + "  ".join(f"{x}->{p['RAIZ'](x)}" for x in (0, 1, 2, 3, 4, 15, 16, 17, 80, 81, 99, 100))
    print(linha)

    subtitulo("PERFEITO(n) — n é a soma dos próprios divisores")
    perfeitos = [n for n in range(1, 40) if p["PERFEITO"](n)]
    print(f"  perfeitos até 39: {perfeitos}")

    subtitulo("SE(c,a,b) — condicional SEM desvio de fluxo")
    print("  SE = c*a + (1-c)*b, com c reduzido a 0/1 por SG.")
    print("  Os dois ramos são sempre avaliados; por isso um ramo 'ruim' não")
    print("  pode travar o programa — em PRF nenhum ramo trava.")
    print("  " + "  ".join(f"SE({c},7,9)={p['SE'](c, 7, 9)}" for c in (0, 1, 5)))

    subtitulo("FAT e POT")
    print("  " + "  ".join(f"FAT({n})={p['FAT'](n)}" for n in range(8)))
    print("  " + "  ".join(f"POT(2,{n})={p['POT'](2, n)}" for n in range(11)))


# ---------------------------------------------------------------------------
# 6. O verificador recusando programas
# ---------------------------------------------------------------------------

RECUSADOS = [
    ("Minimização ilimitada (o operador mu sem teto)",
     "BUSCA = MIN(COMP(EQ, [COMP(MULT,[P2_2,P2_2]), P1_2]))"),

    ("Laço `while` — nem chega ao verificador",
     "GIRA = WHILE(COMP(NEQ, [P1_1, 1]))"),

    ("Auto-referência (recursão geral disfarçada de chamada de nome)",
     "LOOPY = COMP(S, [LOOPY])"),

    ("Referência mútua entre duas definições",
     "PAR = COMP(NSG, [IMPAR])\nIMPAR = COMP(NSG, [PAR])"),

    ("COMP com número errado de argumentos",
     "ERRADO = COMP(ADD, [P1_1])"),

    ("COMP com argumentos de aridades diferentes",
     "ERRADO = COMP(ADD, [P1_1, P1_2])"),

    ("Projeção com índice fora da faixa",
     "ERRADO = P4_3"),

    ("REC com passo de aridade errada (precisa de n+2)",
     "ERRADO = REC(P1_1, COMP(S, [P1_2]))"),

    ("Redefinição de um nome já existente",
     "ADD = Z"),
]


def verificador_em_acao(programa):
    titulo("6. O VERIFICADOR EM AÇÃO — PROGRAMAS RECUSADOS ANTES DE RODAR")

    print("\n  Cada trecho abaixo é submetido junto com a biblioteca. Nenhum deles")
    print("  chega a ser avaliado: a recusa é estática.\n")

    for descricao, codigo in RECUSADOS:
        print(f"  ## {descricao}")
        for linha in codigo.splitlines():
            print(f"     | {linha}")
        try:
            programa.estender(codigo)
            print("     !! ACEITO — isto seria um furo no verificador\n")
        except ErroDeTotalidade as erro:
            print(f"     -> ErroDeTotalidade: {erro}\n")
        except ErroDeAridade as erro:
            print(f"     -> ErroDeAridade: {erro}\n")
        except ErroDeSintaxe as erro:
            print(f"     -> ErroDeSintaxe: {erro}\n")

    subtitulo("Um caso que a linguagem ACEITA, e deveria mesmo")
    print("  O enunciado sugere  ADD = REC(P1_1, COMP(S,[P2_3])).")
    print("  Ele passa no verificador (aridades fecham, é total), mas o P2_3")
    print("  projeta o contador y em vez do resultado parcial r, então define")
    print("  outra função. O verificador garante TOTALIDADE, não intenção:")
    teste = carregar_texto("SOMA = REC(P1_1, COMP(S, [P2_3]))")
    print("    SOMA(x,y) com P2_3: " +
          "  ".join(f"({x},{y})->{teste['SOMA'](x, y)}" for x, y in
                    [(3, 0), (3, 1), (3, 4), (10, 4)]))
    correto = carregar_texto("SOMA = REC(P1_1, COMP(S, [P3_3]))")
    print("    SOMA(x,y) com P3_3: " +
          "  ".join(f"({x},{y})->{correto['SOMA'](x, y)}" for x, y in
                    [(3, 0), (3, 1), (3, 4), (10, 4)]))


# ---------------------------------------------------------------------------
# 7. Por que não é Turing-completa
# ---------------------------------------------------------------------------

def porque_nao_e_turing_completa(p):
    titulo("7. POR QUE A SINTAXE IMPEDE TURING-COMPLETUDE E LAÇOS INFINITOS")

    print("""
  (a) O ARGUMENTO ESTRUTURAL — indução sobre a árvore

      Toda expressão é folha (Z, S, Pi_n, literal) ou um dos três
      operadores. Provamos "é total" por indução:

        base    Z, S, Pi_n e literais são totais e param em 1 passo.
        COMP    f e gj totais => f(g1(x),...,gk(x)) total: soma finita
                de trabalho finito.
        REC     h(x,y) faz exatamente y chamadas de g; y JÁ É um número
                quando o laço começa, e o laço não pode alterá-lo.
        MINLIM  faz no máximo b(x)+1 testes; b é total pela hipótese de
                indução, logo b(x) é um número antes do laço começar.

      Não há caso indutivo faltando porque não há mais construtores. Todo
      programa da linguagem para. Por isso o avaliador (interpretador.py)
      não contém um único `while`: só dois `for` sobre `range` calculado
      antes da primeira volta.

  (b) O QUE FOI RETIRADO — e por que essas eram as peças perigosas

      1. mu ILIMITADO. Kleene: FRP + minimização ilimitada = funções
         recursivas gerais = Turing-completo. É exatamente o que MIN faria,
         e é por isso que MIN existe na gramática só para ser recusado.
      2. AUTO-REFERÊNCIA. Um nome só enxerga definições ANTERIORES. Sem
         ponto fixo não há recursão geral: quando o corpo de F é analisado,
         F ainda não está no ambiente.
      3. `while` / `loop`. Nem entram no analisador sintático.
      4. Condicional como FUNÇÃO, não como desvio. SE(c,a,b) avalia os dois
         ramos e escolhe com aritmética. Não existe "ramo que não termina".

  (c) O ARGUMENTO DE DIAGONALIZAÇÃO — por que a perda é inevitável

      Toda linguagem TOTAL cujos programas são enumeráveis deixa funções
      computáveis de fora. Enumere os programas f0, f1, f2, ... (dá para
      fazer: são cadeias finitas de um alfabeto finito). Então

          d(n) = f_n(n) + 1

      é computável (basta simular) e total, mas difere de todo f_n. Logo d
      não está na linguagem. Não é falha de projeto: é o preço de decidir
      a parada de graça. Um interpretador universal para PRF, se existisse
      dentro da própria PRF, produziria d — então ele também não existe.

  (d) O EXEMPLO CONCRETO — Ackermann

      A(0,n) = n+1;  A(m+1,0) = A(m,1);  A(m+1,n+1) = A(m, A(m+1,n))

      Total, computável, e cresce mais rápido que qualquer FRP: para todo
      programa PRF f de aridade 1 existe m com A(m,n) > f(n) para n grande.
      Tentar escrevê-la aqui esbarra na estrutura: a recursão de Ackermann
      é sobre DOIS argumentos ao mesmo tempo (recursão aninhada), e REC só
      recorre no ÚLTIMO, com os demais fixos como parâmetros. Não existe
      onde encaixar A(m+1,n) dentro de um REC.
""")

    print("  Medida do preço em passos básicos (Z, S, P aplicados):")
    for nome, args in [("ADD", (30, 40)), ("MULT", (12, 12)), ("POT", (2, 10)),
                       ("FAT", (7,)), ("DIV", (100, 7)), ("PRIMO", (91,))]:
        r, passos = p[nome].com_passos(*args)
        arg = ", ".join(str(a) for a in args)
        print(f"    {nome}({arg}) = {r:<10} {mil(passos):>13} passos")

    print("""
  Cada número aí é finito, e o verificador sabia disso antes de rodar.
  Essa é a troca: a linguagem não computa tudo o que é computável, mas
  sobre ela o problema da parada é decidível — a resposta é sempre "sim".""")


# ---------------------------------------------------------------------------
# 8. Custo do cálculo puro (sem a memória de recursão)
# ---------------------------------------------------------------------------

def custo_sem_memoria(p):
    titulo("8. O EFEITO DA MEMÓRIA DE RECURSÃO")

    print("""
  O avaliador guarda a coluna h(x,0..y) que o laço do REC já produz e a
  reaproveita. Isso é sempre correto AQUI porque toda função da linguagem
  é pura e total — mesmo argumento, mesmo valor, sempre. Numa linguagem
  com funções parciais essa troca não seria segura.

  Sem a memória, PRED(y) custa y voltas e SUB(x,y) — que chama PRED y
  vezes — vira quadrático:
""")
    print(f"    {'chamada':<18} {'com memória':>15} {'sem memória':>15}")
    for nome, args in [("SUB", (300, 300)), ("RESTO", (200, 7)), ("FIB", (7,))]:
        interpretador.TABELAS = True
        p2 = carregar(BIBLIOTECA)
        _, com = p2[nome].com_passos(*args)
        interpretador.TABELAS = False
        p3 = carregar(BIBLIOTECA)
        _, sem = p3[nome].com_passos(*args)
        interpretador.TABELAS = True
        arg = ", ".join(str(a) for a in args)
        print(f"    {nome + '(' + arg + ')':<18} {mil(com):>15} {mil(sem):>15}")
    print("\n  A totalidade não muda nos dois casos — só o preço.")


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

AJUDA = """
  Comandos:
    NOME arg1 arg2 ...     aplica uma função        ex:  PRIMO 97
    NOME = expr            define uma função nova   ex:  DOBRO = COMP(MULT,[P1_1,2])
    :defs                  lista as definições
    :ver NOME              mostra a expressão e o certificado de NOME
    :sair                  encerra
"""


def repl(p):
    print("Mini-interpretador PRF. `:sair` para sair, `:ajuda` para os comandos.")
    while True:
        try:
            linha = input("prf> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not linha or linha.startswith("#"):
            continue
        if linha in (":sair", ":q"):
            return
        if linha == ":ajuda":
            print(AJUDA)
            continue
        if linha == ":defs":
            for f in p:
                print(f"  {f.nome:<14} N^{f.aridade} -> N")
            continue
        if linha.startswith(":ver "):
            nome = linha[5:].strip()
            if nome in p:
                f = p[nome]
                print(f"  {f.nome} = {f.expr}")
                print(f"  tipo N^{f.aridade} -> N, profundidade "
                      f"{f.certificado.profundidade}, usa "
                      f"{f.certificado.resumo_operadores()}")
            else:
                print(f"  {nome!r} não está definido")
            continue
        try:
            if "=" in linha:
                p = p.estender(linha)
                nome = linha.split("=")[0].strip()
                print(f"  ok: {nome} : N^{p[nome].aridade} -> N")
            else:
                partes = linha.split()
                f = p[partes[0]]
                args = [int(a) for a in partes[1:]]
                t = time.time()
                r, passos = f.com_passos(*args)
                print(f"  {r}   ({mil(passos)} passos, {time.time() - t:.3f}s)")
        except (ErroDeSintaxe, ErroDeAridade, ErroDeTotalidade) as erro:
            print(f"  {type(erro).__name__}: {erro}")
        except Exception as erro:                       # noqa: BLE001
            print(f"  erro: {erro}")


# ---------------------------------------------------------------------------

def main():
    fonte = open(BIBLIOTECA, encoding="utf-8").read()
    programa = Programa(analisar(fonte))

    if "--repl" in sys.argv:
        repl(programa)
        return

    inicio = time.time()
    print("=" * 76)
    print("MINI-INTERPRETADOR DA LINGUAGEM PRF")
    print("Funções Recursivas Primitivas: total por construção")
    print("=" * 76)

    apresentar_linguagem(programa)
    problema_primalidade(programa)
    problema_fibonacci(programa)
    problema_divisao(programa)
    extras(programa)
    verificador_em_acao(programa)
    porque_nao_e_turing_completa(programa)
    custo_sem_memoria(programa)

    titulo(f"FIM — tudo isso levou {time.time() - inicio:.1f}s e parou sozinho.")


if __name__ == "__main__":
    main()
