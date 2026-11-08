"""
totem.py — o TARS como totem de atendimento do BairroVivo (GS CitizenTech).

O sensor ultrassônico (HC-SR04) diz ao robô o que está na frente dele; o Arduino classifica com o
modelo de presenca.py e manda eventos pelo USB. Este programa decide o que fazer com eles:

  ninguém na frente   espera, com o microfone DESLIGADO (só ouve quando há alguém: privacidade)
  alguém chegando     cumprimenta por voz, com uma fala gerada pela IA a partir do contexto
                      (hora, distância, quantos atendimentos hoje)
  pessoa na frente    conversa: registra um problema do bairro (poste apagado, buraco, lixo,
                      calçada, mobiliário) ou consulta um protocolo, pela API do BairroVivo
  silêncio            oferece ajuda (15 s) e depois se despede (40 s)
  pessoa foi embora   encerra o atendimento e volta a esperar
  objeto parado       registra sozinho uma possível obstrução da calçada (categoria Calçada /
                      acessibilidade), marcada para revisão de um operador
  sensor com falha    avisa e passa a atender quando alguém fala (sem depender do sensor)

Uso: python tars.py --totem --porta auto --baud 115200   (ou 6_totem_bairrovivo.bat)
Sem o robô, digitando: python tars.py --totem --sem-robo --teclado
  e simule o sensor com /chegou, /saiu, /obstaculo, /falha, /passou.
"""
import json, queue, re, threading, time

import bairrovivo
from tars import (ACOES, MODELO, decidir, interpretar, microfone, microfone_offline, perguntar_llm,
                  sem_acento, voz)

SILENCIO_OFERECE_S = 15
SILENCIO_DESPEDE_S = 40
SAIU_APOS_S = 2.5            # vazio/saindo por este tempo = a pessoa foi embora
CHEGANDO_CONFIRMA_S = 1.0    # "chegando" por 1 s (ou "presente") = vem ao totem, não só passando
OBSTACULO_INTERVALO_S = 1800  # no máximo um registro de obstrução a cada 30 min
OUVIR_S = 6

PRIORIDADE_SUGERIDA = {      # plano do BairroVivo, seção 3.2 (o operador pode mudar)
    'Buraco / pavimento': 'Alta', 'Iluminação': 'Média', 'Descarte irregular': 'Média',
    'Calçada / acessibilidade': 'Alta', 'Mobiliário urbano': 'Baixa',
}
PALAVRAS_CATEGORIA = {       # sem acento, minúsculas: garantem a categoria mesmo se a IA errar
    'Iluminação': ('poste', 'luz', 'lampada', 'iluminacao', 'escuro', 'apagad'),
    'Buraco / pavimento': ('buraco', 'asfalto', 'pavimento', 'cratera', 'remendo'),
    'Descarte irregular': ('lixo', 'entulho', 'descarte', 'sujeira', 'sofa velho', 'pneu'),
    'Calçada / acessibilidade': ('calcada', 'rampa', 'cadeirante', 'acessib', 'obstru', 'passagem bloqueada'),
    'Mobiliário urbano': ('banco', 'placa', 'ponto de onibus', 'abrigo', 'lixeira', 'brinquedo', 'semaforo'),
}
SIM = ('sim', 'pode', 'confirm', 'isso', 'correto', 'envia', 'manda', 'claro', 'ok', 'beleza', 'certo')
NAO = ('nao', 'cancela', 'errado', 'espera', 'corrig', 'deixa')
TCHAU = ('tchau', 'ate logo', 'ate mais', 'so isso', 'era isso', 'obrigad', 'valeu', 'falou')

SISTEMA_SAUDACAO = """Você é o TARS, o robô do filme Interestelar, agora atendente de um totem do BairroVivo,
uma plataforma de zeladoria do bairro. O sensor acabou de perceber alguém se aproximando.
Você recebe um JSON com o contexto (período do dia, distância, atendimentos de hoje).
Cumprimente de acordo com o período, diga que pode registrar um problema do bairro (poste apagado,
buraco, lixo, calçada quebrada, banco ou placa danificada) ou consultar um protocolo.
Seja simpático, com uma pitada de humor seco, em português do Brasil, em no máximo 2 frases curtas.
Responda SOMENTE com JSON: {"fala": "...", "acao": "saudar"}"""

SISTEMA_PEDIDO = """Você é o TARS, atendente de um totem do BairroVivo (zeladoria do bairro).
Analise o que o cidadão disse e responda SOMENTE com JSON:
{"intencao": "registrar" | "consultar" | "conversar" | "encerrar",
 "categoria": uma de [CATEGORIAS] ou "",
 "titulo": "título curto do problema (até 8 palavras)" ou "",
 "descricao": "descrição objetiva do problema, sem inventar nada" ou "",
 "local": "rua, número ou ponto de referência que o cidadão disse" ou "",
 "protocolo": "números do protocolo, se ele disse" ou "",
 "fala": "sua resposta curta em português do Brasil",
 "acao": um de [ACOES]}
Regras: registrar = relata um problema do bairro; consultar = quer saber do andamento de um protocolo;
encerrar = se despede ou agradece; conversar = qualquer outra coisa (responda e lembre o que você faz).
Nunca invente endereço, protocolo ou prazo. Nunca prometa que a prefeitura vai resolver.
Não peça nome, telefone, CPF nem e-mail.""".replace(
    '[CATEGORIAS]', json.dumps(bairrovivo.CATEGORIAS, ensure_ascii=False)).replace(
    '[ACOES]', json.dumps(ACOES))


def _norm(texto):
    return ' ' + ' '.join(''.join(c if c.isalnum() else ' ' for c in sem_acento(texto).lower()).split()) + ' '


def categoria_por_palavra(texto):
    t = _norm(texto)
    for cat, palavras in PALAVRAS_CATEGORIA.items():
        if any(p in t for p in palavras):
            return cat
    return ''


def tem(texto, palavras):
    t = _norm(texto)
    return any(f' {p}' in t for p in palavras)


LOGRADOUROS = r'(rua|r\.|avenida|av\.?|travessa|alameda|estrada|rodovia|praça|praca|largo|viela|esquina|em frente)'


def local_por_texto(texto):
    """'tem um buraco na Rua das Flores 120' → 'Rua das Flores 120' (reserva se a IA não extrair)."""
    m = re.search(r'\b' + LOGRADOUROS + r'\b.*', texto, re.I)
    return m.group(0).strip(' .,;!?') if m else ''


def periodo(hora):
    return 'manhã' if 5 <= hora < 12 else 'tarde' if 12 <= hora < 18 else 'noite'


def _json_llm(resposta):
    try:
        return json.loads(resposta[resposta.index('{'):resposta.rindex('}') + 1])
    except (ValueError, AttributeError):
        return {}


def falar_protocolo(protocolo):
    """BV-0007 → "B V, número 7": o sintetizador lê melhor."""
    letras = ' '.join(re.sub(r'[^A-Za-z]', '', protocolo).upper())
    numero = re.sub(r'\D', '', protocolo).lstrip('0') or '0'
    return f'{letras}, número {numero}' if letras else numero


class Totem:
    def __init__(self, robo, ponte, preparar, ouvir, modelo=MODELO, sem_sensor=False, relogio=time.time,
                 formato_protocolo='BV-{:04d}', log=print):
        self.robo, self.ponte, self.preparar, self.ouvir = robo, ponte, preparar, ouvir
        self.modelo, self.relogio, self.log = modelo, relogio, log
        self.formato_protocolo = formato_protocolo
        self.sem_sensor = sem_sensor
        self.sensor = 'falha' if sem_sensor else 'vazio'
        self.sensor_desde = relogio()
        self.distancia = 0
        self.fase = 'espera'      # espera | conversa | pedindo_local | confirmando | pedindo_protocolo | aguardando_saida
        self.rascunho = None
        self.silencio_desde = None
        self.ofereceu = False
        self.atendimentos = 0
        self.ultimo_obstaculo = -1e9
        self.historico = []

    # ── saída: voz + tela + gesto juntos ─────────────────────────────────────────
    def falar(self, fala, acao='repouso', tela=None):
        self.log(f'TARS: {fala}  [{acao}]')
        tocar = self.preparar(fala)
        self.robo.texto(tela or fala)
        self.robo.acao(acao if acao in ACOES else 'repouso')
        tocar()

    # ── eventos do sensor ────────────────────────────────────────────────────────
    def processar_eventos(self):
        while True:
            try:
                ev = self.robo.eventos.get_nowait()
            except queue.Empty:
                return
            self.tratar_evento(ev)

    def tratar_evento(self, ev):
        tipo = ev.get('ev')
        if tipo in ('estado', 'leitura'):
            self.ponte.enviar_evento_sensor(ev)
        if tipo == 'estado':
            novo = ev.get('estado', 'vazio')
            self.distancia = ev.get('d', 0)
            if novo != self.sensor:
                self.log(f'[sensor] {novo} ({self.distancia} cm, confiança {ev.get("conf", "?")}%)')
                anterior, self.sensor, self.sensor_desde = self.sensor, novo, self.relogio()
                if novo == 'falha':
                    self.robo.texto('SENSOR COM FALHA: FALE COMIGO')
                    self.log('[sensor] sem o HC-SR04: o totem passa a atender quando alguém fala')
                elif anterior == 'falha':
                    self.log('[sensor] voltou a funcionar')
                if novo == 'obstaculo':
                    self.registrar_obstaculo()
        elif tipo == 'autonomo':
            self.log('[robô] ficou sem notícias do computador e entrou no modo autônomo; retomando')
            self.robo.modo_autonomo(False)
        elif tipo == 'desconectado':
            self.log('[robô] cabo desconectado: sigo atendendo só por voz')
            self.sensor = 'falha'

    def sem_sensor_agora(self):
        return self.sem_sensor or self.sensor == 'falha'

    def pessoa_saiu(self):
        if self.sem_sensor_agora():
            return False
        return self.sensor in ('vazio', 'saindo') and self.relogio() - self.sensor_desde >= SAIU_APOS_S

    # ── laço principal ───────────────────────────────────────────────────────────
    def passo(self):
        """Uma volta do laço. Separado de rodar() para os testes."""
        self.processar_eventos()
        if self.fase == 'espera':
            if self.sem_sensor_agora():
                texto = self.ouvir(OUVIR_S)
                self.processar_eventos()
                if texto:
                    self.iniciar_atendimento(cumprimentar=False)
                    self.responder(texto)
            elif self.sensor == 'presente' or (self.sensor == 'chegando' and
                                               self.relogio() - self.sensor_desde >= CHEGANDO_CONFIRMA_S):
                self.iniciar_atendimento()   # quem só passa na calçada não é cumprimentado
            else:
                time.sleep(0.1)
            return
        if self.fase == 'aguardando_saida':
            if self.pessoa_saiu() or self.sem_sensor_agora():
                self.esperar_proximo()
            else:
                time.sleep(0.1)
            return
        if self.pessoa_saiu():
            self.encerrar(saiu=True)
            return
        texto = self.ouvir(OUVIR_S)
        self.processar_eventos()
        if texto:
            self.log(f'ouvi: {texto}')
            self.silencio_desde, self.ofereceu = self.relogio(), False
            self.responder(texto)
            return
        if self.pessoa_saiu():
            self.encerrar(saiu=True)
            return
        calado = self.relogio() - self.silencio_desde
        if calado >= SILENCIO_DESPEDE_S:
            self.encerrar(saiu=False)
        elif calado >= SILENCIO_OFERECE_S and not self.ofereceu:
            self.ofereceu = True
            self.falar('Posso ajudar? Você pode registrar um problema do bairro, como poste apagado ou '
                       'buraco, ou consultar um protocolo.', 'pensar', 'POSSO AJUDAR?')

    def rodar(self):
        self.robo.modo_autonomo(False)
        self.esperar_proximo()
        while True:
            self.passo()

    # ── atendimento ──────────────────────────────────────────────────────────────
    def esperar_proximo(self):
        self.fase, self.rascunho = 'espera', None
        self.robo.texto('BAIRROVIVO: CHEGUE PERTO' if not self.sem_sensor_agora() else 'BAIRROVIVO: FALE COMIGO')

    def iniciar_atendimento(self, cumprimentar=True):
        self.atendimentos += 1
        self.fase, self.rascunho, self.ofereceu = 'conversa', None, False
        self.silencio_desde = self.relogio()
        self.historico = []
        self.log(f'— atendimento {self.atendimentos} —')
        if cumprimentar:
            fala, acao = self.saudacao()
            self.falar(fala, acao, 'BAIRROVIVO: POSSO AJUDAR?')

    def saudacao(self):
        hora = time.localtime(self.relogio()).tm_hour
        contexto = {'evento': self.sensor, 'distancia_cm': self.distancia, 'periodo': periodo(hora),
                    'atendimentos_hoje': self.atendimentos}
        reserva = {'manhã': 'Bom dia', 'tarde': 'Boa tarde', 'noite': 'Boa noite'}[periodo(hora)]
        try:
            r = perguntar_llm([{'role': 'user', 'content': json.dumps(contexto, ensure_ascii=False)}],
                              self.modelo, sistema=SISTEMA_SAUDACAO, timeout=20)
            fala, _ = interpretar(r)
            if fala and fala != '...':
                return fala, 'saudar'
        except OSError as erro:
            self.log(f'(IA indisponível na saudação: {erro})')
        return (f'{reserva}! Sou o TARS, do BairroVivo. Posso registrar um problema do bairro '
                f'ou consultar um protocolo.'), 'saudar'

    def entender(self, texto):
        """IA + palavras-chave → dict com intencao, categoria, titulo, descricao, local, protocolo, fala, acao."""
        d = {}
        try:
            d = _json_llm(perguntar_llm(self.historico + [{'role': 'user', 'content': texto}], self.modelo,
                                        sistema=SISTEMA_PEDIDO, timeout=30))
        except OSError as erro:
            self.log(f'(IA indisponível: {erro}; usando palavras-chave)')
        d = {k: str(d.get(k, '') or '').strip() for k in
             ('intencao', 'categoria', 'titulo', 'descricao', 'local', 'protocolo', 'fala', 'acao')}
        cat_palavra = categoria_por_palavra(texto)
        if d['categoria'] not in bairrovivo.CATEGORIAS:
            d['categoria'] = cat_palavra
        numeros = re.findall(r'\d+', texto)
        # palavras-chave têm prioridade nas decisões que mudam o que acontece
        if tem(texto, ('protocolo', 'andamento', 'status', 'consultar', 'acompanhar')):
            d['intencao'] = 'consultar'
            d['protocolo'] = numeros[-1] if numeros else re.sub(r'\D', '', d['protocolo'])
        elif tem(texto, TCHAU) and len(_norm(texto).split()) <= 6:
            d['intencao'] = 'encerrar'
        elif cat_palavra or tem(texto, ('registrar', 'reclamar', 'denunciar', 'problema')):
            d['intencao'] = 'registrar'
        elif d['intencao'] not in ('registrar', 'consultar', 'conversar', 'encerrar'):
            d['intencao'] = 'conversar'
        if d['intencao'] == 'registrar':
            d['local'] = d['local'] or local_por_texto(texto)
            curto = ' '.join(texto.split()[:8])
            d['titulo'] = d['titulo'] or (curto[:1].upper() + curto[1:])
            d['descricao'] = d['descricao'] or texto
        return d

    def responder(self, texto):
        self.historico = (self.historico + [{'role': 'user', 'content': texto}])[-8:]
        if self.fase == 'confirmando':
            return self.confirmar(texto)
        if self.fase == 'pedindo_local':
            self.rascunho['local_texto'] = texto.strip()
            return self.pedir_confirmacao()
        if self.fase == 'pedindo_protocolo':
            numeros = re.findall(r'\d+', texto)
            self.fase = 'conversa'
            if not numeros:
                return self.falar('Não entendi o número. Pode repetir só os números do protocolo?', 'duvida')
            return self.consultar(numeros[-1])
        d = self.entender(texto)
        self.log(f'[IA] intenção {d["intencao"]}, categoria "{d["categoria"]}"')
        if d['intencao'] == 'encerrar':
            return self.encerrar(saiu=False)
        if d['intencao'] == 'consultar':
            if not d['protocolo']:
                self.fase = 'pedindo_protocolo'
                return self.falar('Claro. Qual é o número do protocolo?', 'pensar', 'NUMERO DO PROTOCOLO?')
            return self.consultar(d['protocolo'])
        if d['intencao'] == 'registrar':
            if not d['categoria']:
                return self.falar('Entendi que é um problema do bairro. É de iluminação, buraco, lixo, '
                                  'calçada ou algo quebrado, como banco ou placa?', 'duvida')
            self.rascunho = {'titulo': d['titulo'], 'descricao': d['descricao'], 'categoria': d['categoria'],
                             'local_texto': d['local'], 'origem': 'totem_voz',
                             'prioridade_sugerida': PRIORIDADE_SUGERIDA[d['categoria']],
                             'texto_original': texto[:300]}
            if not d['local']:
                self.fase = 'pedindo_local'
                return self.falar('Onde fica? Diga a rua, o número ou um ponto de referência.', 'pensar', 'ONDE FICA?')
            return self.pedir_confirmacao()
        fala = d['fala']
        acao = d['acao'] if d['acao'] in ACOES else 'repouso'
        if not fala:
            try:
                fala, acao = decidir(texto, self.historico[:-1], self.modelo)
            except OSError:
                fala, acao = 'Posso registrar um problema do bairro ou consultar um protocolo.', 'repouso'
        self.falar(fala, acao)

    def pedir_confirmacao(self):
        r = self.rascunho
        self.fase = 'confirmando'
        self.falar(f'Vou registrar: {r["categoria"]}, {r["titulo"]}, em {r["local_texto"]}. Posso enviar?',
                   'pensar', f'{r["categoria"]}: CONFIRMA?')

    def confirmar(self, texto):
        if tem(texto, NAO):
            self.fase, self.rascunho = 'conversa', None
            return self.falar('Tudo bem, não registrei. Pode me contar de novo, do jeito certo.', 'sim')
        if not tem(texto, SIM):
            return self.falar('Só para confirmar: posso enviar? Responda sim ou não.', 'duvida')
        self.fase = 'conversa'
        try:
            protocolo, _ = self.ponte.registrar_ocorrencia(self.rascunho)
        except bairrovivo.ErroAPI as erro:
            self.log(f'[BairroVivo] {erro}')
            return self.falar('O BairroVivo recusou o registro agora. Tente pelo aplicativo, por favor.', 'triste')
        finally:
            self.rascunho = None
        if protocolo:
            return self.falar(f'Registrado! Protocolo {falar_protocolo(protocolo)}. Um operador vai revisar. '
                              f'Quer registrar mais alguma coisa?', 'feliz', f'PROTOCOLO {protocolo}')
        self.falar('Estou sem conexão com o BairroVivo agora. Guardei o seu relato e envio assim que a '
                   'conexão voltar.', 'sim', 'GUARDADO: ENVIO DEPOIS')

    def consultar(self, numero):
        protocolo = self.formato_protocolo.format(int(numero)) if str(numero).isdigit() else str(numero)
        try:
            oc = self.ponte.consultar(protocolo)
        except OSError:
            return self.falar('Não consegui falar com o BairroVivo agora. Tente de novo em alguns minutos.', 'triste')
        if not oc:
            return self.falar(f'Não encontrei o protocolo {falar_protocolo(protocolo)}. Confira o número.', 'duvida')
        self.falar(f'O protocolo {falar_protocolo(protocolo)}, {oc.get("titulo", "")}, está: {oc.get("status")}.',
                   'sim', f'{protocolo}: {oc.get("status", "")}')

    def encerrar(self, saiu):
        if saiu:
            self.log('[sensor] a pessoa foi embora')
            self.falar('Até logo!', 'saudar', 'ATE LOGO!')
            self.esperar_proximo()
        else:
            self.falar('Obrigado! Se precisar, é só chegar perto de novo.', 'saudar', 'ATE LOGO!')
            self.fase = 'aguardando_saida'

    def registrar_obstaculo(self):
        agora = self.relogio()
        if self.fase != 'espera' or agora - self.ultimo_obstaculo < OBSTACULO_INTERVALO_S:
            return
        self.ultimo_obstaculo = agora
        rascunho = {'titulo': 'Possível obstrução em frente ao totem', 'categoria': 'Calçada / acessibilidade',
                    'descricao': f'O sensor ultrassônico do totem detectou um objeto parado a {self.distancia} cm '
                                 f'por mais de 20 s, bloqueando a passagem. Sugestão automática: conferir no local.',
                    'local_texto': self.ponte.cfg['local']['descricao'], 'origem': 'sensor_fisico',
                    'prioridade_sugerida': 'Alta'}
        try:
            protocolo, _ = self.ponte.registrar_ocorrencia(rascunho)
        except bairrovivo.ErroAPI as erro:
            self.log(f'[BairroVivo] {erro}')
            protocolo = None
        self.log(f'[BairroVivo] obstrução registrada para revisão: {protocolo or "na fila"}')
        self.falar('Atenção: tem algo bloqueando a passagem na frente do totem. Avisei a zeladoria.',
                   'duvida', 'PASSAGEM OBSTRUIDA: AVISEI')


def ouvir_teclado(robo):
    """Digitar em vez de falar. Linhas com / simulam o sensor: /chegou /saiu /obstaculo /falha /passou."""
    linhas = queue.Queue()
    SIMULA = {'/chegou': [('chegando', 120), ('presente', 60)], '/saiu': [('saindo', 120), ('vazio', 0)],
              '/obstaculo': [('obstaculo', 45)], '/falha': [('falha', 0)], '/passou': [('chegando', 140), ('vazio', 0)],
              '/vazio': [('vazio', 0)]}

    def ler():
        while True:
            try:
                linha = input().strip()
            except EOFError:
                return
            if linha in SIMULA:
                for estado, d in SIMULA[linha]:
                    robo.eventos.put({'ev': 'estado', 'estado': estado, 'd': d, 'conf': 99, 'simulado': True})
            elif linha:
                linhas.put(linha)

    threading.Thread(target=ler, daemon=True).start()

    def ouvir(timeout=None):
        try:
            return linhas.get(timeout=timeout)
        except queue.Empty:
            return ''
    return ouvir


def rodar(robo, a):
    ponte = bairrovivo.Ponte()
    if a.teclado:
        print('Totem no modo digitado. Simule o sensor com: /chegou /saiu /obstaculo /falha /passou')
        ouvir = ouvir_teclado(robo)
    else:
        ouvir = microfone_offline(a.vosk) if a.vosk else microfone()
    preparar = (lambda texto: lambda: None) if a.mudo else voz(a.voz_offline)
    print('Carregando a IA (a primeira vez demora)...')
    try:
        perguntar_llm([{'role': 'user', 'content': 'Oi'}], a.modelo, timeout=180)
    except OSError as erro:
        print(f'Ollama não respondeu ({erro}): o totem segue com respostas prontas e palavras-chave.')
    print(f'API do BairroVivo: {ponte.cfg["url"]} ({"no ar" if ponte.saude() else "fora do ar: guardando na fila"})')
    print('Totem pronto. Ctrl+C para sair.')
    Totem(robo, ponte, preparar, ouvir, a.modelo, sem_sensor=a.sem_sensor).rodar()
