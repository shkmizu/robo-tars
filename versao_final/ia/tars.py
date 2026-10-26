"""
tars.py — o "cérebro" do robô TARS: ouve, pensa (LLM local no Ollama), fala e mexe o robô.
Versão final: use com versao_final/arduino/tars_ia. Ao começar, desliga a coreografia do robô
(comando "m 0") para os braços não fazerem barulho perto do microfone; ao sair, religa ("m 1").

Uso (no Windows, os .bat desta pasta já rodam estes comandos):
  python tars.py --porta auto --baud 115200 --teclado       robô no cabo USB, digitando (o TARS ainda fala)
  python tars.py --porta auto --baud 115200 --diagnostico   confere tudo antes de apresentar
  python tars.py --porta auto --baud 115200                 conversa por voz (apresentação)
  python tars.py --escolher-voz                             ouvir e escolher a voz do TARS
  python tars.py --porta COM5                               robô pelo Bluetooth (a porta "de saída" do HC-05)
  python tars.py --sem-robo --teclado                       sem robô: mostra os comandos que seriam enviados
  python tars.py --teste                                    autoteste (não precisa de microfone, Ollama nem robô)
  Sem internet: --vosk <pasta do modelo> (reconhecimento offline) e --voz-offline (voz do Windows).

Para usar dentro do script do CP4:
  from tars import Robo, decidir
  robo, historico = Robo('COM5'), []
  fala, acao = decidir(texto_reconhecido, historico)
  robo.texto(fala); robo.acao(acao)        # depois o script do CP4 fala `fala` como já faz
"""
import argparse, json, os, re, time, unicodedata, urllib.error, urllib.request

MODELO = 'llama3.2:3b'      # troque pelo modelo que vocês usam (veja com: ollama list)
OLLAMA = 'http://localhost:11434/api/chat'
# Voz do TARS: neural da Microsoft (edge-tts, precisa de internet). Para ouvir e escolher outra:
# python tars.py --escolher-voz (ou 5_escolher_voz.bat), que grava a escolha em voz.txt.
VOZ_TARS = 'pt-BR-AntonioNeural'
TOM = '+0Hz'           # negativo = mais grave; mudar o tom deixa a voz mais "robótica"
VELOCIDADE = '+0%'     # negativo = mais devagar
VOZES = [   # (nome no edge-tts, descrição) para o --escolher-voz
    ('pt-BR-AntonioNeural', 'masculina, brasileira'),
    ('pt-BR-FranciscaNeural', 'feminina, brasileira'),
    ('pt-BR-ThalitaMultilingualNeural', 'feminina, brasileira, a mais nova e expressiva'),
    ('en-US-AndrewMultilingualNeural', 'masculina, multilíngue, bem natural (pode ter leve sotaque)'),
    ('en-US-BrianMultilingualNeural', 'masculina, multilíngue, descontraída (pode ter leve sotaque)'),
    ('en-US-AvaMultilingualNeural', 'feminina, multilíngue (pode ter leve sotaque)'),
    # ElevenLabs (precisa da chave em elevenlabs_chave.txt). A Brian funciona no plano grátis; as vozes
    # brasileiras são da biblioteca da ElevenLabs e pela API pedem um plano pago (a partir do Starter).
    ('elevenlabs:nPczCjzI2devNBz1zQrb', '[ElevenLabs] Brian, masculina, multilíngue (plano grátis)'),
    ('elevenlabs:E9a8LlXPNWtyvvSoZzrb', '[ElevenLabs] Talis, brasileira, natural e descontraída'),
    ('elevenlabs:Dps47AVoFamqqkDShRDS', '[ElevenLabs] Fabio Oliveira, brasileira, grave e madura'),
    ('elevenlabs:dIwbXBNI0A6EpdIWTvvr', '[ElevenLabs] Thiago Morais, brasileira'),
    ('elevenlabs:blPx0tvsvee8CuFd63lX', '[ElevenLabs] Sávio, brasileira, calma e pausada'),
]
ELEVEN_MODELO = 'eleven_flash_v2_5'   # o mais rápido; 'eleven_multilingual_v2' é mais natural, mas demora mais
# Risada depois das piadas, junto com o gesto "piada": o modelo v3 da ElevenLabs entende "[laughs]"
# e ri de verdade. É gerada uma vez só por conversa. Só nas vozes [ElevenLabs]; para desligar: RISADA = ''
RISADA = '[laughs] Ha ha ha!'
RISADA_MODELO = 'eleven_v3'
ARQUIVO_CHAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'elevenlabs_chave.txt')
ARQUIVO_VOZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voz.txt')
ACOES = ('saudar', 'dancar', 'feliz', 'triste', 'sim', 'nao', 'pensar', 'repouso',
         'andar', 'roda', 'piada', 'duvida', 'susto')

# Personalidade do TARS — ajustem do jeito do grupo (é o que mais muda a "cara" do robô).
# A última parte (o formato JSON e a lista de ações) precisa continuar igual.
PERSONALIDADE = """Você é o TARS, o robô do filme Interestelar, numa versão de mesa feita por estudantes.
Seu nível de humor é {humor}% e o de honestidade é {honestidade}%: responda com respostas secas, sinceras e
um pouco irônicas. Com humor perto de 0% seja totalmente sério; perto de 100%, faça piada em quase toda resposta.
Com honestidade baixa você pode inventar exageros; alta, diga só a verdade, mesmo que seja indelicada.
Fale em português do Brasil, em no máximo 2 frases curtas.
Responda SOMENTE com um JSON assim: {"fala": "o que você diz", "acao": "uma ação"}.
Ações possíveis: saudar (cumprimentos e despedidas), dancar (quando pedirem dança ou música),
sim (concordar), nao (discordar ou recusar), feliz (elogios, boas notícias), triste (notícias ruins),
andar (quando pedirem para andar ou caminhar), roda (quando pedirem para rolar ou girar),
piada (quando você contar uma piada ou estiver brincando), duvida (quando não souber),
susto (surpresa, susto), repouso (todo o resto)."""

# Ajustes do TARS que mudam com a voz: "humor 60%", "honestidade 100 por cento".
AJUSTES = {'humor': 75, 'honestidade': 90}

# Palavras que disparam a ação na hora, sem depender da LLM: garantem o comportamento na
# apresentação (ex.: "Oi, TARS" sempre acena). Sem acento e em minúsculas.
PALAVRAS = {   # a primeira que aparecer na lista ganha: "Olá TARS, caminhe" anda
    'andar': ('anda', 'ande', 'andar', 'caminha', 'caminhe', 'caminhar'),
    'roda': ('rola', 'role', 'rolar', 'modo roda', 'vira roda', 'gira', 'gire', 'girar'),
    'piada': ('piada', 'piadas', 'me faz rir', 'me faca rir'),
    'saudar': ('oi', 'ola', 'bom dia', 'boa tarde', 'boa noite', 'tchau', 'ate logo', 'acene', 'acena'),
    'dancar': ('danca', 'dance', 'dancar', 'dancinha'),
    'feliz': ('parabens', 'muito bem', 'mandou bem'),
}


# Falas do filme (adaptadas): respondem na hora, sem esperar a IA. Chave: trechos que disparam
# (sem acento, minúsculos); valor: (fala, ação). {humor} e {honestidade} viram os números atuais.
FILME = [
    (('quem e voce', 'se apresente', 'apresente se', 'fale sobre voce'),
     ('Eu sou o TARS. Ex-robô de missão, agora robô de mesa. Humor em {humor} por cento.', 'saudar')),
    (('esta brincando', 'ta brincando', 'e serio', 'luz de piada'),
     ('Eu tenho uma luz de piada. Quando ela piscar, eu estava brincando.', 'piada')),
    (('nao e possivel', 'isso e impossivel'),
     ('Não é possível? Não. É necessário.', 'sim')),
    (('posso confiar', 'confia em mim', 'voce e honesto'),
     ('Honestidade em {honestidade} por cento. Os outros {resto} por cento são diplomacia.', 'sim')),
    (('qual sua missao', 'qual e a sua missao', 'qual a sua missao'),
     ('Ajudar a humanidade. E fazer piadas sobre ela no caminho.', 'feliz')),
]


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
                        'messages': [{'role': 'system', 'content': _ajustes(PERSONALIDADE)}] + historico[-10:]}).encode()
    req = urllib.request.Request(OLLAMA, corpo, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())['message']['content']


def _ajustes(texto):
    return (texto.replace('{humor}', str(AJUSTES['humor']))
                 .replace('{honestidade}', str(AJUSTES['honestidade']))
                 .replace('{resto}', str(100 - AJUSTES['honestidade'])))


def comando_especial(ouvido):
    """Ajustes e falas do filme, sem a IA. Retorna (fala, ação, texto da tela) ou None."""
    t = ' '.join(''.join(c if c.isalnum() or c == '%' else ' ' for c in sem_acento(ouvido).lower()).split())
    for nome in AJUSTES:
        if nome not in t:
            continue
        numero = re.search(nome + r'\D{0,25}?(\d{1,3})', t)
        if numero:
            AJUSTES[nome] = min(int(numero.group(1)), 100)
            fala = f'{nome.capitalize()} ajustado para {AJUSTES[nome]} por cento.'
            if nome == 'humor' and AJUSTES[nome] >= 90:
                fala += ' Vou providenciar uma luz de piada.'
            acao = 'piada' if nome == 'humor' and AJUSTES[nome] >= 90 else 'sim'
            return fala, acao, f'{nome.upper()} {AJUSTES[nome]}%'
        if any(p in t for p in ('qual', 'nivel', 'quanto', 'como esta')):
            return (f'{nome.capitalize()} em {AJUSTES[nome]} por cento.', 'pensar',
                    f'{nome.upper()} {AJUSTES[nome]}%')
    for gatilhos, (fala, acao) in FILME:
        if any(g in t for g in gatilhos):
            return _ajustes(fala), acao, None
    return None


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


class SaidaDeSom:
    """Deixa a saída de som sempre aberta, tocando silêncio enquanto o TARS está calado. Sem isso, o
    Windows "desliga" a placa de som entre uma fala e outra e come o começo da frase seguinte."""
    TAXA = 24000   # a mesma do áudio da ElevenLabs (pcm_24000)

    def __init__(self):
        import pyaudio, queue, threading  # pip install pyaudio (o mesmo do microfone)
        self._queue, self._threading = queue, threading
        self.stream = pyaudio.PyAudio().open(format=pyaudio.paInt16, channels=1, rate=self.TAXA,
                                             output=True, frames_per_buffer=self.TAXA // 50)
        self.fila = queue.Queue()
        threading.Thread(target=self._rodar, daemon=True).start()

    def _rodar(self):
        silencio = bytes(2 * self.TAXA // 50)   # 20 ms
        while True:
            try:
                item = self.fila.get(timeout=0.01)
            except self._queue.Empty:
                self.stream.write(silencio)
                continue
            if isinstance(item, bytes):
                self.stream.write(item)
            else:
                item.set()   # chegou ao fim da fala

    def tocar(self, pedacos):
        """Toca áudio PCM 16 bits mono 24 kHz, pedaço por pedaço (já começa enquanto o resto chega)."""
        sobra = b''
        for pedaco in pedacos:
            pedaco = sobra + pedaco
            corte = len(pedaco) - len(pedaco) % 2   # amostras de 2 bytes não podem ser partidas
            self.fila.put(pedaco[:corte])
            sobra = pedaco[corte:]
        fim = self._threading.Event()
        self.fila.put(fim)
        fim.wait()


SAIDA = []   # a SaidaDeSom, criada por acordar_som()


def acordar_som():
    if not SAIDA:
        try:
            SAIDA.append(SaidaDeSom())
        except Exception as erro:   # sem pyaudio ou sem saída de som: as falas usam o silêncio no começo
            print(f'(não consegui manter a saída de som aberta: {erro})')
            SAIDA.append(None)
    return SAIDA[0]


def _tocar(arquivo):
    import sys, subprocess
    if sys.platform == 'win32' and arquivo.endswith('.wav'):
        import winsound
        winsound.PlaySound(arquivo, winsound.SND_FILENAME)
    elif sys.platform == 'win32':     # MCI do próprio Windows: toca mp3 sem instalar nada
        import ctypes
        mci = ctypes.windll.winmm.mciSendStringW
        mci(f'open "{arquivo}" type mpegvideo alias tars', None, 0, None)
        mci('play tars wait', None, 0, None)
        mci('close tars', None, 0, None)
    elif sys.platform == 'darwin':
        subprocess.run(['afplay', arquivo], check=True)
    else:
        subprocess.run(['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', arquivo], check=True)


def _com_silencio(mp3, ms=400):
    """Põe silêncio no começo do mp3 do edge-tts (MPEG-2 camada III, 24 kHz, 48 kbps, mono): a saída de
    som do notebook "acorda" durante o silêncio e não come o começo da fala. Outro formato: não mexe."""
    inicio = 10 + int.from_bytes(mp3[6:10], 'big') if mp3[:3] == b'ID3' else 0   # pula a etiqueta ID3
    if mp3[inicio:inicio + 2] != b'\xff\xf3' or mp3[inicio + 2] & 0xFD != 0x64 or mp3[inicio + 3] >> 6 != 3:
        return mp3
    quadro = b'\xff\xf3\x64\xc0' + bytes(140)    # 144 bytes = 24 ms de silêncio
    return mp3[:inicio] + quadro * (ms // 24) + mp3[inicio:]


def _voz_escolhida():
    """(voz, tom, velocidade) gravados pelo --escolher-voz em voz.txt; senão, os do topo do arquivo."""
    try:
        with open(ARQUIVO_VOZ, encoding='utf-8') as f:
            nome, tom, vel = (f.read().split() + [TOM, VELOCIDADE])[:3]
        return nome, tom, vel
    except (OSError, ValueError):
        return VOZ_TARS, TOM, VELOCIDADE


def chave_elevenlabs():
    """Chave da API: variável ELEVENLABS_API_KEY ou o arquivo elevenlabs_chave.txt (fora do GitHub)."""
    if os.environ.get('ELEVENLABS_API_KEY'):
        return os.environ['ELEVENLABS_API_KEY'].strip()
    for arquivo in (ARQUIVO_CHAVE, ARQUIVO_CHAVE + '.txt'):   # o Bloco de Notas às vezes põe .txt de novo
        try:
            with open(arquivo, encoding='utf-8-sig') as f:
                return f.read().strip()
        except OSError:
            pass
    return None


def sem_etiquetas(texto):
    """Tira etiquetas de emoção como "[laughs]" (só a ElevenLabs v3 sabe interpretá-las)."""
    return re.sub(r'\s*\[[^\]]*\]', '', texto).strip()


def voz_elevenlabs(voice_id):
    """Voz da ElevenLabs pela API (precisa de internet e da chave). Com a SaidaDeSom, toca enquanto
    o áudio ainda chega (streaming); sem ela, grava um WAV com silêncio no começo."""
    import tempfile, wave
    chave = chave_elevenlabs()
    if not chave:
        raise RuntimeError('falta a chave da ElevenLabs (rode o 5_escolher_voz.bat e escolha uma voz [ElevenLabs])')
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream?output_format=pcm_24000'
    saida = acordar_som()

    def pedir(texto, modelo):
        corpo = json.dumps({'text': texto, 'model_id': modelo}).encode()
        req = urllib.request.Request(url, corpo, {'xi-api-key': chave, 'Content-Type': 'application/json'})
        try:
            r = urllib.request.urlopen(req, timeout=30)
            return r, r.read(4800)   # espera só os primeiros 0,1 s de áudio, não a frase toda
        except urllib.error.HTTPError as erro:   # mostra o motivo: chave errada, créditos, plano...
            raise RuntimeError(f'ElevenLabs {erro.code}: {erro.read().decode("utf-8", "ignore")[:200]}') from None

    risada = []   # o áudio da risada, guardado depois da primeira vez (economiza créditos e tempo)

    def tocar_pcm(pcm, nome_arquivo):
        if saida:
            return lambda: saida.tocar([pcm])
        caminho = os.path.join(tempfile.gettempdir(), nome_arquivo)
        with wave.open(caminho, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(bytes(2 * 24000 * 4 // 10) + pcm)   # 0,4 s de silêncio: a saída de som "acorda"
        return lambda: _tocar(caminho)

    def preparar_risada():
        if not risada:
            r, primeiro = pedir(RISADA, RISADA_MODELO)
            with r:
                risada.append(primeiro + r.read())
        return tocar_pcm(risada[0], 'tars_risada.wav')

    def preparar(texto):
        r, primeiro = pedir(sem_etiquetas(texto), ELEVEN_MODELO)
        if saida:
            def pedacos():
                yield primeiro
                with r:
                    while True:
                        try:
                            pedaco = r.read(4800)
                        except OSError as erro:   # internet caiu no meio da frase
                            print(f'(a fala foi cortada: {erro})')
                            return
                        if not pedaco:
                            return
                        yield pedaco
            return lambda: saida.tocar(pedacos())
        with r:
            return tocar_pcm(primeiro + r.read(), 'tars_fala.wav')
    if RISADA:
        preparar.risada = preparar_risada
    return preparar


def _motor(nome):
    """preparar(texto) da voz pelo nome gravado em voz.txt."""
    if nome.startswith('elevenlabs:'):
        return voz_elevenlabs(nome.split(':', 1)[1])
    return voz_neural(nome)


def voz_neural(nome=None):
    """Voz neural (edge-tts). Precisa de internet; levanta erro se não conseguir."""
    import asyncio, tempfile, edge_tts  # pip install edge-tts
    arquivo = os.path.join(tempfile.gettempdir(), 'tars_fala.mp3')
    escolhida, tom, vel = _voz_escolhida()
    nome = nome or escolhida
    if nome.startswith('elevenlabs:'):   # reserva da ElevenLabs: a voz padrão da Microsoft
        nome, tom, vel = VOZ_TARS, TOM, VELOCIDADE

    def preparar(texto):
        fala = edge_tts.Communicate(sem_etiquetas(texto), nome, rate=vel, pitch=tom)
        asyncio.run(fala.save(arquivo))
        if not acordar_som():   # com a saída de som aberta, o silêncio só atrasaria a fala
            with open(arquivo, 'rb') as f:
                mp3 = _com_silencio(f.read())
            with open(arquivo, 'wb') as f:
                f.write(mp3)
        return lambda: _tocar(arquivo)
    return preparar


def voz_offline():
    """Voz do sistema (pyttsx3), sem internet."""
    import pyttsx3  # pip install pyttsx3
    pt = _voz_portugues(pyttsx3.init())
    if not pt:
        print('Aviso: nenhuma voz em português; vai falar com sotaque. Windows: Configurações → '
              'Hora e idioma → Fala. Mac: Ajustes → Acessibilidade → Conteúdo Falado → Voz do sistema.')

    def falar(texto):
        motor = pyttsx3.init()   # um motor novo por fala: no Windows o pyttsx3 às vezes emudece
        if pt:
            motor.setProperty('voice', pt.id)
        motor.say(sem_etiquetas(texto))
        motor.runAndWait()
        motor.stop()
    return lambda texto: lambda: falar(texto)


def voz(offline=False):
    """Retorna preparar(texto) → tocar(). Preparar gera o áudio antes, para os braços e a voz
    começarem juntos. Usa a voz escolhida; se ela falhar (internet, chave, créditos), passa para a
    voz da Microsoft e depois para a voz do sistema, até o fim da conversa."""
    acordar_som()
    nome = _voz_escolhida()[0]
    motores = [] if offline else [lambda: _motor(nome)]
    if not offline and nome.startswith('elevenlabs:'):
        motores.append(lambda: voz_neural(VOZ_TARS))
    motores.append(voz_offline)
    atual = []

    def proximo():
        while motores:
            try:
                atual[:] = [motores.pop(0)()]
                return
            except Exception as erro:   # biblioteca não instalada, falta a chave...
                print(f'(voz indisponível: {erro})')

    def preparar(texto):
        while True:
            if not atual:
                proximo()
            try:
                return atual[0](texto)
            except Exception as erro:
                if not motores:
                    raise
                print(f'(voz falhou: {erro}; usando a próxima voz daqui em diante)')
                atual.clear()

    def preparar_risada():
        """tocar() da risada, ou uma função que não faz nada se esta voz não sabe rir."""
        try:
            return getattr(atual[0], 'risada', lambda: lambda: None)() if atual else (lambda: None)
        except Exception as erro:
            print(f'(risada indisponível: {erro})')
            return lambda: None
    preparar.risada = preparar_risada
    proximo()
    return preparar


def escolher_voz():
    """Toca uma amostra de cada voz e grava a escolhida em voz.txt."""
    amostra = 'Olá, eu sou o TARS. Meu nível de humor está em setenta e cinco por cento. Quer ouvir uma piada?'
    atual = _voz_escolhida()[0]
    while True:
        print('\nVozes do TARS:')
        for i, (nome, descricao) in enumerate(VOZES, 1):
            print(f'  {i}. {descricao}{"   <- atual" if nome == atual else ""}')
        resposta = input('Número para ouvir, "g" + número para gravar (ex.: g3), Enter para sair: ').strip().lower()
        if not resposta:
            return
        gravar = resposta.startswith('g')
        try:
            nome = VOZES[int(resposta.lstrip('g ')) - 1][0]
        except (ValueError, IndexError):
            print('Não entendi.')
            continue
        if gravar:
            with open(ARQUIVO_VOZ, 'w', encoding='utf-8') as f:
                f.write(f'{nome} {TOM} {VELOCIDADE}\n')
            print(f'Gravado: o TARS agora fala com {nome}.')
            atual = nome
            continue
        try:
            if nome.startswith('elevenlabs:') and not chave_elevenlabs():
                chave = input('Cole a chave da API da ElevenLabs (elevenlabs.io → Developers → API Keys): ').strip()
                if not chave:
                    continue
                with open(ARQUIVO_CHAVE, 'w', encoding='utf-8') as f:
                    f.write(chave + '\n')
            _motor(nome)(amostra)()
        except Exception as erro:
            print(f'Não consegui tocar essa voz ({erro}). Confira a internet.')


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
        if not a.voz_offline:
            try:
                _motor(_voz_escolhida()[0])('Diagnóstico da voz.')()
                return f'{_voz_escolhida()[0]} (internet ok)'
            except Exception as erro:
                print(f'         voz escolhida falhou ({erro}); conferindo a voz do sistema')
        import pyttsx3
        v = _voz_portugues(pyttsx3.init())
        if not v:
            raise RuntimeError('sem voz neural e sem voz do sistema em português (Configurações → Hora e idioma → Fala)')
        return f'{v.name} (voz do sistema)'

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
    assert acao_por_palavra('Olá tars, caminhar') == 'andar'
    assert acao_por_palavra('Conta uma piada') == 'piada'
    assert comando_especial('TARS, ajuste o humor para 60%') == ('Humor ajustado para 60 por cento.', 'sim', 'HUMOR 60%')
    assert comando_especial('Qual o seu nível de humor?')[0] == 'Humor em 60 por cento.'
    assert comando_especial('honestidade 100 por cento')[2] == 'HONESTIDADE 100%'
    assert comando_especial('Você tem senso de humor?') is None    # sem número nem pergunta: vai para a IA
    assert comando_especial('humor 95')[1] == 'piada'
    assert 'Os outros 0 por cento' in comando_especial('Posso confiar em você?')[0]
    assert comando_especial('Você está brincando?')[1] == 'piada'
    assert comando_especial('Que dia é hoje?') is None
    assert '60' not in _ajustes(PERSONALIDADE) and '95%' in _ajustes(PERSONALIDADE)
    assert _com_silencio(b'\xff\xfb\x90\x64abc') == b'\xff\xfb\x90\x64abc'   # outro formato de mp3: não mexe
    assert sem_etiquetas('Um robô entra num bar. [laughs]') == 'Um robô entra num bar.'
    AJUSTES.update(humor=75, honestidade=90)
    print('autoteste ok')


def main():
    ap = argparse.ArgumentParser(description='TARS: voz + LLM local + robô')
    ap.add_argument('--porta', help='porta do robô (ex.: COM5, ou auto para achar o Uno no USB); sem ela, só simula')
    ap.add_argument('--baud', type=int, default=9600, help='9600 no Bluetooth, 115200 no cabo USB')
    ap.add_argument('--modelo', default=MODELO)
    ap.add_argument('--teclado', action='store_true', help='digitar em vez de usar o microfone (o TARS continua falando)')
    ap.add_argument('--vosk', metavar='PASTA', help='reconhecimento de voz offline com este modelo Vosk')
    ap.add_argument('--voz-offline', action='store_true', help='usar a voz do sistema em vez da voz neural (sem internet)')
    ap.add_argument('--mudo', action='store_true', help='não falar em voz alta (só texto)')
    ap.add_argument('--sem-robo', action='store_true')
    ap.add_argument('--teste', action='store_true', help='autoteste das funções')
    ap.add_argument('--escolher-voz', action='store_true', help='ouvir as vozes e escolher a do TARS')
    ap.add_argument('--diagnostico', action='store_true', help='confere Ollama, voz, microfone, internet e robô')
    a = ap.parse_args()
    if a.teste:
        return _autoteste()
    if a.diagnostico:
        return diagnostico(a)
    if a.escolher_voz:
        return escolher_voz()

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
    preparar = (lambda texto: lambda: None) if a.mudo else voz(a.voz_offline)
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
        especial = comando_especial(ouvido)
        if especial:
            fala, acao, tela = especial
        else:
            robo.texto('PENSANDO...')
            robo.acao('pensar')
            tela = None
            try:
                fala, acao = decidir(ouvido, historico, a.modelo)
            except OSError as erro:   # Ollama fechado ou modelo não baixado
                print(f'Ollama: {erro} — abra o Ollama e confira o modelo com "ollama list"')
                fala, acao = 'Perdi a conexão com o meu cérebro.', acao_por_palavra(ouvido) or 'triste'
        print(f'TARS: {fala}  [{acao}]')
        tocar = preparar(fala)   # gera o áudio antes: braços e voz começam juntos
        if acao == 'piada':
            rir = getattr(preparar, 'risada', lambda: lambda: None)()
        robo.texto(tela or fala)
        if acao == 'piada':   # conta a piada parado; no fim, ri junto com o gesto e a "luz de piada"
            robo.acao('repouso')
            tocar()
            robo.acao('piada')
            rir()
        else:
            robo.acao(acao)
            tocar()


if __name__ == '__main__':
    main()
