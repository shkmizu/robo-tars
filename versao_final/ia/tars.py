"""
tars.py — o "cérebro" do robô TARS: ouve, pensa (LLM local no Ollama), fala e mexe o robô.
Versão final: use com versao_final/arduino/tars_ia. Ao começar, desliga a coreografia do robô
(comando "m 0") para os braços não fazerem barulho perto do microfone; ao sair, religa ("m 1").

Uso:
  python tars.py --porta COM5 --diagnostico   confere tudo antes de apresentar
  python tars.py --porta COM5                 robô pelo Bluetooth (a porta "de saída" do HC-05)
  python tars.py --porta COM5 --vosk modelo   reconhecimento de voz offline (sem internet)
  python tars.py --porta COM5 --teclado       digitando em vez de usar o microfone (o TARS ainda fala)
  python tars.py --sem-robo --teclado         sem robô: mostra os comandos que seriam enviados
  python tars.py --teste                      autoteste (não precisa de microfone, Ollama nem robô)

Para usar dentro do script do CP4:
  from tars import Robo, decidir
  robo, historico = Robo('COM5'), []
  fala, acao = decidir(texto_reconhecido, historico)
  robo.texto(fala); robo.acao(acao)        # depois o script do CP4 fala `fala` como já faz
"""
import argparse, json, time, unicodedata, urllib.request

MODELO = 'llama3.2:3b'      # troque pelo modelo que vocês usam (veja com: ollama list)
OLLAMA = 'http://localhost:11434/api/chat'
ACOES = ('saudar', 'dancar', 'feliz', 'triste', 'sim', 'nao', 'pensar', 'repouso')

# Personalidade do TARS — ajustem do jeito do grupo (é o que mais muda a "cara" do robô).
# A última parte (o formato JSON e a lista de ações) precisa continuar igual.
PERSONALIDADE = """Você é o TARS, o robô do filme Interestelar, numa versão de mesa feita por estudantes.
Seu nível de humor é 75% e o de honestidade é 90%: responda com respostas secas, sinceras e um pouco irônicas.
Fale em português do Brasil, em no máximo 2 frases curtas.
Responda SOMENTE com um JSON assim: {"fala": "o que você diz", "acao": "uma ação"}.
Ações possíveis: saudar (cumprimentos e despedidas), dancar (quando pedirem dança ou música),
sim (concordar), nao (discordar ou recusar), feliz (elogios, boas notícias), triste (notícias ruins),
repouso (todo o resto)."""

# Palavras que disparam a ação na hora, sem depender da LLM: garantem o comportamento na
# apresentação (ex.: "Oi, TARS" sempre acena). Sem acento e em minúsculas.
PALAVRAS = {
    'saudar': ('oi', 'ola', 'bom dia', 'boa tarde', 'boa noite', 'tchau', 'ate logo', 'acene', 'acena'),
    'dancar': ('danca', 'dance', 'dancar', 'dancinha'),
    'feliz': ('parabens', 'muito bem', 'mandou bem'),
}


def sem_acento(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()


def acao_por_palavra(texto):
    t = ' ' + ' '.join(''.join(c if c.isalnum() else ' ' for c in sem_acento(texto).lower()).split()) + ' '
    for acao, palavras in PALAVRAS.items():
        if any(f' {p} ' in t for p in palavras):
            return acao
    return None


def interpretar(resposta):
    """Resposta da LLM → (fala, ação). Aceita JSON com texto em volta, texto solto e ação inválida."""
    try:
        dados = json.loads(resposta[resposta.index('{'):resposta.rindex('}') + 1])
        fala, acao = str(dados.get('fala', '')).strip(), str(dados.get('acao', '')).strip().lower()
    except (ValueError, AttributeError):
        fala, acao = resposta.strip(), ''
    acao = sem_acento(acao)
    return fala or '...', acao if acao in ACOES else 'repouso'


def perguntar_llm(historico, modelo=MODELO):
    corpo = json.dumps({'model': modelo, 'stream': False, 'format': 'json', 'keep_alive': '60m',  # não descarrega
                        'messages': [{'role': 'system', 'content': PERSONALIDADE}] + historico[-10:]}).encode()
    req = urllib.request.Request(OLLAMA, corpo, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())['message']['content']


def decidir(ouvido, historico, modelo=MODELO):
    """O que o TARS diz e faz. Palavras-chave têm prioridade sobre a ação escolhida pela LLM."""
    historico.append({'role': 'user', 'content': ouvido})
    resposta = perguntar_llm(historico, modelo)
    historico.append({'role': 'assistant', 'content': resposta})
    fala, acao = interpretar(resposta)
    return fala, acao_por_palavra(ouvido) or acao


# Nomes com que o Uno (e os clones com chip CH340) aparece na lista de portas.
NOMES_ARDUINO = ('arduino', 'ch340', 'ch34', 'usb-serial', 'usb serial', 'wchusbserial', 'usbserial', 'usbmodem')


def encontrar_porta():
    """Acha a porta do Uno ligado pelo cabo USB (para usar --porta auto)."""
    from serial.tools import list_ports  # pip install pyserial
    portas = list(list_ports.comports())
    for p in portas:
        if any(n in f'{p.device} {p.description} {p.manufacturer}'.lower() for n in NOMES_ARDUINO):
            return p.device
    achadas = ', '.join(f'{p.device} ({p.description})' for p in portas) or 'nenhuma'
    raise SystemExit(f'Não achei o Arduino no USB. Portas encontradas: {achadas}. '
                     'Confira o cabo e o driver CH340, ou rode com --porta COMx.')


class Robo:
    """Manda comandos ao Arduino pelo Bluetooth (HC-05) ou USB. Sem porta: só imprime (modo de teste)."""

    def __init__(self, porta=None, baud=9600):
        self.serial, self.pendentes = None, 0
        if porta == 'auto':
            porta = encontrar_porta()
            print(f'Robô encontrado na porta {porta}.')
        if porta:
            import serial  # pip install pyserial
            self.serial = serial.Serial(porta, baud, timeout=0.2)
            time.sleep(2)  # pelo USB o Uno reinicia ao abrir a porta

    def _esperar(self, prazo=15):
        """Espera os "ok" das ações em andamento: o Uno só guarda 64 bytes enquanto mexe os braços.
        Retorna False se o robô não respondeu (desligado ou Bluetooth caído)."""
        fim = time.time() + prazo
        while self.pendentes and time.time() < fim:
            linha = self.serial.readline().decode('ascii', 'ignore').strip()
            if linha.startswith(('ok', 'erro')):
                self.pendentes -= 1
                if linha.startswith('erro'):
                    print(f'[robô] {linha}')
        respondeu = self.pendentes == 0
        if not respondeu:
            print('[robô] sem resposta: confira se está ligado e se o Bluetooth está conectado')
        self.pendentes = 0
        return respondeu

    def _enviar(self, linha, esperar):
        linha = sem_acento(linha).replace('\n', ' ')
        if not self.serial:
            print(f'[robô] {linha}')
            return
        self._esperar()
        self.serial.write((linha + '\n').encode('ascii', 'ignore'))
        self.pendentes += 1
        if esperar:
            self._esperar()

    def acao(self, nome):
        """Não espera terminar: o computador já pode falar enquanto o robô se mexe."""
        self._enviar(f'a {nome}', esperar=False)

    def modo_autonomo(self, ligado):
        """Coreografia sozinha (True) ou braços parados esperando a IA (False)."""
        self._enviar(f'm {1 if ligado else 0}', esperar=True)

    def texto(self, msg):
        self._enviar(f't {msg[:60]}', esperar=True)  # 't ' + 60 + Enter cabe nos 64 bytes do Uno


def microfone():
    """Reconhecimento de voz (Google, precisa de internet). Se o CP4 usa outro, troquem aqui."""
    import speech_recognition as sr  # pip install SpeechRecognition pyaudio
    rec, mic = sr.Recognizer(), sr.Microphone()
    with mic as fonte:
        rec.adjust_for_ambient_noise(fonte, duration=1)

    def ouvir():
        with mic as fonte:
            audio = rec.listen(fonte, phrase_time_limit=8)
        try:
            return rec.recognize_google(audio, language='pt-BR')
        except sr.UnknownValueError:
            return ''
        except sr.RequestError as erro:   # sem internet: não derruba o programa
            print(f'Reconhecimento de voz sem internet ({erro}). Use --vosk (offline) ou --teclado.')
            return ''
    return ouvir


def microfone_offline(pasta_modelo):
    """Reconhecimento de voz SEM internet (Vosk). Baixe o modelo português pequeno
    (vosk-model-small-pt-0.3, ~30 MB) em alphacephei.com/vosk/models e descompacte numa pasta."""
    import pyaudio, vosk  # pip install vosk
    vosk.SetLogLevel(-1)
    rec = vosk.KaldiRecognizer(vosk.Model(pasta_modelo), 16000)
    entrada = pyaudio.PyAudio().open(format=pyaudio.paInt16, channels=1, rate=16000,
                                     input=True, frames_per_buffer=4000)
    entrada.stop_stream()   # só escuta dentro de ouvir(): não ouve a própria voz do TARS

    def ouvir():
        entrada.start_stream()
        try:
            while True:
                if rec.AcceptWaveform(entrada.read(4000, exception_on_overflow=False)):
                    texto = json.loads(rec.Result()).get('text', '')
                    if texto:
                        return texto
        finally:
            entrada.stop_stream()
    return ouvir


def _voz_portugues(motor):
    for v in motor.getProperty('voices'):
        # No Windows o nome diz o idioma; no Mac (ex.: "Luciana") ele só aparece em v.languages.
        idiomas = ' '.join(str(l) for l in (getattr(v, 'languages', None) or []))
        nome = (v.name + ' ' + v.id + ' ' + idiomas).lower()
        if 'portug' in nome or 'brazil' in nome or 'pt-br' in nome or 'pt_br' in nome:
            return v
    return None


def voz():
    """Voz sintetizada offline (vozes do Windows). Se o CP4 usa outra, troquem aqui."""
    import pyttsx3  # pip install pyttsx3
    pt = _voz_portugues(pyttsx3.init())
    if not pt:
        print('Aviso: nenhuma voz em português; vai falar com sotaque. Windows: Configurações → '
              'Hora e idioma → Fala. Mac: Ajustes → Acessibilidade → Conteúdo Falado → Voz do sistema.')

    def falar(texto):
        motor = pyttsx3.init()   # um motor novo por fala: no Windows o pyttsx3 às vezes emudece
        if pt:
            motor.setProperty('voice', pt.id)
        motor.say(texto)
        motor.runAndWait()
        motor.stop()
    return falar


def diagnostico(a):
    """Confere tudo o que a apresentação precisa e diz o que falta. Rodar na sala antes de apresentar."""
    falhas = 0

    def item(nome, teste):
        nonlocal falhas
        try:
            print(f'  OK     {nome}: {teste()}')
        except Exception as erro:
            falhas += 1
            print(f'  FALHA  {nome}: {erro}')

    def ollama():
        with urllib.request.urlopen(OLLAMA.replace('/api/chat', '/api/tags'), timeout=5) as r:
            nomes = [m['name'] for m in json.loads(r.read())['models']]
        if a.modelo not in nomes and f'{a.modelo}:latest' not in nomes:
            raise RuntimeError(f'modelo {a.modelo} não baixado (ollama pull {a.modelo}); '
                               f'disponíveis: {", ".join(nomes) or "nenhum"}')
        return f'rodando, modelo {a.modelo}'

    def ia():
        inicio = time.time()
        fala, acao = decidir('Oi, TARS!', [], a.modelo)
        return f'{time.time() - inicio:.1f} s → "{fala}" [{acao}]'

    def voz_pt():
        import pyttsx3
        v = _voz_portugues(pyttsx3.init())
        if not v:
            raise RuntimeError('nenhuma voz em português (Configurações → Hora e idioma → Fala)')
        return v.name

    def mic():
        import speech_recognition as sr
        nomes = sr.Microphone.list_microphone_names()
        if not nomes:
            raise RuntimeError('nenhum microfone encontrado')
        return f'{len(nomes)} dispositivo(s) de áudio'

    def reconhecimento():
        if a.vosk:
            import os, vosk
            if not os.path.isdir(a.vosk):
                raise RuntimeError(f'pasta do modelo Vosk não existe: {a.vosk}')
            return f'offline (Vosk, {a.vosk})'
        urllib.request.urlopen('https://www.google.com', timeout=5)
        return 'Google (internet ok)'

    def portas():
        from serial.tools import list_ports
        ps = [f'{p.device} ({p.description})' for p in list_ports.comports()]
        if not ps:
            raise RuntimeError('nenhuma porta COM: o HC-05 está pareado?')
        return '; '.join(ps)

    def robo():
        if not a.porta:
            raise RuntimeError('rode com --porta COMx para testar o robô')
        r = Robo(a.porta, a.baud)
        r.texto('DIAGNOSTICO')
        r.acao('sim')
        if not r._esperar():
            raise RuntimeError(f'o robô não respondeu em {a.porta}')
        return f'respondeu em {a.porta} (deve ter mexido os braços)'

    print('Diagnóstico do TARS')
    for nome, teste in [('Ollama', ollama), ('IA responde', ia), ('Voz em português', voz_pt),
                        ('Microfone', mic), ('Reconhecimento de voz', reconhecimento),
                        ('Portas COM', portas), ('Robô', robo)]:
        item(nome, teste)
    print('Tudo pronto para apresentar.' if not falhas else f'{falhas} item(ns) com FALHA: corrija antes de apresentar.')


def _autoteste():
    assert interpretar('{"fala": "Olá, humano.", "acao": "saudar"}') == ('Olá, humano.', 'saudar')
    assert interpretar('Claro! {"fala": "Não.", "acao": "não"}') == ('Não.', 'nao')
    assert interpretar('{"fala": "Ok", "acao": "voar"}') == ('Ok', 'repouso')
    assert interpretar('resposta sem json') == ('resposta sem json', 'repouso')
    assert acao_por_palavra('Oi, TARS!') == 'saudar'
    assert acao_por_palavra('Boa noite, pessoal') == 'saudar'
    assert acao_por_palavra('Que noite bonita') is None      # "oi" dentro de "noite" não conta
    assert acao_por_palavra('Dança pra gente!') == 'dancar'
    assert sem_acento('ação Olá') == 'acao Ola'
    print('autoteste ok')


def main():
    ap = argparse.ArgumentParser(description='TARS: voz + LLM local + robô')
    ap.add_argument('--porta', help='porta do robô (ex.: COM5, ou auto para achar o Uno no USB); sem ela, só simula')
    ap.add_argument('--baud', type=int, default=9600, help='9600 no Bluetooth, 115200 no cabo USB')
    ap.add_argument('--modelo', default=MODELO)
    ap.add_argument('--teclado', action='store_true', help='digitar em vez de usar o microfone (o TARS continua falando)')
    ap.add_argument('--vosk', metavar='PASTA', help='reconhecimento de voz offline com este modelo Vosk')
    ap.add_argument('--mudo', action='store_true', help='não falar em voz alta (só texto)')
    ap.add_argument('--sem-robo', action='store_true')
    ap.add_argument('--teste', action='store_true', help='autoteste das funções')
    ap.add_argument('--diagnostico', action='store_true', help='confere Ollama, voz, microfone, internet e robô')
    a = ap.parse_args()
    if a.teste:
        return _autoteste()
    if a.diagnostico:
        return diagnostico(a)

    robo = Robo(None if a.sem_robo else a.porta, a.baud)
    try:
        conversar(robo, a)
    finally:   # também no Ctrl+C: o robô volta a se mexer sozinho
        robo.modo_autonomo(True)


def conversar(robo, a):
    robo.modo_autonomo(False)
    if a.teclado:
        ouvir = lambda: input('você> ')
    else:
        ouvir = microfone_offline(a.vosk) if a.vosk else microfone()
    falar = print if a.mudo else voz()
    historico = []
    robo.texto('ACORDANDO...')
    print('Carregando a IA (a primeira vez demora)...')
    try:
        inicio = time.time()
        perguntar_llm([{'role': 'user', 'content': 'Oi'}], a.modelo)   # aquece: tira a demora da 1ª pergunta
        print(f'IA pronta em {time.time() - inicio:.0f} s.')
    except OSError as erro:
        print(f'Ollama não respondeu ({erro}). Abra o Ollama e confira o modelo com "ollama list".')
    robo.texto('PRONTO')
    print('TARS pronto. Diga "desligar" para sair.')
    while True:
        robo.texto('OUVINDO...')
        ouvido = ouvir().strip()
        if not ouvido:
            continue
        print(f'ouvi: {ouvido}')
        if sem_acento(ouvido).lower().strip(' .!') in ('desligar', 'sair'):
            robo.texto('ATE LOGO')
            robo.acao('repouso')
            break
        robo.texto('PENSANDO...')
        robo.acao('pensar')
        try:
            fala, acao = decidir(ouvido, historico, a.modelo)
        except OSError as erro:   # Ollama fechado ou modelo não baixado
            print(f'Ollama: {erro} — abra o Ollama e confira o modelo com "ollama list"')
            fala, acao = 'Perdi a conexão com o meu cérebro.', acao_por_palavra(ouvido) or 'triste'
        print(f'TARS: {fala}  [{acao}]')
        robo.texto(fala)
        robo.acao(acao)
        falar(fala)


if __name__ == '__main__':
    main()
