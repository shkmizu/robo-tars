"""
Gera os arquivos de corte a laser a partir de projeto.py:  python laser/exportar_laser.py

  laser/chapa_N.dxf            peças distribuídas na chapa (camada CORTE vermelha, GRAVACAO azul), mm
  laser/00_pente_de_teste.dxf  cortar ANTES, para conferir o kerf
  laser/chapa_N.svg            prévia com o nome de cada peça (só para conferir; não mandar ao laser)
"""
import os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, '..', 'fusion', 'RoboDoisBracos'))
import projeto as P

MARGEM = 10.0   # borda da chapa sem peças (fixação/irregularidade do MDF)
VAO = 4.0       # espaço entre peças


def _girar(geo):
    """Gira 90° (sem espelhar — a face gravada continua para cima)."""
    out = []
    for g in geo:
        if g[0] == 'circ':
            out.append(('circ', (-g[1][1], g[1][0]), g[2]))
        elif g[0] == 'grav':
            out.append(('grav', (-g[1][1], g[1][0]), (-g[2][1], g[2][0])))
        else:
            out.append(('poly', [(-y, x) for x, y in P.amostrar(g)]))
    return out


def _mover(geo, dx, dy):
    out = []
    for g in geo:
        if g[0] == 'circ':
            out.append(('circ', (g[1][0] + dx, g[1][1] + dy), g[2]))
        elif g[0] == 'grav':
            out.append(('grav', (g[1][0] + dx, g[1][1] + dy), (g[2][0] + dx, g[2][1] + dy)))
        else:
            out.append(('poly', [(x + dx, y + dy) for x, y in P.amostrar(g)]))
    return out


def _peca_deitada(geo):
    """Lado maior na horizontal, canto inferior esquerdo em (0, 0)."""
    x0, y0, x1, y1 = P.caixa(geo[0])
    if y1 - y0 > x1 - x0:
        geo = _girar(geo)
        x0, y0, x1, y1 = P.caixa(geo[0])
    return _mover(geo, -x0, -y0), x1 - x0, y1 - y0


def distribuir(itens, larg, alt):
    """Prateleiras (first-fit decreasing height): cada peça vai na primeira prateleira onde cabe.
    ponytail: não é o encaixe ótimo; para este conjunto sobra muito espaço na chapa de 900×600."""
    chapas = []   # cada chapa: lista de prateleiras [y, altura, x_livre, [(nome, geo)]]
    for nome, geo, w, h in sorted(itens, key=lambda i: -i[3]):
        for prateleiras in chapas:
            p = next((p for p in prateleiras if h <= p[1] and p[2] + w <= larg - MARGEM), None)
            if p is None and prateleiras[-1][0] + prateleiras[-1][1] + VAO + h <= alt - MARGEM:
                y = prateleiras[-1][0] + prateleiras[-1][1] + VAO
                p = [y, h, MARGEM, []]
                prateleiras.append(p)
            if p:
                break
        else:
            p = [MARGEM, h, MARGEM, []]
            chapas.append([p])
        p[3].append((nome, _mover(geo, p[2], p[0])))
        p[2] += w + VAO
    return [[peca for prat in ch for peca in prat[3]] for ch in chapas]


def _dxf(pecas, caminho):
    """DXF R12 em mm: polilinhas fechadas e círculos na camada CORTE, linhas na GRAVACAO."""
    L = ['0', 'SECTION', '2', 'HEADER', '9', '$ACADVER', '1', 'AC1009', '9', '$INSUNITS', '70', '4',
         '0', 'ENDSEC', '0', 'SECTION', '2', 'TABLES',
         '0', 'TABLE', '2', 'LTYPE', '70', '1', '0', 'LTYPE', '2', 'CONTINUOUS', '70', '0',
         '3', 'Solid line', '72', '65', '73', '0', '40', '0.0', '0', 'ENDTAB',
         '0', 'TABLE', '2', 'LAYER', '70', '2',
         '0', 'LAYER', '2', 'CORTE', '70', '0', '62', '1', '6', 'CONTINUOUS',
         '0', 'LAYER', '2', 'GRAVACAO', '70', '0', '62', '5', '6', 'CONTINUOUS',
         '0', 'ENDTAB', '0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES']
    f = lambda v: f'{v:.4f}'
    for _, geo in pecas:
        for g in geo:
            if g[0] == 'circ':
                L += ['0', 'CIRCLE', '8', 'CORTE', '62', '1', '10', f(g[1][0]), '20', f(g[1][1]), '30', '0',
                      '40', f(g[2])]
            elif g[0] == 'grav':
                L += ['0', 'LINE', '8', 'GRAVACAO', '62', '5', '10', f(g[1][0]), '20', f(g[1][1]), '30', '0',
                      '11', f(g[2][0]), '21', f(g[2][1]), '31', '0']
            else:
                L += ['0', 'POLYLINE', '8', 'CORTE', '62', '1', '66', '1', '70', '1', '10', '0', '20', '0', '30', '0']
                for x, y in g[1]:
                    L += ['0', 'VERTEX', '8', 'CORTE', '10', f(x), '20', f(y), '30', '0']
                L += ['0', 'SEQEND', '8', 'CORTE']
    L += ['0', 'ENDSEC', '0', 'EOF']
    with open(caminho, 'w', encoding='ascii', newline='\r\n') as arq:
        arq.write('\n'.join(L) + '\n')


def _svg(pecas, larg, alt, caminho):
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 {larg} {alt}">'
           f'<rect width="{larg}" height="{alt}" fill="#f4efe6" stroke="#999"/>']
    Y = lambda y: alt - y
    for nome, geo in pecas:
        for g in geo:
            if g[0] == 'circ':
                out.append(f'<circle cx="{g[1][0]:.2f}" cy="{Y(g[1][1]):.2f}" r="{g[2]:.2f}" fill="none" stroke="#d00" stroke-width="0.3"/>')
            elif g[0] == 'grav':
                out.append(f'<line x1="{g[1][0]:.2f}" y1="{Y(g[1][1]):.2f}" x2="{g[2][0]:.2f}" y2="{Y(g[2][1]):.2f}" stroke="#06c" stroke-width="0.4"/>')
            else:
                pts = ' '.join(f'{x:.2f},{Y(y):.2f}' for x, y in g[1])
                out.append(f'<polygon points="{pts}" fill="none" stroke="#d00" stroke-width="0.3"/>')
        x0, y0, x1, y1 = P.caixa(geo[0])
        out.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{Y((y0 + y1) / 2):.1f}" font-size="{min(6.0, (x1 - x0) / 8):.1f}" '
                   f'text-anchor="middle" font-family="sans-serif" fill="#333">{nome}</text>')
    out.append('</svg>')
    with open(caminho, 'w', encoding='utf-8') as arq:
        arq.write('\n'.join(out))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    falhas = [t for ok, t in P.verificar() if not ok]
    if falhas:
        print('Projeto com verificações em FALHA — corrija antes de cortar:\n  ' + '\n  '.join(falhas))
        raise SystemExit(1)
    larg, alt = P.CHAPA
    itens = []
    for p in P.PECAS:
        if not p['inst']:
            continue
        geo, w, h = _peca_deitada(p['geom'](P.KERF, P.FOLGA))
        rotulo = f"{p['nome']}"
        itens += [(rotulo, geo, w, h)] * len(p['inst'])
    chapas = distribuir(itens, larg, alt)
    for n, pecas in enumerate(chapas, 1):
        _dxf(pecas, os.path.join(AQUI, f'chapa_{n}.dxf'))
        _svg(pecas, larg, alt, os.path.join(AQUI, f'chapa_{n}.svg'))
        area = sum(P.area(g[0]) for _, g in pecas)
        print(f'chapa_{n}.dxf: {len(pecas)} peças, {100 * area / (larg * alt):.0f}% da chapa {larg:g}×{alt:g}')
    # uma peça por arquivo, medida nominal (sem kerf), para modelar no Fusion: Inserir → Inserir DXF
    pasta = os.path.join(AQUI, 'pecas')
    os.makedirs(pasta, exist_ok=True)
    for n, p in enumerate((p for p in P.PECAS if p['inst']), 1):
        nome = P.sem_acento(p['nome']).replace(' ', '_').replace('/', '-').replace('(', '').replace(')', '')
        _dxf([(p['nome'], p['geom'](0, 0))], os.path.join(pasta, f'{n:02d}_{nome}_x{len(p["inst"])}.dxf'))
    print(f'pecas/: {n} DXFs, um por tipo de peça (medida nominal, para o Fusion)')
    pente, _, _ = _peca_deitada(P.g_pente(0, 0))
    _dxf([('Pente de teste', _mover(pente, MARGEM, MARGEM))], os.path.join(AQUI, '00_pente_de_teste.dxf'))
    print(f'00_pente_de_teste.dxf: cortar antes (kerf usado nas peças: {P.KERF} mm, MDF {P.T} mm)')


if __name__ == '__main__':
    main()
