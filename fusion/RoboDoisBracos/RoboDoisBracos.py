"""
RoboDoisBracos.py — script do Fusion 360 que gera o robô a partir de projeto.py.

Cria um documento novo com: componentes nomeados (chapas de MDF + peças compradas),
parâmetros de referência, juntas de revolução com limites nos dois ombros,
varredura de interferência em várias poses, DXFs de corte (e de gravação) e lista de peças em ./saida.

Para mudar uma medida: edite projeto.py e rode o script de novo (gera outro documento).
"""
import adsk.core, adsk.fusion, traceback, os, sys, math, csv, importlib, unicodedata

_PASTA = os.path.dirname(os.path.realpath(__file__))
if _PASTA not in sys.path:
    sys.path.insert(0, _PASTA)
import projeto as P

CM = 0.1                    # a API do Fusion trabalha em cm
VARRER_INTERFERENCIA = True  # ~15 análises; desligue para gerar mais rápido


def _p(x, y, z=0.0):
    return adsk.core.Point3D.create(x * CM, y * CM, z * CM)


def _v(v):
    return adsk.core.Vector3D.create(*v)


def _matriz(inst):
    o, ex, ez = inst
    m = adsk.core.Matrix3D.create()
    m.setWithCoordinateSystem(_p(*o), _v(ex), _v(P.cruz(ez, ex)), _v(ez))
    return m


def _slug(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().replace(' ', '_')


def _ponta(curva, q):
    """Ponto da curva mais próximo de q (arcos do Fusion podem trocar início e fim)."""
    a, b = curva.startSketchPoint, curva.endSketchPoint
    return a if a.geometry.distanceTo(_p(*q)) <= b.geometry.distanceTo(_p(*q)) else b


def _desenhar(sk, geo):
    linhas, arcos = sk.sketchCurves.sketchLines, sk.sketchCurves.sketchArcs
    sk.isComputeDeferred = True
    for prim in geo:
        if prim[0] == 'grav':
            linhas.addByTwoPoints(_p(*prim[1]), _p(*prim[2]))
            continue
        if prim[0] == 'circ':
            sk.sketchCurves.sketchCircles.addByCenterRadius(_p(*prim[1]), prim[2] * CM)
            continue
        segs = P.segmentos(prim)
        inicio = atual = None
        for i, seg in enumerate(segs):   # encadeia pelos pontos do esboço para o perfil fechar
            ini = atual or _p(*seg[1])
            fim = inicio if i == len(segs) - 1 else _p(*seg[-1])
            c = linhas.addByTwoPoints(ini, fim) if seg[0] == 'L' else arcos.addByThreePoints(ini, _p(*seg[2]), fim)
            inicio = inicio or _ponta(c, seg[1])
            atual = _ponta(c, seg[-1])
    sk.isComputeDeferred = False


def _criar_chapa(root, peca):
    insts = peca['inst'] or [((0, -400, 0), P.X_, P.Z_)]   # pente de teste: só para o DXF
    occ = root.occurrences.addNewComponent(_matriz(insts[0]))
    comp = occ.component
    comp.name = peca['nome']
    sk = comp.sketches.add(comp.xYConstructionPlane)
    sk.name = 'Perfil'
    _desenhar(sk, P.cortes(peca['geom'](0.0, 0.0)))
    perfis = [sk.profiles.item(i) for i in range(sk.profiles.count)]
    perfil = max(perfis, key=lambda pr: pr.areaProperties().area)   # a chapa (contorno menos furos)
    ext = comp.features.extrudeFeatures.addSimple(perfil, adsk.core.ValueInput.createByReal(P.T * CM),
                                                  adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext.bodies.item(0).name = peca['nome']
    geo = peca['geom'](P.KERF, P.FOLGA)
    for nome, prims in (('Corte laser', P.cortes(geo)), ('Gravação laser', P.gravacoes(geo))):
        if prims:   # "Corte laser" tem kerf/folga compensados — é ele que vai para o DXF
            s = comp.sketches.add(comp.xYConstructionPlane)
            s.name = nome
            _desenhar(s, prims)
            s.isVisible = False
    if not peca['inst']:
        occ.isLightBulbOn = False
        return comp, []
    return comp, [occ] + [root.occurrences.addExistingComponent(comp, _matriz(i)) for i in insts[1:]]


def _criar_comprado(root, c):
    occ = root.occurrences.addNewComponent(_matriz(c['inst'][0]))
    comp = occ.component
    comp.name = c['nome']
    tbm = adsk.fusion.TemporaryBRepManager.get()
    base = comp.features.baseFeatures.add()
    base.startEdit()
    for s in c['solidos']:
        if s[0] == 'caixa':
            (lx, ly, lz) = s[2]
            caixa = adsk.core.OrientedBoundingBox3D.create(_p(*s[1]), _v(P.X_), _v(P.Y_), lx * CM, ly * CM, lz * CM)
            corpo = tbm.createBox(caixa)
        else:
            corpo = tbm.createCylinderOrCone(_p(*s[1]), s[3] * CM, _p(*s[2]), s[3] * CM)
        comp.bRepBodies.add(corpo, base)
    base.finishEdit()
    return [occ] + [root.occurrences.addExistingComponent(comp, _matriz(i)) for i in c['inst'][1:]]


def _aresta_circular(occ, raio_mm):
    for b in range(occ.bRepBodies.count):
        arestas = occ.bRepBodies.item(b).edges
        for i in range(arestas.count):
            circ = adsk.core.Circle3D.cast(arestas.item(i).geometry)
            if circ and abs(circ.radius - raio_mm * CM) < 1e-4:
                return arestas.item(i)
    raise RuntimeError(f'Furo de referência Ø{2 * raio_mm:g} não encontrado em {occ.name}')


def _centro_y(occ):
    bb = occ.boundingBox
    return (bb.minPoint.y + bb.maxPoint.y) / 2


def _junta(root, nome, movel, fixo, raio_mm, limites, teste):
    """Junta de revolução no furo central de `movel`. Descobre o sentido do eixo girando 90°
    e vendo se `teste` foi para a frente (−Y); assim os limites ficam na convenção de projeto.py."""
    geo = adsk.fusion.JointGeometry.createByCurve(_aresta_circular(movel, raio_mm),
                                                  adsk.fusion.JointKeyPointTypes.CenterKeyPoint)
    inp = root.asBuiltJoints.createInput(movel, fixo, geo)
    inp.setAsRevoluteJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
    j = root.asBuiltJoints.add(inp)
    j.name = nome
    mov = adsk.fusion.RevoluteJointMotion.cast(j.jointMotion)
    y0 = _centro_y(teste)
    mov.rotationValue = math.radians(90)
    adsk.doEvents()
    sinal = 1 if _centro_y(teste) < y0 else -1
    mov.rotationValue = 0
    a, b = sorted(sinal * math.radians(v) for v in limites)
    lim = mov.rotationLimits
    lim.isMinimumValueEnabled, lim.minimumValue = True, a
    lim.isMaximumValueEnabled, lim.maximumValue = True, b
    return mov, sinal


POSES_VARREDURA = [(a, a) for a in (-90, -45, 0, 45, 90)] + [(45, -45), (90, -90)]   # (D, E)


def _varrer(design, occs, juntas):
    coll = adsk.core.ObjectCollection.create()
    for o in occs:
        coll.add(o)
    falhas = []
    for pose in POSES_VARREDURA:
        for (mov, sinal), ang in zip(juntas, pose):
            mov.rotationValue = sinal * math.radians(ang)
        adsk.doEvents()
        res = design.analyzeInterference(design.createInterferenceInput(coll))
        if res.count:
            nome = lambda corpo: corpo.assemblyContext.name if corpo.assemblyContext else corpo.name
            pares = sorted({f'{nome(res.item(i).entityOne)} × {nome(res.item(i).entityTwo)}'
                            for i in range(res.count)})
            falhas.append(f'ombro D {pose[0]}°, ombro E {pose[1]}°: ' + '; '.join(pares))
    for mov, _ in juntas:
        mov.rotationValue = 0
    return falhas


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        importlib.reload(P)   # pega as edições de projeto.py sem reiniciar o Fusion
        verificacoes = P.verificar()

        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        design.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        root = design.rootComponent

        for nome, valor in [('espessura_mdf', P.T), ('kerf', P.KERF), ('folga_encaixe', P.FOLGA),
                            ('largura_bloco', P.SW), ('profundidade_bloco', P.SD), ('altura_corpo', P.H),
                            ('altura_eixo_ombro', P.OMBRO_Z), ('comprimento_dente', P.DEDO)]:
            design.userParameters.add(nome, adsk.core.ValueInput.createByString(f'{valor} mm'), 'mm',
                                      'Referência: altere em projeto.py e rode o script de novo')

        saida = os.path.join(_PASTA, 'saida')
        os.makedirs(saida, exist_ok=True)
        pecas = []   # (nome, grupo, lado, ocorrência)
        lado = lambda inst: 'D' if inst[0][0] > 0 else 'E'
        for n, p in enumerate(P.PECAS, 1):
            comp, occs = _criar_chapa(root, p)
            base = os.path.join(saida, f'{n:02d}_{_slug(p["nome"])}_x{max(1, len(p["inst"]))}')
            comp.sketches.itemByName('Corte laser').saveAsDXF(base + '.dxf')
            grav = comp.sketches.itemByName('Gravação laser')
            if grav:
                grav.saveAsDXF(base + '_gravar.dxf')
            pecas += [(p['nome'], p['grupo'], lado(i), o) for i, o in zip(p['inst'], occs)]
        for c in P.COMPRADOS:
            pecas += [(c['nome'], c['grupo'], lado(i), o) for i, o in zip(c['inst'], _criar_comprado(root, c))]

        for _, grupo, _, o in pecas:
            o.isGrounded = grupo == 'tronco'
        juntas = []   # cada braço (todas as suas chapas + horn) gira como um bloco só
        for ld in 'DE':
            coll = adsk.core.ObjectCollection.create()
            for _, g, l, o in pecas:
                if g == 'braco' and l == ld:
                    coll.add(o)
            root.rigidGroups.add(coll, False)
            achar = lambda nome: next(o for n_, _, l, o in pecas if n_ == nome and l == ld)
            juntas.append(_junta(root, f'Ombro {ld}', achar('Anteparo do horn'), achar('Servo SG90'),
                                 P.FURO_OMBRO / 2, P.LIMITE_OMBRO, achar('Braço lateral externa (tampa)')))

        falhas = _varrer(design, [o for *_, o in pecas], juntas) if VARRER_INTERFERENCIA else None

        with open(os.path.join(saida, 'lista_de_pecas.csv'), 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f, delimiter=';')
            w.writerow(['Categoria', 'Item', 'Qtd', 'Observação'])
            w.writerows(P.lista_materiais())
        if falhas is None:
            interf = 'Varredura de interferência desligada.'
        elif falhas:
            interf = 'INTERFERÊNCIAS:\n' + '\n'.join(falhas)
        else:
            interf = (f'Varredura de interferência: 0 colisões em {len(POSES_VARREDURA)} poses '
                      '(braços juntos de −90° a 90° e alternados).')
        texto = P.relatorio() + '\n\n' + interf
        with open(os.path.join(saida, 'relatorio.txt'), 'w', encoding='utf-8') as f:
            f.write(texto)
        ui.messageBox(texto + f'\n\nDXFs, lista de peças e relatório em:\n{saida}', 'Robô TARS')
    except Exception:
        if ui:
            ui.messageBox('Falha:\n{}'.format(traceback.format_exc()))
