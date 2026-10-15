"""Gera demo/robo_demo.html (visualizador 3D) a partir de projeto.py: `python demo/gerar_demo.py`."""
import json, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, '..', 'fusion', 'RoboDoisBracos'))
import projeto as P


def _r(pts):
    return [[round(x, 2), round(y, 2)] for x, y in pts]


pecas = []
for p in P.PECAS:
    if p['inst']:
        geo = p['geom'](0, 0)   # medidas nominais, como no modelo 3D
        corte = P.cortes(geo)
        pecas.append(dict(nome=p['nome'], grupo=p['grupo'], inst=p['inst'],
                          contorno=_r(P.amostrar(corte[0])), furos=[_r(P.amostrar(g)) for g in corte[1:]],
                          vincos=[[list(g[1]), list(g[2])] for g in P.gravacoes(geo)]))

r = P.analisar()
dados = dict(
    T=P.T, ombro=[P.OMBRO_Y, P.OMBRO_Z], limites=P.LIMITE_OMBRO, janela_oled=P.OLED['janela'],
    pecas=pecas,
    comprados=[dict(nome=c['nome'], grupo=c['grupo'], solidos=c['solidos'], inst=c['inst']) for c in P.COMPRADOS],
    verificacoes=P.verificar(),
    resumo=dict(massa=round(r['massa']), largura=round(2 * (P.CX_BRACO + P.SW / 2)), altura=round(P.H + P.T),
                profundidade=round(P.SD), fs=round(P.SG90['torque_kgcm'] / r['torque'], 1)),
)

with open(os.path.join(AQUI, 'template.html'), encoding='utf-8') as f:
    html = f.read().replace('/*DADOS*/null', json.dumps(dados, ensure_ascii=False, separators=(',', ':')))
with open(os.path.join(AQUI, 'robo_demo.html'), 'w', encoding='utf-8') as f:
    f.write(html)
print('demo/robo_demo.html gerado')
