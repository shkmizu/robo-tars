"""
presenca.py — o modelo de IA embarcada do TARS (GS CitizenTech): classifica o que o sensor
ultrassônico HC-SR04 vê na frente do robô, olhando 1 s de leituras (10 amostras a 10 Hz):

  vazio     ninguém perto (ou só coisas longe, a mais de ~1,5 m)
  chegando  alguém se aproximando
  presente  alguém parado na frente do totem
  saindo    alguém se afastando

É uma regressão logística multiclasse (softmax) com 4 características da janela. Pequena o
bastante para rodar no Arduino Uno: 20 números em ponto flutuante, gravados em
arduino/tars_ia/modelo_presenca.h. Este arquivo treina o modelo, mede a precisão e gera o header.
As mesmas contas estão em C em arduino/tars_ia/presenca.h (um teste confere que dão o mesmo resultado).

Uso:
  python presenca.py treinar                         treina (dados sintéticos + gravações em gravacoes/)
  python presenca.py gravar --rotulo presente        grava leituras reais do robô para treinar de novo
  python presenca.py ao-vivo                         mostra a distância e a classe em tempo real
"""
import argparse, csv, glob, math, os, random, sys, time

CLASSES = ('vazio', 'chegando', 'presente', 'saindo')
N_JANELA = 10          # amostras por janela
PERIODO_S = 0.1        # 10 leituras por segundo
ALCANCE_CM = 400       # sem eco (nada no alcance) conta como 4 m
PERTO_CM = 150         # "perto do totem"
CARACTERISTICAS = ('media_m', 'inclinacao_m_s', 'desvio_m', 'fracao_perto')

AQUI = os.path.dirname(os.path.abspath(__file__))
HEADER = os.path.join(AQUI, '..', 'arduino', 'tars_ia', 'modelo_presenca.h')
METRICAS = os.path.join(AQUI, 'presenca_metricas.md')
PASTA_GRAVACOES = os.path.join(AQUI, 'gravacoes')


# ─── Características (mesmas contas de presenca.h) ──────────────────────────────────

def _mediana3(a, b, c):
    return max(min(a, b), min(max(a, b), c))


def caracteristicas(d_cm):
    """10 leituras em cm (0 = sem eco) → [média (m), inclinação (m/s), desvio da reta (m), fração perto]."""
    m = [(x if x > 0 else ALCANCE_CM) / 100 for x in d_cm]
    n = len(m)
    f = [m[0]] + [_mediana3(m[i - 1], m[i], m[i + 1]) for i in range(1, n - 1)] + [m[-1]]   # tira picos
    media = sum(f) / n
    xm = (n - 1) * PERIODO_S / 2
    sxx = sum((i * PERIODO_S - xm) ** 2 for i in range(n))
    inclinacao = sum((i * PERIODO_S - xm) * (y - media) for i, y in enumerate(f)) / sxx
    # desvio em volta da reta: o "tremido" (balanço da pessoa, ruído), sem o movimento de aproximação
    desvio = math.sqrt(sum((y - media - inclinacao * (i * PERIODO_S - xm)) ** 2 for i, y in enumerate(f)) / n)
    perto = sum(1 for x in d_cm if 0 < x < PERTO_CM) / n
    return [media, inclinacao, desvio, perto]


def prever(modelo, d_cm):
    """→ (classe, probabilidades)"""
    x = [(v - mu) / sd for v, mu, sd in zip(caracteristicas(d_cm), modelo['media'], modelo['escala'])]
    z = [b + sum(w * xi for w, xi in zip(ws, x)) for ws, b in zip(modelo['pesos'], modelo['vies'])]
    zmax = max(z)
    e = [math.exp(v - zmax) for v in z]
    s = sum(e)
    p = [v / s for v in e]
    return CLASSES[p.index(max(p))], p


# ─── Dados sintéticos: física simples do HC-SR04 e de uma pessoa ─────────────────────

def _leituras(rnd, dist_cm):
    """Distâncias verdadeiras → leituras como o HC-SR04 dá: ruído, falhas de eco e picos."""
    ruido, falha, pico = rnd.uniform(0.3, 1.2), rnd.uniform(0, 0.05), rnd.uniform(0, 0.02)
    out = []
    for d in dist_cm:
        r = rnd.random()
        if d >= ALCANCE_CM or r < falha:
            out.append(0)                                   # sem eco
        elif r < falha + pico:
            out.append(rnd.randint(20, ALCANCE_CM - 1))     # eco espúrio
        else:
            out.append(max(2, min(ALCANCE_CM - 1, round(d + rnd.gauss(0, ruido)))))
    return out


def _balanco(rnd):
    """Uma pessoa nunca fica imóvel: balança alguns cm."""
    amp, freq, fase = rnd.uniform(0.5, 4), rnd.uniform(0.15, 1.0), rnd.uniform(0, math.tau)
    return lambda t: amp * math.sin(math.tau * freq * t + fase)


def amostra_sintetica(rnd, classe):
    t = [i * PERIODO_S for i in range(N_JANELA)]
    if classe == 'vazio':
        caso = rnd.random()
        if caso < 0.35:
            dist = [ALCANCE_CM] * N_JANELA                                  # nada na frente
        elif caso < 0.7:
            d0 = rnd.uniform(165, 390)                                      # parede/objeto longe
            dist = [d0] * N_JANELA
        else:
            d0, bal = rnd.uniform(170, 330), _balanco(rnd)                  # pessoa longe, parada
            v = rnd.uniform(-0.15, 0.15) * 100
            dist = [d0 + v * ti + bal(ti) for ti in t]
    elif classe == 'presente':
        d0, bal = rnd.uniform(25, 125), _balanco(rnd)
        v = rnd.gauss(0, 0.04) * 100
        dist = [d0 + v * ti + bal(ti) for ti in t]
    else:
        v = rnd.uniform(0.3, 1.5) * 100 * (-1 if classe == 'chegando' else 1)   # passo lento a normal
        d0 = rnd.uniform(70, 330) if classe == 'chegando' else rnd.uniform(30, 260)
        bal = _balanco(rnd)
        dist = [max(25, d0 + v * ti + bal(ti) * 0.5) for ti in t]
    return _leituras(rnd, dist)


def dados_sinteticos(n, semente):
    rnd = random.Random(semente)
    return [(amostra_sintetica(rnd, c), c) for _ in range(n // len(CLASSES)) for c in CLASSES]


def dados_gravados(pasta=PASTA_GRAVACOES):
    """CSVs de `presenca.py gravar` (colunas: tempo_s, d_cm, rotulo) → janelas deslizantes rotuladas."""
    janelas = []
    for arq in sorted(glob.glob(os.path.join(pasta, '*.csv'))):
        with open(arq, newline='', encoding='utf-8') as f:
            linhas = [(int(r['d_cm']), r['rotulo']) for r in csv.DictReader(f)]
        for i in range(len(linhas) - N_JANELA + 1):
            bloco = linhas[i:i + N_JANELA]
            rotulos = {r for _, r in bloco}
            if len(rotulos) == 1 and bloco[0][1] in CLASSES:
                janelas.append(([d for d, _ in bloco], bloco[0][1]))
    return janelas


# ─── Treino: softmax com descida de gradiente, em Python puro ────────────────────────

def treinar(dados, epocas=400, taxa=0.5, l2=1e-3):
    X = [caracteristicas(d) for d, _ in dados]
    y = [CLASSES.index(c) for _, c in dados]
    k, n = len(CLASSES), len(CARACTERISTICAS)
    media = [sum(x[j] for x in X) / len(X) for j in range(n)]
    escala = [math.sqrt(sum((x[j] - media[j]) ** 2 for x in X) / len(X)) or 1.0 for j in range(n)]
    Xs = [[(x[j] - media[j]) / escala[j] for j in range(n)] for x in X]
    W = [[0.0] * n for _ in range(k)]
    b = [0.0] * k
    for _ in range(epocas):
        gW = [[0.0] * n for _ in range(k)]
        gb = [0.0] * k
        for x, yi in zip(Xs, y):
            z = [b[c] + sum(W[c][j] * x[j] for j in range(n)) for c in range(k)]
            zmax = max(z)
            e = [math.exp(v - zmax) for v in z]
            s = sum(e)
            for c in range(k):
                g = e[c] / s - (1.0 if c == yi else 0.0)
                gb[c] += g
                for j in range(n):
                    gW[c][j] += g * x[j]
        m = len(Xs)
        for c in range(k):
            b[c] -= taxa * gb[c] / m
            for j in range(n):
                W[c][j] -= taxa * (gW[c][j] / m + l2 * W[c][j])
    return dict(media=media, escala=escala, pesos=W, vies=b)


def avaliar(modelo, dados):
    k = len(CLASSES)
    conf = [[0] * k for _ in range(k)]
    for d, c in dados:
        p, _ = prever(modelo, d)
        conf[CLASSES.index(c)][CLASSES.index(p)] += 1
    acertos = sum(conf[i][i] for i in range(k))
    return acertos / max(1, len(dados)), conf


def relatorio(acuracia, conf, n_treino, n_teste, n_gravadas):
    k = len(CLASSES)
    linhas = ['# Modelo de presença do TARS: métricas', '',
              f'Gerado por `presenca.py treinar`. Treino: {n_treino} janelas ({n_gravadas} gravadas no robô, '
              f'o resto sintético); teste: {n_teste} janelas sintéticas separadas, que o modelo não viu.', '',
              f'**Acurácia no teste: {acuracia * 100:.1f}%**', '',
              '| real ↓ / previsto → | ' + ' | '.join(CLASSES) + ' | revocação |',
              '|---|' + '---|' * (k + 1)]
    for i, c in enumerate(CLASSES):
        total = sum(conf[i]) or 1
        linhas.append(f'| **{c}** | ' + ' | '.join(str(v) for v in conf[i]) + f' | {conf[i][i] / total * 100:.0f}% |')
    prec = []
    for j in range(k):
        col = sum(conf[i][j] for i in range(k)) or 1
        prec.append(f'{conf[j][j] / col * 100:.0f}%')
    linhas.append('| precisão | ' + ' | '.join(prec) + ' | |')
    linhas += ['', 'Os dados sintéticos simulam o ruído do HC-SR04 (0,3–1,2 cm), falhas de eco (até 5%), '
               'ecos espúrios (até 2%) e o balanço natural de uma pessoa parada (0,5–4 cm). '
               'Com gravações reais em `gravacoes/` (`presenca.py gravar`), elas entram no treino.']
    return '\n'.join(linhas) + '\n'


def exportar_header(modelo, caminho=HEADER, acuracia=None):
    f = lambda v: f'{v:.7g}f'
    lst = lambda vs: '{' + ', '.join(f(v) for v in vs) + '}'
    texto = [
        '// modelo_presenca.h — GERADO por versao_final/ia/presenca.py (python presenca.py treinar). Não edite à mão.',
        f'// Regressão logística multiclasse: {len(CARACTERISTICAS)} características → {len(CLASSES)} classes'
        + (f'; acurácia no teste: {acuracia * 100:.1f}%.' if acuracia is not None else '.'),
        '#pragma once',
        f'#define PRESENCA_N_CLASSES {len(CLASSES)}',
        f'#define PRESENCA_N_CARAC {len(CARACTERISTICAS)}',
        '// classes: ' + ', '.join(f'{i} = {c}' for i, c in enumerate(CLASSES)),
        '// características: ' + ', '.join(CARACTERISTICAS),
        f'static const float PRESENCA_MEDIA[PRESENCA_N_CARAC] PROGMEM = {lst(modelo["media"])};',
        f'static const float PRESENCA_ESCALA[PRESENCA_N_CARAC] PROGMEM = {lst(modelo["escala"])};',
        'static const float PRESENCA_PESOS[PRESENCA_N_CLASSES][PRESENCA_N_CARAC] PROGMEM = {',
        *[f'  {lst(w)},' for w in modelo['pesos']],
        '};',
        f'static const float PRESENCA_VIES[PRESENCA_N_CLASSES] PROGMEM = {lst(modelo["vies"])};',
    ]
    with open(caminho, 'w', encoding='utf-8', newline='\n') as arq:
        arq.write('\n'.join(texto) + '\n')


def carregar_header(caminho=HEADER):
    """Lê o modelo de volta do header (o tars.py usa o mesmo modelo do Arduino, para o modo sem robô)."""
    import re
    with open(caminho, encoding='utf-8') as arq:
        txt = arq.read()
    def nums(nome):
        bloco = re.search(nome + r'[^=]*=\s*(\{.*?\});', txt, re.S).group(1)
        return [float(v) for v in re.findall(r'-?\d+\.?\d*(?:e-?\d+)?', bloco)]
    p = nums('PRESENCA_PESOS')
    n = len(CARACTERISTICAS)
    return dict(media=nums('PRESENCA_MEDIA'), escala=nums('PRESENCA_ESCALA'),
                pesos=[p[i * n:(i + 1) * n] for i in range(len(CLASSES))], vies=nums('PRESENCA_VIES'))


# ─── Gravação de dados reais pelo robô ───────────────────────────────────────────────

def _leituras_do_robo(a):
    from tars import Robo
    robo = Robo(a.porta, a.baud)
    robo.modo_autonomo(False)
    robo.leituras_brutas(True)
    try:
        while True:
            ev = robo.eventos.get()
            if ev.get('ev') == 'bruto':
                yield int(ev.get('d', 0))
    finally:
        robo.leituras_brutas(False)
        robo.modo_autonomo(True)


def gravar(a):
    os.makedirs(PASTA_GRAVACOES, exist_ok=True)
    arq = os.path.join(PASTA_GRAVACOES, f'{time.strftime("%Y%m%d_%H%M%S")}_{a.rotulo}.csv')
    print(f'Gravando "{a.rotulo}" por {a.segundos} s em {arq}. Faça o movimento agora.')
    fim = time.time() + a.segundos
    with open(arq, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['tempo_s', 'd_cm', 'rotulo'])
        inicio = time.time()
        for d in _leituras_do_robo(a):
            w.writerow([f'{time.time() - inicio:.2f}', d, a.rotulo])
            if time.time() > fim:
                break
    print('Pronto. Rode "python presenca.py treinar" para incluir no modelo.')


def ao_vivo(a):
    modelo = carregar_header()
    janela = []
    for d in _leituras_do_robo(a):
        janela = (janela + [d])[-N_JANELA:]
        if len(janela) == N_JANELA:
            c, p = prever(modelo, janela)
            barra = '#' * int((d or ALCANCE_CM) / 10)
            print(f'{d:4d} cm  {c:9s} {max(p) * 100:3.0f}%  {barra}')


def main():
    ap = argparse.ArgumentParser(description='Modelo de presença do TARS (HC-SR04)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    t = sub.add_parser('treinar')
    t.add_argument('--gravacoes', default=PASTA_GRAVACOES)
    t.add_argument('--semente', type=int, default=42)
    for nome in ('gravar', 'ao-vivo'):
        g = sub.add_parser(nome)
        g.add_argument('--porta', default='auto')
        g.add_argument('--baud', type=int, default=115200)
        if nome == 'gravar':
            g.add_argument('--rotulo', choices=CLASSES, required=True)
            g.add_argument('--segundos', type=int, default=30)
    a = ap.parse_args()
    if a.cmd == 'gravar':
        return gravar(a)
    if a.cmd == 'ao-vivo':
        return ao_vivo(a)
    gravadas = dados_gravados(a.gravacoes)
    treino = dados_sinteticos(6000, a.semente) + gravadas
    teste = dados_sinteticos(2000, a.semente + 1)
    modelo = treinar(treino)
    acuracia, conf = avaliar(modelo, teste)
    exportar_header(modelo, acuracia=acuracia)
    texto = relatorio(acuracia, conf, len(treino), len(teste), len(gravadas))
    with open(METRICAS, 'w', encoding='utf-8', newline='\n') as f:
        f.write(texto)
    print(texto)
    print(f'Gerados: {os.path.relpath(HEADER)} e {os.path.relpath(METRICAS)}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
