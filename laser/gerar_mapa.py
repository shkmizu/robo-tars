"""Gera laser/mapa_da_chapa.html: a chapa de corte interativa (mesma distribuição do chapa_1.dxf).
python laser/gerar_mapa.py"""
import json, math, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import exportar_laser as E
P = E.P

# onde cada peça vai e como é presa
INFO = {
    'Base': ('Corpo', 'Fica embaixo do corpo. Os 4 furos largos cobrem as cabeças dos parafusos dos espaçadores do Arduino.', 'Colada sob o fundo do corpo'),
    'Corpo frente': ('Corpo', 'Frente do corpo: janela da tela OLED (bloco direito) e o vinco gravado que separa os dois blocos do meio.', 'Colada'),
    'Corpo trás (tampa)': ('Corpo', 'Tampa de manutenção: janela do USB do Arduino, furo do cabo da fonte e recorte da chave liga/desliga.', '4 parafusos M3 nos reforços'),
    'Corpo lateral': ('Corpo', 'Laterais do corpo: janela e 2 pré-furos do SG90 no eixo; 4 furos do PCA9685 (usados só na lateral esquerda).', 'Coladas'),
    'Corpo topo': ('Corpo', 'Topo do corpo, com o vinco gravado.', 'Colado'),
    'Corpo fundo': ('Corpo', 'Fundo do corpo: 4 furos dos espaçadores do Arduino Uno.', 'Colado'),
    'Mancal disco de encosto': ('Mancal', 'Disco Ø64 colado por fora da lateral do corpo. O braço encosta nele; os parafusos do SG90 entram nele.', 'Colado na lateral do corpo'),
    'Mancal disco do eixo': ('Mancal', 'Disco Ø46 colado sobre o disco de encosto: o furo do braço gira em volta dele. Passar vela.', 'Colado no disco de encosto'),
    'Braço frente/trás': ('Braços', 'Frente e trás dos dois braços. Os 2 rasgos recebem as abas do anteparo do horn.', 'Coladas'),
    'Braço lateral interna': ('Braços', 'Lado do braço voltado para o corpo. O furo Ø46,4 gira em volta do disco do eixo do mancal.', 'Colada'),
    'Braço lateral externa (tampa)': ('Braços', 'Tampa do braço: dá acesso ao parafuso do horn do SG90.', '4 parafusos M3 nos reforços'),
    'Braço topo/fundo': ('Braços', 'Topo e fundo dos dois braços.', 'Colados'),
    'Anteparo do horn': ('Braços', 'Placa dentro do braço onde o horn duplo do SG90 é parafusado (4 × M2). O furo central dá acesso ao parafuso do horn.', 'Encaixada nos rasgos e colada'),
    'Reforço do corpo': ('Reforços', 'Plaquinha colada por dentro da lateral do corpo. O rasgo-T guarda a porca do parafuso da tampa traseira.', 'Colado'),
    'Reforço do braço': ('Reforços', 'Plaquinha colada por dentro do braço. O rasgo-T guarda a porca do parafuso da tampa do braço.', 'Colado'),
}


def _perimetro(g):
    if g[0] == 'circ':
        return 2 * math.pi * g[2]
    if g[0] == 'grav':
        return math.dist(g[1], g[2])
    pts = g[1]
    return sum(math.dist(pts[i - 1], pts[i]) for i in range(len(pts)))


def main():
    larg, alt = P.CHAPA
    itens, tipos = [], []
    for p in P.PECAS:
        if not p['inst']:
            continue
        geo, w, h = E._peca_deitada(p['geom'](P.KERF, P.FOLGA))
        k = len(tipos)
        grupo, desc, fix = INFO[p['nome']]
        tipos.append(dict(nome=p['nome'], qtd=len(p['inst']), w=round(w, 1), h=round(h, 1),
                          grupo=grupo, desc=desc, fix=fix))
        itens += [(k, geo, w, h)] * len(p['inst'])
    pecas = E.distribuir(itens, larg, alt)[0]

    Y = lambda y: alt - y
    svg, corte, grav = [], 0.0, 0.0
    for k, geo in pecas:
        d = []
        for g in P.cortes(geo):
            corte += _perimetro(g)
            if g[0] == 'circ':
                (cx, cy), r = g[1], g[2]
                d.append(f'M{cx - r:.2f} {Y(cy):.2f}a{r:.2f} {r:.2f} 0 1 0 {2 * r:.2f} 0a{r:.2f} {r:.2f} 0 1 0 {-2 * r:.2f} 0Z')
            else:
                d.append('M' + 'L'.join(f'{x:.2f} {Y(y):.2f}' for x, y in g[1]) + 'Z')
        linhas = ''
        for g in P.gravacoes(geo):
            grav += _perimetro(g)
            linhas += f'<line class="gv" x1="{g[1][0]:.2f}" y1="{Y(g[1][1]):.2f}" x2="{g[2][0]:.2f}" y2="{Y(g[2][1]):.2f}"/>'
        x0, y0, x1, y1 = P.caixa(geo[0])
        fs = max(5.0, min(14.0, (y1 - y0) * 0.45, (x1 - x0) * 0.45))
        svg.append(f'<g class="p" data-k="{k}" tabindex="-1"><path d="{"".join(d)}"/>{linhas}'
                   f'<text x="{(x0 + x1) / 2:.1f}" y="{Y((y0 + y1) / 2) + fs * 0.35:.1f}" font-size="{fs:.1f}">{k + 1}</text></g>')

    area = sum(P.area(g[0]) for _, g in pecas)
    resumo = dict(pecas=len(pecas), tipos=len(tipos), uso=round(100 * area / (larg * alt)),
                  corte=round(corte / 1000, 1), grav=round(grav / 1000, 2), larg=larg, alt=alt,
                  T=P.T, kerf=P.KERF)
    with open(os.path.join(AQUI, 'mapa_template.html'), encoding='utf-8') as f:
        html = (f.read().replace('/*SVG*/', '\n'.join(svg))
                .replace('/*TIPOS*/null', json.dumps(tipos, ensure_ascii=False))
                .replace('/*RESUMO*/null', json.dumps(resumo)))
    with open(os.path.join(AQUI, 'mapa_da_chapa.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'mapa_da_chapa.html: {len(pecas)} peças, corte {resumo["corte"]} m, gravação {resumo["grav"]} m')


if __name__ == '__main__':
    main()
