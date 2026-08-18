"""
O Limite do laço `for` vs. `while`: a fronteira entre FRP e FRG.

Execute com:  python main.py
Os gráficos são gravados em ./graficos
"""

import os

import benchmark
import frg
import frp

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graficos")


def titulo(texto):
    print("\n" + "=" * 72)
    print(texto)
    print("=" * 72)


# ---------------------------------------------------------------------------
# 1. Módulo FRP
# ---------------------------------------------------------------------------

def demonstrar_frp():
    titulo("1. MÓDULO FRP — tudo construído com laços `for` limitados")

    print("\nFunções básicas:")
    print(f"  Z(7)          = {frp.Z(7)}")
    print(f"  S(7)          = {frp.S(7)}")
    print(f"  P_2^3(4,5,6)  = {frp.P(3, 2)(4, 5, 6)}")

    print("\nAritmética (só composição + recursão primitiva):")
    print(f"  soma(3, 4)     = {frp.soma(3, 4)}")
    print(f"  mult(6, 7)     = {frp.mult(6, 7)}")
    print(f"  pot(2, 10)     = {frp.pot(2, 10)}")
    print(f"  fatorial(6)    = {frp.fatorial(6)}")
    print(f"  sub(9, 4)      = {frp.sub(9, 4)}   (subtração truncada)")
    print(f"  sub(4, 9)      = {frp.sub(4, 9)}   (nunca fica negativo)")
    print(f"  maior(9, 4)    = {frp.maior(9, 4)}")

    print("\nRaiz quadrada piso por minimização limitada  mu y <= x [(y+1)^2 > x]:")
    print("      x | floor(sqrt(x)) | testes feitos | teto b+1")
    for x in (0, 1, 15, 16, 17, 99, 100, 1000):
        r, testes, teto = frp.raiz_quadrada_piso_com_custo(x)
        print(f"  {x:5} | {r:14} | {testes:13} | {teto:8}")
    print("\n  Os testes nunca chegam ao teto: o `for` já garantia a parada.")


# ---------------------------------------------------------------------------
# 2. Módulo FRG
# ---------------------------------------------------------------------------

def demonstrar_frg():
    titulo("2. MÓDULO FRG — laços indefinidos (`while`) e Ackermann")

    frg.configurar_pilha(benchmark.LIMITE_RECURSAO)

    print("\nTabela de A(m, n):")
    print("      m\\n |" + "".join(f"{n:>8}" for n in range(6)))
    for m in range(4):
        linha = f"  {m:7} |"
        for n in range(6):
            try:
                linha += f"{frg.ackermann(m, n):>8}"
            except RecursionError:
                linha += f"{'estouro':>8}"
        print(linha)
    print(f"\n  A(4, 0) = {frg.ackermann(4, 0)}")
    print("  A(4, 1) = 65533   (valor conhecido; ver benchmark: estoura a pilha)")
    print("  A(4, 2) = 2^65536 - 3  (número com ~19.729 dígitos)")

    print("\nMinimização NÃO-limitada  mu y [ y*y >= 1000 ]:")
    y = frg.minimizacao_ilimitada(lambda y: y * y >= 1000)
    print(f"  encontrou y = {y}  (aqui o `while` teve sorte e parou)")

    print("\nMinimização NÃO-limitada  mu y [ y*y == 2 ]  (não existe solução):")
    try:
        frg.minimizacao_ilimitada(lambda y: y * y == 2, teto_seguranca=100_000)
    except frg.BuscaInterrompida as e:
        print(f"  {e}")
    print("  Sem o teto de segurança, este `while` rodaria para sempre.")
    print("  É exatamente isso que a minimização LIMITADA torna impossível.")


# ---------------------------------------------------------------------------
# 3. Benchmark e gráficos
# ---------------------------------------------------------------------------

def rodar_benchmark():
    titulo("3. BENCHMARK — tempo, chamadas e pilha da Função de Ackermann")
    os.makedirs(PASTA, exist_ok=True)

    print("\nMedindo o custo de um quadro de pilha...")
    bytes_quadro = benchmark.bytes_por_quadro()
    print(f"  1 quadro de chamada ~ {bytes_quadro:.0f} bytes")

    print("\nMedindo A(m, n) para m = 0..3:")
    dados = benchmark.coletar_crescimento()
    for m in sorted(dados):
        r = dados[m][-1]
        chamadas = f"{r['chamadas']:,}".replace(",", ".")
        valor = r["valor"] if r["valor"] is not None else "estourou a pilha"
        print(f"  m={m}: até n={r['n']}  valor={valor}  "
              f"tempo={r['tempo']:.3f}s  chamadas={chamadas}")

    print("\nMedindo a pilha em casos escolhidos:")
    pilha = benchmark.coletar_pilha()
    print("     caso |  profundidade |   memória (KB) | resultado")
    for r in pilha:
        mem = r["prof_max"] * bytes_quadro / 1024
        if r["estourou"]:
            estado = "STACK OVERFLOW"
        elif r["desistiu"]:
            estado = "nao terminou (teto de chamadas)"
        else:
            estado = f"valor = {r['valor']}"
        prof = f"{r['prof_max']:,}".replace(",", ".")
        kb = f"{mem:,.1f}".replace(",", "@").replace(".", ",").replace("@", ".")
        print(f"  A({r['m']},{r['n']}) | {prof:>13} | {kb:>14} | {estado}")

    print("\nGerando gráficos:")
    p = lambda nome: os.path.join(PASTA, nome)
    benchmark.grafico_frp_crescimento(p("01_frp_crescimento.png"))
    benchmark.grafico_minimizacao_limitada(p("02_frp_minimizacao_limitada.png"))
    benchmark.grafico_tempo(dados, p("03_ackermann_tempo.png"))
    benchmark.grafico_chamadas(dados, p("04_ackermann_chamadas.png"))
    benchmark.grafico_memoria(pilha, bytes_quadro, p("05_ackermann_memoria.png"))
    benchmark.grafico_frp_vs_frg(pilha, dados, p("06_frp_vs_frg.png"))
    return dados, pilha, bytes_quadro


# ---------------------------------------------------------------------------
# 4. Conclusão
# ---------------------------------------------------------------------------

def conclusao(pilha):
    titulo("4. POR QUE A MINIMIZAÇÃO LIMITADA NUNCA ENTRA EM LOOP INFINITO")
    estouros = [f"A({r['m']},{r['n']})" for r in pilha if r["estourou"]]
    print(f"""
  mu y <= b [ P(x, y) ]  vira, literalmente:

      for y in range(b + 1):
          if P(x, y): return y
      return b + 1

  1) O limite b é calculado ANTES do laço começar, por uma função que já é
     FRP (logo, total). Quando o `for` inicia, o número de voltas já está
     escrito na pedra: b + 1.

  2) Nenhum comando dentro do corpo pode alterar esse número. Não há
     condição de continuação para avaliar: a cada volta o contador y só
     cresce, e range(b+1) é finito.

  3) Como o conjunto {{0, 1, ..., b}} é finito e y percorre cada elemento
     uma única vez, o laço termina em no máximo b + 1 passos — mesmo no
     pior caso, quando P nunca é verdadeiro (aí devolvemos b + 1).

  4) Existe até uma cota explícita: custo(mu y <= b) <= (b + 1) * custo(P).
     Como P é total e b é total, a composição é total. FRP é fechada por
     minimização limitada — por isso a raiz quadrada piso continua sendo FRP.

  É a correspondência exata com o laço `for` de contagem fixa:
     `for`   = repetição com contador conhecido de antemão  -> sempre para
     `while` = repetição com condição avaliada a cada volta -> pode não parar

  Já a minimização NÃO-limitada (mu y) e a Função de Ackermann usam o segundo
  regime. Ackermann é total (sempre tem resposta), mas nenhum `for` de
  profundidade fixa a calcula: ela precisa de recursão aninhada, e cada nível
  de aninhamento vira um quadro de pilha.

  Resultado medido neste computador: {', '.join(estouros)} estouraram a pilha.
  Entradas com um único dígito — e a máquina desiste. Veja o gráfico
  graficos/05_ackermann_memoria.png.
""")


if __name__ == "__main__":
    demonstrar_frp()
    demonstrar_frg()
    _, pilha, _ = rodar_benchmark()
    conclusao(pilha)
    print(f"Gráficos gravados em: {PASTA}\n")
