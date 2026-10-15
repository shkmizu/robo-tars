"""
projeto.py — fonte única de parâmetros, geometria 2D das peças e verificações de engenharia
do robô no estilo TARS (4 blocos de MDF 3 mm cortados a laser, 2 micro servos SG90).

Não depende de nenhum programa: `python projeto.py` confere torque, folgas, estabilidade,
espaço interno e comprimento dos cabos. `laser/exportar_laser.py` gera o DXF de corte;
`demo/gerar_demo.py` gera a demonstração 3D; RoboDoisBracos.py monta tudo no Fusion.

Arquitetura:
  - Corpo = os 2 blocos do meio, uma caixa só (com um vinco gravado no meio). Guarda o Arduino,
    o PCA9685, a tela OLED e os 2 SG90. Toda a fiação fica dentro dessa caixa.
  - Braços = os 2 blocos de fora. Giram em torno de um eixo NO MEIO da altura deles: o braço fica
    equilibrado (como uma gangorra) e o SG90 só vence atrito e aceleração.
  - Mancal de MDF: 2 discos colados na lateral do corpo; o braço gira apoiado neles. O peso do
    braço vai para o corpo, não para o eixo de plástico do SG90.
  - O horn do SG90 é parafusado num anteparo dentro do braço.

Convenções (mm, graus, gramas):
  mundo: X = lateral (lado "D" = +X, à direita de quem olha de frente), Y = para trás,
         Z = para cima; origem no centro da base do corpo.
  ombro: 0° = braço em pé ao lado do corpo, +90° = deitado para a frente, −90° = para trás.

Fontes das medidas dos componentes (ver README):
  SG90: desenho dimensional "SG90 Servo - Dimensions" (Aus Electronics Direct, TA0132).
  Arduino Uno R3: desenho oficial (furos 13,97/2,54; 15,24/50,8; 66,04/7,62; 66,04/35,56).
  PCA9685: Adafruit 815 — 62,5 × 25,4 mm, furos Ø2,5 com espaçamento 55,88 × 19,05 mm.
  OLED SSD1306 0,96": área ativa 21,74 × 10,86 mm (placa varia 27–30 mm: vai colada, sem furos).
"""
import math

# ─── Material e laser ────────────────────────────────────────────────────────────────
T = 3.0              # espessura REAL do MDF — meça com paquímetro ("3 mm" varia de 2,7 a 3,2)
KERF = 0.15          # largura do corte — confirme com o técnico / calibre com o "Pente de teste"
FOLGA = 0.0          # folga extra nos encaixes (+ = mais solto, − = mais justo)
CHAPA = (900.0, 600.0)  # chapa de MDF / mesa do laser
DENS_MDF = 0.75e-3   # g/mm³ (≈ 750 kg/m³)
DEDO = 18.0          # comprimento alvo de cada dente dos encaixes

# ─── Forma (TARS: 4 blocos iguais lado a lado) ───────────────────────────────────────
SW = 36.0            # largura de cada bloco (X); o corpo tem 2 blocos = 2·SW
SD = 84.0            # profundidade dos blocos (Y) — o Uno deitado + USB precisa de ≥ 81
H = 300.0            # altura do corpo (Z)
FOLGA_MESA = 3.0     # menor distância braço ↔ mesa em qualquer ângulo
BASE_FRENTE, BASE_TRAS = 0.0, 0.0     # braço equilibrado: o centro de massa quase não anda
LIMITE_OMBRO = (-90.0, 90.0)          # 180° de curso do SG90, centrado com o braço em pé
ANTEPARO_ALT = 70.0  # altura do anteparo que recebe o horn dentro do braço
ABA = 20.0           # abas do anteparo

# ─── Mancal de MDF (2 discos colados na lateral do corpo) ────────────────────────────
MANCAL_ENCOSTO_D = 64.0   # disco 1 (encosta na lateral): o braço roça nele de lado
MANCAL_D = 46.0           # disco 2: o furo do braço gira em volta dele
MANCAL_FOLGA = 0.4        # o furo do braço é desenhado 0,4 mm maior (+ o kerf = folga de giro)
MANCAL_FURO = 20.0        # furo do disco 2: passagem do ressalto e do eixo do SG90
ATRITO = 0.3              # MDF com MDF passado com vela/parafina
ACEL = 12.0               # rad/s² — pico do movimento suave (90° em 0,9 s)

# ─── Furos e fixação ─────────────────────────────────────────────────────────────────
FURO_M3 = 3.4
TSLOT_LARG = 3.2                   # canal do parafuso no rasgo-T
TSLOT_PORCA = (5.8, 2.7)           # alojamento da porca M3 (5,5 entre faces × 2,4) + folga
TSLOT_PROF_PORCA = 4.0
PARAFUSO_M3 = 12.0                 # M3×12 nos rasgos-T
FOLGA_JANELA = 0.2                 # folga por lado na janela do SG90
FURO_PILOTO = 1.4                  # pré-furo dos parafusos auto-atarraxantes do SG90 (Ø2,2)
FURO_OMBRO = 7.0                   # no anteparo: acesso ao parafuso do horn (referência da junta)
FURO_HORN = 2.2                    # no anteparo: M2 nos furos do horn (alargar o horn p/ 2,1 mm)
FURO_FONTE = 12.0                  # passa-cabo do plugue P4 da fonte (o plugue tem ~10 mm)
CHAVE_RECORTE = (19.0, 12.0)       # chave gangorra KCD1 (encaixe padrão 19 × 12 mm; lixar se justo)
FURO_PCA = 2.9                     # M2,5 (furo da placa: Ø2,5 Adafruit / Ø3 clones)
FURO_ALIVIO = 7.0                  # na base: cabeças dos parafusos dos espaçadores do Uno
ESPACADOR_ELETRONICA = 10.0
MASSA_EXTRA_G = 30.0               # fios, parafusos, capacitor

# ─── Critérios de projeto ────────────────────────────────────────────────────────────
PONTE_MIN = 2.0                    # menor faixa de MDF aceitável entre furos/bordas
FS_TORQUE = 3.0                    # torque de stall ÷ torque exigido
MARGEM_TOMBAMENTO = 10.0           # centro de massa ↔ borda da base
SOBRA_CABO = 30.0                  # comprimento extra mínimo em cada cabo (curvas, conectores)

# ─── Componentes comprados ───────────────────────────────────────────────────────────
# SG90 (desenho TA0132): referencial do servo com origem no eixo de saída, na face de baixo;
# "eixo_ponta" = distância do eixo até a ponta mais próxima do corpo; alturas a partir da base.
SG90 = dict(comp=22.7, larg=12.1, alt_corpo=22.7, alt_flange=15.9, esp_flange=2.4,
            comp_flange=32.4, furo_ponta=1.9, eixo_ponta=5.8, alt_ressalto=27.1,
            alt_eixo=30.7, r_ressalto=5.9, cabo=250.0, torque_kgcm=1.8, massa_g=10.0,
            horn_acima=1.0, horn_alt=2.5, horn_comp=32.0, horn_larg=6.9, horn_furos=(10.0, 14.0))
# Arduino Uno R3: contorno e furos do desenho oficial (origem no canto do conector USB).
UNO = dict(comp=68.58, larg=53.34, alt_comp=12.0, usb_saliencia=6.5, massa_g=25.0,
           furos=[(13.97, 2.54), (15.24, 50.8), (66.04, 7.62), (66.04, 35.56)],
           furo=FURO_M3, r_espacador=2.75)
# PCA9685 (Adafruit 815): furos centrados, espaçamento 55,88 × 19,05 mm.
_px, _py = (62.5 - 55.88) / 2, (25.4 - 19.05) / 2
PCA9685 = dict(comp=62.5, larg=25.4, alt_comp=11.0, usb_saliencia=0.0, massa_g=9.0,
               furos=[(_px, _py), (62.5 - _px, _py), (_px, 25.4 - _py), (62.5 - _px, 25.4 - _py)],
               furo=FURO_PCA, r_espacador=2.5)
# OLED 0,96" SSD1306 I²C: placa de 27–30 mm conforme o fabricante; colada atrás da janela.
OLED = dict(placa=(27.0, 27.5, 4.0), janela=(23.0, 12.0), massa_g=5.0)
OLED_X, OLED_Z = SW / 2, H - 70.0  # centro da tela: bloco D do corpo, perto do topo

# ─── Posições derivadas (lado D; o lado E é o D girado 180° em torno de Z) ──────────
# Braço com o eixo no meio: o canto de baixo gira num raio que não pode alcançar a mesa.
_A = H + T - FOLGA_MESA
MEIO_BRACO = math.floor(10 * (_A ** 2 - (SD / 2) ** 2) / (2 * _A)) / 10   # metade do comprimento
LZ_BRACO = 2 * MEIO_BRACO
Z_BRACO = H - LZ_BRACO
OMBRO_Y, OMBRO_Z = 0.0, H - MEIO_BRACO
X_SERVO = SW - T - (SG90['alt_flange'] + SG90['esp_flange'])   # base do SG90 (flange na face interna)
X_BRACO = SW + T                                                # o disco de encosto define o vão
X_ANTEPARO = X_SERVO + SG90['alt_eixo'] + SG90['horn_acima']    # face de cima do horn
CX_BRACO = X_BRACO + SW / 2
UNO_X0 = -UNO['larg'] / 2
UNO_Y0 = SD / 2 - T - UNO['usb_saliencia'] - 0.5     # USB virado para trás
PCA_Z0 = 40.0
BASE_Y0, BASE_Y1 = -SD / 2 - BASE_FRENTE, SD / 2 + BASE_TRAS

X_, Y_, Z_ = (1, 0, 0), (0, 1, 0), (0, 0, 1)
MX, BAIXO, FRENTE = (-1, 0, 0), (0, 0, -1), (0, -1, 0)


# ─── Geometria 2D ────────────────────────────────────────────────────────────────────
# Uma peça é uma lista de primitivas; a PRIMEIRA é sempre o contorno externo.
#   ('poly', [pts])         polígono fechado (corte)
#   ('circ', (cx, cy), r)   (corte)
#   ('path', [segmentos])   contorno fechado com ('L', p, q) e ('A', p, meio, q) (corte)
#   ('grav', p, q)          linha de gravação (vinco decorativo, potência baixa)

def retangulo(cx, cy, w, h):
    return ('poly', [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2),
                     (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)])


def circulo(cx, cy, d):
    return ('circ', (cx, cy), d / 2)


def sem_acento(s):
    import unicodedata
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()


def cortes(geo):
    return [g for g in geo if g[0] != 'grav']


def gravacoes(geo):
    return [g for g in geo if g[0] == 'grav']


def rasgo(cx, cy, vertical, kerf, folga):
    """Furo que recebe uma aba (ABA × T). O laser alarga furos e encolhe abas em `kerf`."""
    ao_longo, atraves = ABA - 2 * kerf + folga, T - kerf + folga
    return retangulo(cx, cy, atraves, ao_longo) if vertical else retangulo(cx, cy, ao_longo, atraves)


def _rasgo_t():
    """Rasgo-T: canal do parafuso M3 + alojamento da porca, como (ao longo, profundidade p/ dentro)."""
    ws, nw, nt = TSLOT_LARG / 2, TSLOT_PORCA[0] / 2, TSLOT_PORCA[1]
    dn, ls = TSLOT_PROF_PORCA, PARAFUSO_M3 - T + 1
    return [(-ws, 0), (-ws, dn), (-nw, dn), (-nw, dn + nt), (-ws, dn + nt), (-ws, ls),
            (ws, ls), (ws, dn + nt), (nw, dn + nt), (nw, dn), (ws, dn), (ws, 0)]


def n_dedos(comp):
    """Número de dentes numa borda: ímpar, para o padrão ser simétrico."""
    n = max(3, round(comp / DEDO))
    return n if n % 2 else n + 1


def centro_dente(comp, k):
    return (k + 0.5) * comp / n_dedos(comp)


def contorno_dedos(x0, y0, x1, y1, donos, tslots=None, kerf=0.0, folga=0.0):
    """Retângulo com encaixes dentados, percorrido no sentido anti-horário.
    donos = {'inf'|'dir'|'sup'|'esq': True/False}: True = esta peça fica com os dentes das
    pontas (e com o canto), False = com os do meio; borda ausente = lisa.
    tslots = {lado: [coordenada absoluta]} — rasgos-T em trechos que pertencem a esta peça.
    kerf/folga deslocam as fronteiras dos dentes: dente cresce, vão encolhe."""
    tslots = tslots or {}
    cantos = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    lados = ('inf', 'dir', 'sup', 'esq')
    comps = [abs(cantos[(i + 1) % 4][0] - cantos[i][0]) + abs(cantos[(i + 1) % 4][1] - cantos[i][1]) for i in range(4)]
    prof = []
    for lado, L in zip(lados, comps):
        dono = donos.get(lado)
        prof.append([0.0] if dono is None else
                    [0.0 if (k % 2 == 0) == dono else T for k in range(n_dedos(L))])
    s = (kerf - folga) / 2
    pts = []
    for i, lado in enumerate(lados):
        a, b, L, ps = cantos[i], cantos[(i + 1) % 4], comps[i], prof[i]
        d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        ni = (-d[1], d[0])                       # normal para dentro
        eixo = 0 if a[1] == b[1] else 1
        p_ant, p_prox, n = prof[i - 1][-1], prof[(i + 1) % 4][0], len(ps)

        def pt(t, p):
            return (a[0] + d[0] * t + ni[0] * p, a[1] + d[1] * t + ni[1] * p)

        for k, p in enumerate(ps):
            ini = p_ant if k == 0 else k * L / n + (s if p else -s)
            fim = L - p_prox if k == n - 1 else (k + 1) * L / n + (-s if p else s)
            pts.append(pt(ini, p))
            for c in sorted(tslots.get(lado, [])):
                tc = (c - a[eixo]) * (1 if d[eixo] > 0 else -1)
                if p == 0 and ini < tc < fim:
                    pts += [pt(tc + al, pr) for al, pr in _rasgo_t()]
            pts.append(pt(fim, p))
    limpos = [q for j, q in enumerate(pts) if math.dist(q, pts[j - 1]) > 1e-9]
    return ('poly', limpos)


def contorno_abas(x0, y0, x1, y1, abas):
    """Retângulo anti-horário com abas (saem T para fora). abas = {lado: [coord absoluta]}."""
    cantos = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    pts = []
    for i, lado in enumerate(('inf', 'dir', 'sup', 'esq')):
        a, b = cantos[i], cantos[(i + 1) % 4]
        eixo = 0 if a[1] == b[1] else 1
        sentido = 1 if b[eixo] > a[eixo] else -1
        d = (sentido, 0) if eixo == 0 else (0, sentido)
        n = (d[1], -d[0])  # normal para fora
        pts.append(a)
        for c in sorted(abas.get(lado, []), key=lambda c: (c - a[eixo]) * sentido):
            s = (c - a[eixo]) * sentido
            for al, pr in [(-ABA / 2, 0), (-ABA / 2, T), (ABA / 2, T), (ABA / 2, 0)]:
                pts.append((a[0] + d[0] * (s + al) + n[0] * pr, a[1] + d[1] * (s + al) + n[1] * pr))
    return ('poly', pts)


# Encaixes de uma caixa: frente/trás ficam com os cantos; as laterais ficam com as pontas
# nas bordas de cima e de baixo; topo e fundo encaixam por dentro de todas.
DONOS_FT = dict(inf=True, dir=True, sup=True, esq=True)
DONOS_LAT = dict(inf=True, dir=False, sup=True, esq=False)
DONOS_TF = dict(inf=False, dir=False, sup=False, esq=False)


def _dentes(comp, impares):
    """Centros de 2 dentes perto das pontas (ímpares = os do meio do padrão; pares = os das pontas)."""
    n = n_dedos(comp)
    ks = (1, n - 2) if impares else (2, n - 3)
    return [centro_dente(comp, k) for k in ks]


# Tampas removíveis: o parafuso atravessa a tampa num dente DELA e entra num "reforço" colado
# por dentro da parede vizinha. Sem o reforço, o furo M3 ficaria no meio de uma parede de 3 mm,
# rente à borda da tampa, e romperia a borda.
REFORCO = (16.0, 24.0)   # ao longo do parafuso × altura
Z_TAMPA_CORPO = _dentes(H, False)        # dentes da tampa traseira (pares)
Z_TAMPA_BRACO = _dentes(LZ_BRACO, True)  # dentes da tampa do braço (ímpares)


def g_reforco(kerf, folga):
    """Local: x = 0 na borda que encosta na tampa, para dentro; rasgo-T no meio dessa borda."""
    return [contorno_dedos(0, -REFORCO[1] / 2, REFORCO[0], REFORCO[1] / 2, {}, {'esq': [0.0]})]


def _janela_servo():
    """Furos do SG90 numa chapa paralela à lateral, em coordenadas (Y, Z − eixo):
    janela do corpo (que atravessa a chapa) + 2 pré-furos dos parafusos das abas."""
    s, c = SG90, FOLGA_JANELA
    e, L = s['eixo_ponta'], s['comp']
    aba = (s['comp_flange'] - L) / 2 - s['furo_ponta']        # do fim do corpo ao furo da aba
    geo = [retangulo(0, (e - (L - e)) / 2, s['larg'] + 2 * c, L + 2 * c)]
    geo += [circulo(0, z, FURO_PILOTO) for z in (e + aba, -(L - e) - aba)]
    return geo


def _deslocar(geo, dy):
    out = []
    for g in geo:
        if g[0] == 'circ':
            out.append(('circ', (g[1][0], g[1][1] + dy), g[2]))
        else:
            out.append(('poly', [(x, y + dy) for x, y in g[1]]))
    return out


# ─── Peças de MDF: corpo ─────────────────────────────────────────────────────────────

def g_corpo_frente(kerf, folga):
    """Local: x = X, y = Z, vista de fora."""
    return [contorno_dedos(-SW, 0, SW, H, DONOS_FT, kerf=kerf, folga=folga),
            retangulo(OLED_X, OLED_Z, *OLED['janela']),
            ('grav', (0, T), (0, H - T))]


def g_corpo_tras(kerf, folga):
    """Tampa removível (4 parafusos nos reforços). Local: x = −X, y = Z, vista de fora."""
    geo = [contorno_dedos(-SW, 0, SW, H, DONOS_FT, kerf=kerf, folga=folga)]
    geo += [circulo(sx * (SW - 1.5 * T), z, FURO_M3) for sx in (-1, 1) for z in Z_TAMPA_CORPO]
    # janela do USB e do jack do Uno, com folga (a posição dos conectores varia entre clones)
    geo.append(retangulo(-(UNO_X0 + 23.5), T + ESPACADOR_ELETRONICA + 7, 47, 18))
    geo.append(circulo(-OLED_X, 60, FURO_FONTE))
    geo.append(retangulo(-OLED_X, 95, *CHAVE_RECORTE))
    geo.append(('grav', (0, 40), (0, H - T)))
    return geo


def g_corpo_lateral(kerf, folga):
    """Local: x = Y, y = Z. Igual para os dois lados (cortar 2): SG90 + furos do PCA9685."""
    geo = [contorno_dedos(-SD / 2, 0, SD / 2, H, DONOS_LAT, kerf=kerf, folga=folga)]
    geo += _deslocar(_janela_servo(), OMBRO_Z)
    for f in PCA9685['furos']:
        _, y, z = para_mundo(INST_PCA, (f[0], f[1], 0))
        geo.append(circulo(y, z, PCA9685['furo']))
    return geo


def g_corpo_topo(kerf, folga):
    return [contorno_dedos(-SW, -SD / 2, SW, SD / 2, DONOS_TF, kerf=kerf, folga=folga),
            ('grav', (0, -SD / 2 + T), (0, SD / 2 - T))]


def g_corpo_fundo(kerf, folga):
    geo = [contorno_dedos(-SW, -SD / 2, SW, SD / 2, DONOS_TF, kerf=kerf, folga=folga)]
    for f in UNO['furos']:
        x, y, _ = para_mundo(INST_UNO, (f[0], f[1], 0))
        geo.append(circulo(x, y, UNO['furo']))
    return geo


def g_base(kerf, folga):
    """Base colada sob o corpo; cobre as cabeças dos parafusos dos espaçadores do Uno."""
    geo = [retangulo(0, (BASE_Y0 + BASE_Y1) / 2, 2 * SW, BASE_Y1 - BASE_Y0)]
    for f in UNO['furos']:
        x, y, _ = para_mundo(INST_UNO, (f[0], f[1], 0))
        geo.append(circulo(x, y, FURO_ALIVIO))
    return geo


def g_mancal_encosto(kerf, folga):
    """Disco 1 do mancal, colado na lateral do corpo. Local: x = Y, y = Z − eixo.
    Tem a mesma janela do SG90: o topo do servo e os parafusos das abas passam por ele."""
    return [circulo(0, 0, MANCAL_ENCOSTO_D)] + _janela_servo()


def g_mancal_eixo(kerf, folga):
    """Disco 2 do mancal, colado no disco 1: o braço gira em volta dele."""
    return [circulo(0, 0, MANCAL_D), circulo(0, 0, MANCAL_FURO)]


# ─── Peças de MDF: braço ─────────────────────────────────────────────────────────────

def g_braco_ft(kerf, folga):
    """Frente e trás do braço (iguais, cortar 4). Local: x = X − centro do braço, y = Z − base do braço."""
    u = X_ANTEPARO - CX_BRACO + T / 2
    geo = [contorno_dedos(-SW / 2, 0, SW / 2, LZ_BRACO, DONOS_FT, kerf=kerf, folga=folga)]
    geo += [rasgo(u, OMBRO_Z - Z_BRACO + j * ANTEPARO_ALT / 4, True, kerf, folga) for j in (-1, 1)]
    return geo


def g_braco_interna(kerf, folga):
    """Lateral do braço voltada para o corpo: o furo gira em volta do disco 2 do mancal."""
    return [contorno_dedos(-SD / 2, 0, SD / 2, LZ_BRACO, DONOS_LAT, kerf=kerf, folga=folga),
            circulo(0, OMBRO_Z - Z_BRACO, MANCAL_D + MANCAL_FOLGA)]


def g_braco_externa(kerf, folga):
    """Tampa removível do braço: dá acesso ao parafuso do horn."""
    geo = [contorno_dedos(-SD / 2, 0, SD / 2, LZ_BRACO, DONOS_LAT, kerf=kerf, folga=folga)]
    geo += [circulo(sy * (SD / 2 - 1.5 * T), z, FURO_M3) for sy in (-1, 1) for z in Z_TAMPA_BRACO]
    return geo


def g_braco_tf(kerf, folga):
    return [contorno_dedos(-SW / 2, -SD / 2, SW / 2, SD / 2, DONOS_TF, kerf=kerf, folga=folga)]


def g_anteparo(kerf, folga):
    """Placa dentro do braço onde o horn duplo do SG90 é parafusado (M2 nos furos a 10 e 14 mm
    do centro). Local: x = Y, y = Z − eixo."""
    a = ANTEPARO_ALT / 4
    geo = [contorno_abas(-(SD / 2 - T), -ANTEPARO_ALT / 2, SD / 2 - T, ANTEPARO_ALT / 2,
                         {'dir': [-a, a], 'esq': [-a, a]}),
           circulo(0, 0, FURO_OMBRO)]
    geo += [circulo(s * r, 0, FURO_HORN) for s in (-1, 1) for r in SG90['horn_furos']]
    return geo


def g_pente(kerf, folga):
    """Calibração (sem compensação): 11 rasgos de T−0,30 a T+0,20 mm, passo 0,05.
    O furo-marcador fica sobre o rasgo mais estreito."""
    n, passo, alt = 11, 12.0, 35.0
    comp = passo * (n + 1)
    geo = [retangulo(comp / 2, alt / 2, comp, alt), circulo(passo, alt - 4, 3)]
    geo += [retangulo(passo * (i + 1), alt / 2, T - 0.30 + 0.05 * i, ABA) for i in range(n)]
    return geo


# ─── Montagem: referenciais de cada instância ───────────────────────────────────────
# inst = (origem, eixo x local, eixo z local); z é a direção da espessura.

def girar_z(inst):
    """Mesma peça girada 180° em torno do eixo vertical: lado D → lado E."""
    f = lambda v: (-v[0], -v[1], v[2])
    return tuple(f(v) for v in inst)


def faces(cx, lx, ly, z0, lz, tras_de_fora):
    """Referenciais das 6 faces de uma caixa (centro X = cx, centrada em Y, base em z0)."""
    tras = ((cx, ly / 2 - T, z0), MX, Y_) if tras_de_fora else ((cx, ly / 2, z0), X_, FRENTE)
    return dict(frente=((cx, -ly / 2 + T, z0), X_, FRENTE), tras=tras,
                lat_pos=((cx + lx / 2 - T, 0, z0), Y_, X_), lat_neg=((cx - lx / 2, 0, z0), Y_, X_),
                fundo=((cx, 0, z0), X_, Z_), topo=((cx, 0, z0 + lz - T), X_, Z_))


CORPO = faces(0, 2 * SW, SD, 0, H, True)
BRACO = faces(CX_BRACO, SW, SD, Z_BRACO, LZ_BRACO, False)
INST_UNO = ((UNO_X0, UNO_Y0, T), FRENTE, Z_)                       # deitado no fundo
INST_PCA = ((-SW + T, -8.0, PCA_Z0), Z_, X_)    # em pé na lateral E, metade da frente


def _par(inst):
    return [inst, girar_z(inst)]


# reforços: no corpo, colados nas laterais junto à tampa traseira; no braço, colados na
# frente e na trás junto à tampa externa
_REF_CORPO = [((x, SD / 2 - T, z), FRENTE, X_) for x in (SW - 2 * T, -SW + T) for z in Z_TAMPA_CORPO]
_REF_BRACO = [((CX_BRACO + SW / 2 - T, y, Z_BRACO + z), MX, Y_)
              for y in (-SD / 2 + T, SD / 2 - 2 * T) for z in Z_TAMPA_BRACO]

PECAS = [
    dict(nome='Base', geom=g_base, grupo='tronco', inst=[((0, 0, -T), X_, Z_)]),
    dict(nome='Corpo frente', geom=g_corpo_frente, grupo='tronco', inst=[CORPO['frente']]),
    dict(nome='Corpo trás (tampa)', geom=g_corpo_tras, grupo='tronco', inst=[CORPO['tras']]),
    dict(nome='Corpo lateral', geom=g_corpo_lateral, grupo='tronco', inst=[CORPO['lat_pos'], CORPO['lat_neg']]),
    dict(nome='Corpo topo', geom=g_corpo_topo, grupo='tronco', inst=[CORPO['topo']]),
    dict(nome='Corpo fundo', geom=g_corpo_fundo, grupo='tronco', inst=[CORPO['fundo']]),
    dict(nome='Mancal disco de encosto', geom=g_mancal_encosto, grupo='tronco',
         inst=_par(((SW, OMBRO_Y, OMBRO_Z), Y_, X_))),
    dict(nome='Mancal disco do eixo', geom=g_mancal_eixo, grupo='tronco',
         inst=_par(((SW + T, OMBRO_Y, OMBRO_Z), Y_, X_))),
    dict(nome='Braço frente/trás', geom=g_braco_ft, grupo='braco', inst=_par(BRACO['frente']) + _par(BRACO['tras'])),
    dict(nome='Braço lateral interna', geom=g_braco_interna, grupo='braco', inst=_par(BRACO['lat_neg'])),
    dict(nome='Braço lateral externa (tampa)', geom=g_braco_externa, grupo='braco', inst=_par(BRACO['lat_pos'])),
    dict(nome='Braço topo/fundo', geom=g_braco_tf, grupo='braco', inst=_par(BRACO['topo']) + _par(BRACO['fundo'])),
    dict(nome='Anteparo do horn', geom=g_anteparo, grupo='braco', inst=_par(((X_ANTEPARO, OMBRO_Y, OMBRO_Z), Y_, X_))),
    dict(nome='Reforço do corpo', geom=g_reforco, grupo='tronco', inst=_REF_CORPO),
    dict(nome='Reforço do braço', geom=g_reforco, grupo='braco', inst=[i for r in _REF_BRACO for i in _par(r)]),
    dict(nome='Pente de teste', geom=g_pente, grupo=None, inst=[]),
]


# ─── Peças compradas (sólidos aproximados para checar espaço e interferência) ────────

def _solidos_servo(s):
    e, aba = s['eixo_ponta'], (s['comp_flange'] - s['comp']) / 2
    zf = s['alt_flange'] + s['esp_flange'] / 2
    return [('caixa', (s['comp'] / 2 - e, 0, s['alt_corpo'] / 2), (s['comp'], s['larg'], s['alt_corpo'])),
            ('caixa', (-e - aba / 2, 0, zf), (aba, s['larg'], s['esp_flange'])),
            ('caixa', (s['comp'] - e + aba / 2, 0, zf), (aba, s['larg'], s['esp_flange'])),
            ('cil', (0, 0, s['alt_corpo']), (0, 0, s['alt_ressalto']), s['r_ressalto']),
            ('cil', (0, 0, s['alt_ressalto']), (0, 0, s['alt_eixo']), 2.4)]


def _solidos_placa(p):
    z, sal = ESPACADOR_ELETRONICA, p['usb_saliencia']
    return ([('caixa', (p['comp'] / 2, p['larg'] / 2, z + 0.8), (p['comp'], p['larg'], 1.6)),
             ('caixa', ((p['comp'] - sal) / 2, p['larg'] / 2, z + 1.6 + p['alt_comp'] / 2),
              (p['comp'] + sal, p['larg'], p['alt_comp']))]
            + [('cil', (x, y, 0), (x, y, z), p['r_espacador']) for x, y in p['furos']])


def _cm_placa(p):
    return (p['comp'] / 2, p['larg'] / 2, ESPACADOR_ELETRONICA + 5)


# SG90 em pé dentro do corpo: eixo de saída para fora (+X), corpo descendo a partir do eixo
INST_SERVO = ((X_SERVO, OMBRO_Y, OMBRO_Z), BAIXO, X_)
_HORN_Z0 = SG90['alt_eixo'] + SG90['horn_acima'] - SG90['horn_alt']
COMPRADOS = [
    dict(nome='Servo SG90', solidos=_solidos_servo(SG90), grupo='tronco', massa=SG90['massa_g'],
         cm=(SG90['comp'] / 2 - SG90['eixo_ponta'], 0, SG90['alt_corpo'] / 2), inst=_par(INST_SERVO)),
    dict(nome='Horn SG90', solidos=[('caixa', (0, 0, _HORN_Z0 + SG90['horn_alt'] - 0.75),
                                     (SG90['horn_larg'], SG90['horn_comp'], 1.5)),
                                    ('cil', (0, 0, _HORN_Z0), (0, 0, _HORN_Z0 + SG90['horn_alt']), SG90['horn_larg'] / 2)],
         grupo='braco', massa=0.3, cm=(0, 0, 0), inst=_par(INST_SERVO)),
    dict(nome='Arduino Uno', solidos=_solidos_placa(UNO), grupo='tronco',
         massa=UNO['massa_g'], cm=_cm_placa(UNO), inst=[INST_UNO]),
    dict(nome='PCA9685', solidos=_solidos_placa(PCA9685), grupo='tronco',
         massa=PCA9685['massa_g'], cm=_cm_placa(PCA9685), inst=[INST_PCA]),
    dict(nome='OLED SSD1306', solidos=[('caixa', (0, 0, OLED['placa'][2] / 2), OLED['placa'])],
         grupo='tronco', massa=OLED['massa_g'], cm=(0, 0, 2), inst=[((OLED_X, -SD / 2 + T, OLED_Z), X_, Y_)]),
]


# ─── Ligações: de onde até onde vai cada cabo, e de que comprimento ele é ─────────────
# Pontos nos referenciais locais dos componentes (posições aproximadas dos conectores).
def _pt(inst, p):
    return para_mundo(inst, p)


def ligacoes():
    e, L = SG90['eixo_ponta'], SG90['comp']
    zc = ESPACADOR_ELETRONICA + 1.6 + 8.5                      # topo dos pinos
    saida_servo = lambda inst: _pt(inst, (L - e, 0, 3))         # cabo sai pela ponta de baixo
    pca_servos = _pt(INST_PCA, (PCA9685['comp'] * 0.3, PCA9685['larg'] - 3, zc))
    pca_ctrl_baixo = _pt(INST_PCA, (2, PCA9685['larg'] / 2, zc))
    pca_ctrl_cima = _pt(INST_PCA, (PCA9685['comp'] - 2, PCA9685['larg'] / 2, zc))
    pca_borne = _pt(INST_PCA, (PCA9685['comp'] / 2, 2, ESPACADOR_ELETRONICA + 8))
    uno_i2c = _pt(INST_UNO, (64.0, 2.5, zc))                    # A4/A5 + 5V/GND na borda de baixo
    oled_pinos = _pt(COMPRADOS[4]['inst'][0], (0, 12.0, 4))
    entrada = (OLED_X, SD / 2 - T, 60.0)
    chave = (OLED_X, SD / 2 - T, 95.0)
    s1, s2 = (saida_servo(i) for i in _par(INST_SERVO))
    return [  # (descrição, de, até, comprimento do cabo disponível)
        ('SG90 D → PCA9685 canal 0 (cabo do servo)', s1, pca_servos, SG90['cabo']),
        ('SG90 E → PCA9685 canal 1 (cabo do servo)', s2, pca_servos, SG90['cabo']),
        ('Uno A4/A5/5V/GND → PCA9685 (jumper macho-fêmea 20 cm)', uno_i2c, pca_ctrl_baixo, 200.0),
        ('PCA9685 → OLED SDA/SCL/VCC/GND (jumper fêmea-fêmea 30 cm)', pca_ctrl_cima, oled_pinos, 300.0),
        ('Plugue da fonte → chave (fio 22 AWG 30 cm)', entrada, chave, 300.0),
        ('Chave → borne V+ do PCA9685 (fio 22 AWG 30 cm)', chave, pca_borne, 300.0),
    ]


# ─── Utilidades geométricas ──────────────────────────────────────────────────────────

def cruz(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def para_mundo(inst, p):
    o, ex, ez = inst
    ey = cruz(ez, ex)
    return tuple(o[i] + ex[i] * p[0] + ey[i] * p[1] + ez[i] * p[2] for i in range(3))


def segmentos(prim):
    """Contorno fechado como lista de ('L', p, q) e ('A', p, meio, q)."""
    if prim[0] == 'poly':
        pts = prim[1]
        return [('L', pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    return prim[1]


def _arco(p, m, q, n=16):
    (ax, ay), (bx, by), (cx, cy) = p, m, q
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    r = math.hypot(ax - ux, ay - uy)
    a0, am, a1 = (math.atan2(y - uy, x - ux) for x, y in (p, m, q))
    volta = 2 * math.pi
    giro = (a1 - a0) % volta
    if (am - a0) % volta > giro:  # o meio não está no sentido anti-horário: vai pelo outro lado
        giro -= volta
    return [(ux + r * math.cos(a0 + giro * i / n), uy + r * math.sin(a0 + giro * i / n)) for i in range(n + 1)]


def amostrar(prim):
    if prim[0] == 'circ':
        (cx, cy), r = prim[1], prim[2]
        return [(cx + r * math.cos(math.tau * i / 64), cy + r * math.sin(math.tau * i / 64)) for i in range(64)]
    pts = []
    for seg in segmentos(prim):
        pts += [seg[1]] if seg[0] == 'L' else _arco(*seg[1:])[:-1]
    return pts


def area(prim):
    pts = amostrar(prim)
    return abs(sum(pts[i - 1][0] * p[1] - p[0] * pts[i - 1][1] for i, p in enumerate(pts))) / 2


def caixa(prim):
    pts = amostrar(prim)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


# ─── Massas, poses e verificações ────────────────────────────────────────────────────

def massas():
    """[(grupo, massa_g, ponto no mundo)] com os braços em pé (0°)."""
    out = []
    for p in PECAS:
        if not p['inst']:
            continue
        geo = cortes(p['geom'](0, 0))
        m = (area(geo[0]) - sum(area(g) for g in geo[1:])) * T * DENS_MDF
        x0, y0, x1, y1 = caixa(geo[0])
        out += [(p['grupo'], m, para_mundo(i, ((x0 + x1) / 2, (y0 + y1) / 2, T / 2))) for i in p['inst']]
    for c in COMPRADOS:
        out += [(c['grupo'], c['massa'], para_mundo(i, c['cm'])) for i in c['inst']]
    out.append(('tronco', MASSA_EXTRA_G, (0, 0, H / 3)))
    return out


def _girar(p, graus):
    """Gira p em torno do eixo dos ombros; positivo = para a frente."""
    c, s = math.cos(math.radians(graus)), math.sin(math.radians(graus))
    y, z = p[1] - OMBRO_Y, p[2] - OMBRO_Z
    return (p[0], OMBRO_Y + y * c + z * s, OMBRO_Z - y * s + z * c)


def posicionar(grupo, p, ang_d, ang_e):
    if grupo != 'braco':
        return p
    return _girar(p, ang_d if p[0] > 0 else ang_e)


_PASSO = range(int(LIMITE_OMBRO[0]), int(LIMITE_OMBRO[1]) + 1, 15)
POSES = [(a, a) for a in _PASSO] + [(a, -a) for a in _PASSO]   # juntos e alternados (passada)


def analisar():
    ms = massas()
    total = sum(m for _, m, _ in ms)
    m_braco = sum(m for g, m, p in ms if g == 'braco' and p[0] > 0)
    estatico = 0.0
    margem = chao = math.inf
    for a, b in POSES:
        m1 = sx = sy = 0.0
        for g, m, p in ms:
            q = posicionar(g, p, a, b)
            sx, sy = sx + m * q[0], sy + m * q[1]
            if g == 'braco' and p[0] > 0:
                m1 += m * (q[1] - OMBRO_Y)
        estatico = max(estatico, abs(m1) / 1e4)             # g·mm → kgf·cm
        cx, cy = sx / total, sy / total
        margem = min(margem, cy - BASE_Y0, BASE_Y1 - cy, SW - abs(cx))
        for y in (-SD / 2, SD / 2):                         # cantos do braço girando
            for z in (Z_BRACO, H):
                chao = min(chao, _girar((0, y, z), a)[2] + T)
    inercia = m_braco / 1000 * (LZ_BRACO ** 2 + SD ** 2) / 12          # kg·mm²
    dinamico = inercia * ACEL / 1000 / 9.807 / 10                      # N·mm → kgf·cm
    atrito = ATRITO * m_braco / 1000 * 9.807 * MANCAL_D / 2 / 9.807 / 10
    return dict(massa=total, m_braco=m_braco, estatico=estatico, dinamico=dinamico, atrito=atrito,
                torque=estatico + dinamico + atrito, margem=margem, chao=chao)


def verificar():
    """[(ok, texto)] — todas devem passar antes de cortar."""
    r = analisar()
    s = SG90
    aba = (s['comp_flange'] - s['comp']) / 2 - s['furo_ponta']
    ponte = aba - FOLGA_JANELA - FURO_PILOTO / 2
    topo_corpo = X_SERVO + s['alt_corpo']
    ressalto = math.hypot(6.0, 2.7) + 0.0                       # lóbulo do ressalto a 6 mm do eixo
    horn_baixo = X_ANTEPARO - s['horn_alt']
    folga_horn = horn_baixo - (X_BRACO + T)
    uno = (UNO_X0, UNO_Y0 - UNO['comp'], UNO_X0 + UNO['larg'], UNO_Y0 + UNO['usb_saliencia'])
    uno_ok = -SW + T <= uno[0] and uno[2] <= SW - T and -SD / 2 + T <= uno[1] and uno[3] <= SD / 2 - T
    z_servo = (OMBRO_Z - (s['comp'] - s['eixo_ponta']) - aba - 2, OMBRO_Z + s['eixo_ponta'] + aba + 2)
    topo_uno = T + ESPACADOR_ELETRONICA + 1.6 + 20                     # com os jumpers encaixados
    y_pca = (INST_PCA[0][1] - PCA9685['larg'], INST_PCA[0][1])
    z_pca = (PCA_Z0, PCA_Z0 + PCA9685['comp'])
    y_ref = (SD / 2 - T - REFORCO[0], SD / 2 - T)
    pca_ok = topo_uno < z_pca[0] and z_pca[1] < z_servo[0] and y_pca[0] >= -SD / 2 + T and y_pca[1] < y_ref[0]
    # os parafusos do PCA9685 saem na face externa da lateral: não podem cair sob o disco do mancal
    for f in PCA9685['furos']:
        _, y, z = para_mundo(INST_PCA, (f[0], f[1], 0))
        pca_ok &= math.hypot(y - OMBRO_Y, z - OMBRO_Z) > MANCAL_ENCOSTO_D / 2 + 4
    # pinos do OLED saem ~23 mm para trás (pino + conector): não podem alcançar o SG90 D
    oled_ok = OLED_X + OLED['janela'][0] / 2 <= SW - T - PONTE_MIN and \
        (OLED_Z - OLED['placa'][1] / 2 > z_servo[1] or -SD / 2 + T + 4 + 23 < -s['larg'] / 2)
    ref_ok = all(not (z_servo[0] - REFORCO[1] / 2 < z < z_servo[1] + REFORCO[1] / 2) or y_ref[0] > s['larg'] / 2
                 for z in Z_TAMPA_CORPO)
    cabos = []
    for desc, a, b, comp in ligacoes():
        precisa = 1.2 * sum(abs(a[i] - b[i]) for i in range(3)) + SOBRA_CABO   # caminho em "L" + 20%
        cabos.append((precisa <= comp, desc, precisa, comp))
    grandes = []
    for p in PECAS:
        x0, y0, x1, y1 = caixa(p['geom'](0, 0)[0])
        w, h = sorted((x1 - x0, y1 - y0))
        if w > min(CHAPA) or h > max(CHAPA):
            grandes.append(p['nome'])
    fs = s['torque_kgcm'] / r['torque']
    out = [
        (ponte >= PONTE_MIN, f'Ponte de MDF entre a janela do SG90 e o pré-furo da aba: {ponte:.1f} mm (mín. {PONTE_MIN})'),
        (X_SERVO >= 1, f'Os dois SG90 dentro do corpo não se tocam: vão de {2 * X_SERVO:.1f} mm'),
        (topo_corpo <= SW + T and ressalto < MANCAL_FURO / 2,
         f'Topo do SG90 cabe na janela do disco de encosto e o ressalto no furo Ø{MANCAL_FURO:g} do disco do eixo'),
        (folga_horn >= 0.5 and X_ANTEPARO + T <= X_BRACO + SW - T,
         f'Horn e anteparo ficam dentro do braço (horn a {folga_horn:.1f} mm da lateral interna)'),
        (r['chao'] >= FOLGA_MESA, f'Braço ↔ mesa em qualquer ângulo: {r["chao"]:.1f} mm (mín. {FOLGA_MESA})'),
        (fs >= FS_TORQUE, f'Ombro: desequilíbrio {r["estatico"]:.2f} + aceleração {r["dinamico"]:.2f} + atrito '
                          f'{r["atrito"]:.2f} = {r["torque"]:.2f} kgf·cm; SG90 dá {s["torque_kgcm"]} → FS {fs:.1f}'),
        (r['margem'] >= MARGEM_TOMBAMENTO,
         f'Centro de massa ↔ borda da base na pior pose: {r["margem"]:.0f} mm (massa total {r["massa"]:.0f} g)'),
        (uno_ok and pca_ok, 'Uno deitado (com jumpers) e PCA9685 em pé cabem sem tocar SG90 nem reforços'),
        (oled_ok, 'Janela da tela longe dos encaixes; pinos/conectores do OLED não alcançam o SG90'),
        (ref_ok, 'Reforços da tampa traseira não tocam os SG90'),
    ]
    out += [(ok, f'Cabo {desc}: precisa ~{p:.0f} mm, tem {c:.0f} mm') for ok, desc, p, c in cabos]
    out.append((not grandes, f'Todas as peças cabem na chapa {CHAPA[0]:g}×{CHAPA[1]:g}' +
                (f' — exceto {grandes}' if grandes else '')))
    return out


def lista_materiais():
    """[(categoria, item, qtd, observação)]"""
    linhas = [('Corte a laser', f'{p["nome"]} (MDF {T:g} mm)', max(1, len(p['inst'])),
               'calibração — cortar antes' if not p['inst'] else
               ('tem gravação (vinco)' if gravacoes(p['geom'](0, 0)) else '')) for p in PECAS]
    return linhas + [
        ('Eletrônica', 'Micro servo SG90 (vem com horns e 2 parafusos)', 2, 'braços'),
        ('Eletrônica', 'Arduino Uno R3 + cabo USB', 1, 'alimentado pelo USB'),
        ('Eletrônica', 'Driver de servos PCA9685 (16 canais, I²C)', 1, 'furos com espaçamento 55,88 × 19,05'),
        ('Eletrônica', 'Display OLED 0,96" SSD1306 I²C (4 pinos, 128×64)', 1, 'endereço 0x3C'),
        ('Eletrônica', 'Fonte 5 V 2 A com plugue P4', 1, 'alimenta só os servos'),
        ('Eletrônica', 'Adaptador P4 fêmea com borne', 1, 'recebe a fonte dentro do corpo'),
        ('Eletrônica', 'Capacitor eletrolítico 470 µF 10 V', 1, 'no borne V+ do PCA9685'),
        ('Eletrônica', 'Chave gangorra KCD1 (2 pinos)', 1, f'recorte {CHAVE_RECORTE[0]:g}×{CHAVE_RECORTE[1]:g} mm'),
        ('Eletrônica', 'Módulo Bluetooth HC-05', 1, 'comandos da IA sem fio (D10/D11)'),
        ('Eletrônica', 'Resistores 1 kΩ e 2 kΩ', '1 + 1', 'divisor de tensão no RXD do HC-05'),
        ('Eletrônica', 'Jumper macho-fêmea 20 cm', 8, 'Uno ↔ PCA9685 e Uno ↔ HC-05'),
        ('Eletrônica', 'Jumper fêmea-fêmea 30 cm', 4, 'PCA9685 ↔ OLED (20 cm não alcança)'),
        ('Eletrônica', 'Fio 22 AWG vermelho e preto', '1 m', 'fonte → chave → PCA9685'),
        ('Fixação', f'Parafuso M3×{PARAFUSO_M3:g} + porca M3', 4 + 4 * 2, '4 na tampa do corpo, 8 nas tampas dos braços'),
        ('Fixação', 'Espaçador M3×10 macho-fêmea + porca M3 + parafuso M3×6', 4, 'Arduino'),
        ('Fixação', 'Espaçador M2,5×10 + parafuso M2,5×6 (2 por espaçador)', 4, 'PCA9685'),
        ('Fixação', 'Parafuso M2×8 + porca M2', 8, 'horn → anteparo (alargar os furos do horn p/ 2,1 mm)'),
        ('Fixação', 'Fita dupla-face espessa', 1, 'prende o OLED atrás da janela'),
        ('Consumível', 'Cola PVA (cola branca para madeira)', 1, 'caixas (exceto as tampas), base e mancais'),
        ('Consumível', 'Vela ou parafina', 1, 'passar no mancal (disco do eixo e furo do braço)'),
    ]


def relatorio():
    linhas = ['Verificações de projeto:']
    linhas += [('  OK    ' if ok else '  FALHA ') + txt for ok, txt in verificar()]
    linhas.append(f'Dimensões: altura {H + T:g} mm (com base) × largura {2 * (CX_BRACO + SW / 2):.0f} mm '
                  f'× profundidade {SD:g} mm; braços de {LZ_BRACO:.1f} mm com o eixo no meio (Z = {OMBRO_Z:.1f})')
    return '\n'.join(linhas)


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')  # console do Windows usa cp1252 por padrão
    print(relatorio())
    raise SystemExit(0 if all(ok for ok, _ in verificar()) else 1)
