"""
bairrovivo.py — a ponte entre o TARS e a API do BairroVivo (GS CitizenTech).

O Arduino não tem Wi-Fi: o sensor manda os eventos pelo USB para o tars.py, e esta ponte os envia
para a API do MVP. Ela também registra e consulta as ocorrências que o cidadão faz por voz no totem.

  - Autenticação do dispositivo: cabeçalho X-Device-Key (a chave fica fora do código).
  - Falha de rede: o que não foi enviado fica numa fila gravada em disco (fila_bairrovivo.json)
    e é reenviado sozinho, com espera crescente entre as tentativas (2 s, 4 s, 8 s… até 60 s).
  - Reenvio sem duplicar: cada envio leva um Idempotency-Key; a API ignora o repetido.

Contrato da API: CITIZENTECH.md, seção "Contrato da API". Para testar sem o backend do grupo:
  python api_simulada.py
"""
import json, os, threading, time, urllib.error, urllib.request, uuid

AQUI = os.path.dirname(os.path.abspath(__file__))
ARQ_CONFIG = os.path.join(AQUI, 'bairrovivo_config.json')
ARQ_CHAVE = os.path.join(AQUI, 'bairrovivo_chave.txt')
ARQ_FILA = os.path.join(AQUI, 'fila_bairrovivo.json')

# Mesmas categorias do plano do BairroVivo (seção 3.2)
CATEGORIAS = ('Buraco / pavimento', 'Iluminação', 'Descarte irregular', 'Calçada / acessibilidade',
              'Mobiliário urbano')

CONFIG_PADRAO = {
    'url': 'http://localhost:8000',          # API do BairroVivo (ou a simulada)
    'prefixo': '/api',
    'dispositivo_id': 'tars-totem-01',
    'local': {'descricao': 'Totem BairroVivo (piloto)', 'latitude': -23.5505, 'longitude': -46.6333},
    'timeout_s': 5,
    'max_leituras_na_fila': 500,            # leituras antigas saem primeiro; ocorrências nunca saem
}


def carregar_config(caminho=ARQ_CONFIG):
    cfg = json.loads(json.dumps(CONFIG_PADRAO))
    if os.path.exists(caminho):
        with open(caminho, encoding='utf-8') as f:
            cfg.update(json.load(f))
    cfg['url'] = os.environ.get('BAIRROVIVO_URL', cfg['url']).rstrip('/')
    cfg['chave'] = os.environ.get('BAIRROVIVO_CHAVE') or _ler_chave()
    return cfg


def _ler_chave():
    try:
        with open(ARQ_CHAVE, encoding='utf-8-sig') as f:
            return f.read().strip() or None
    except OSError:
        return None


class ErroAPI(Exception):
    def __init__(self, status, corpo):
        super().__init__(f'API respondeu {status}: {corpo[:200]}')
        self.status = status


class Ponte:
    """Envia leituras e ocorrências. Tudo o que não precisa de resposta na hora vai pela fila."""

    def __init__(self, config=None, arquivo_fila=ARQ_FILA, avisar=print, iniciar=True):
        self.cfg = config or carregar_config()
        self.arquivo_fila = arquivo_fila
        self.avisar = avisar
        self._trava = threading.Lock()
        self._acordar = threading.Event()
        self._parar = False
        self.online = None          # None = ainda não sabe; True/False depois da 1ª tentativa
        self.espera = 2
        self.fila = self._carregar_fila()
        if not self.cfg.get('chave'):
            self.avisar('(BairroVivo: sem chave do dispositivo; crie bairrovivo_chave.txt ou BAIRROVIVO_CHAVE)')
        if iniciar:
            threading.Thread(target=self._trabalhar, daemon=True).start()

    # ── API pública ──────────────────────────────────────────────────────────────
    def enviar_evento_sensor(self, ev):
        """Evento do Arduino ({"ev":"estado","estado":"presente","d":62,"conf":93}) → leitura na API."""
        corpo = {
            'dispositivo_id': self.cfg['dispositivo_id'], 'tipo': 'presenca_ultrassonico',
            'evento': ev.get('ev'), 'estado': ev.get('estado'), 'distancia_cm': ev.get('d'),
            'confianca': (ev.get('conf') or 0) / 100, 'origem': 'sensor_fisico',
            'momento': _agora_iso(),
        }
        self._enfileirar('POST', f'/dispositivos/{self.cfg["dispositivo_id"]}/leituras', corpo, 'leitura')

    def registrar_ocorrencia(self, rascunho):
        """Tenta registrar na hora (para o TARS falar o protocolo). Sem rede: guarda na fila.
        → (protocolo ou None, resposta ou None)"""
        corpo = dict(rascunho)
        corpo.setdefault('dispositivo_id', self.cfg['dispositivo_id'])
        corpo.setdefault('referencia_totem', self.cfg['local'])
        corpo.setdefault('momento', _agora_iso())
        corpo['requer_revisao'] = True       # sugestão automática: um operador sempre revisa
        item = self._item('POST', '/ocorrencias', corpo, 'ocorrencia')
        try:
            resp = self._requisicao(item)
            self._marcar_online(True)
            return resp.get('protocolo'), resp
        except ErroAPI as erro:
            if 400 <= erro.status < 500 and erro.status != 429:
                raise                         # dado inválido ou chave errada: reenviar não resolve
            self._marcar_online(False)
        except OSError:
            self._marcar_online(False)
        with self._trava:
            self.fila.append(item)
            self._salvar_fila()
        self._acordar.set()
        return None, None

    def consultar(self, protocolo):
        """→ dict da ocorrência, None se não existe; levanta OSError sem rede."""
        try:
            resp = self._requisicao(self._item('GET', f'/ocorrencias/{protocolo}', None, 'consulta'))
            self._marcar_online(True)
            return resp
        except ErroAPI as erro:
            if erro.status == 404:
                return None
            raise OSError(str(erro)) from None

    def saude(self):
        try:
            self._requisicao(self._item('GET', '/saude', None, 'saude'))
            self._marcar_online(True)
            return True
        except (OSError, ErroAPI):
            self._marcar_online(False)
            return False

    def pendentes(self):
        with self._trava:
            return len(self.fila)

    def parar(self):
        self._parar = True
        self._acordar.set()

    # ── fila e envio ─────────────────────────────────────────────────────────────
    def _item(self, metodo, caminho, corpo, tipo):
        return {'id': str(uuid.uuid4()), 'metodo': metodo, 'caminho': caminho, 'corpo': corpo, 'tipo': tipo}

    def _enfileirar(self, metodo, caminho, corpo, tipo):
        with self._trava:
            self.fila.append(self._item(metodo, caminho, corpo, tipo))
            leituras = [i for i in self.fila if i['tipo'] == 'leitura']
            excesso = len(leituras) - self.cfg['max_leituras_na_fila']
            if excesso > 0:
                descartar = {i['id'] for i in leituras[:excesso]}
                self.fila = [i for i in self.fila if i['id'] not in descartar]
            self._salvar_fila()
        self._acordar.set()

    def _requisicao(self, item):
        url = self.cfg['url'] + self.cfg['prefixo'] + item['caminho']
        cab = {'Accept': 'application/json', 'Idempotency-Key': item['id']}
        if self.cfg.get('chave'):
            cab['X-Device-Key'] = self.cfg['chave']
        dados = None
        if item['corpo'] is not None:
            dados = json.dumps(item['corpo'], ensure_ascii=False).encode('utf-8')
            cab['Content-Type'] = 'application/json'
        req = urllib.request.Request(url, dados, cab, method=item['metodo'])
        try:
            with urllib.request.urlopen(req, timeout=self.cfg['timeout_s']) as r:
                texto = r.read().decode('utf-8') or '{}'
                return json.loads(texto)
        except urllib.error.HTTPError as erro:
            raise ErroAPI(erro.code, erro.read().decode('utf-8', 'ignore')) from None

    def _trabalhar(self):
        while not self._parar:
            self._acordar.wait(timeout=self.espera if self.online is False else 2)
            self._acordar.clear()
            while not self._parar:
                with self._trava:
                    item = self.fila[0] if self.fila else None
                if item is None:
                    break
                try:
                    self._requisicao(item)
                except ErroAPI as erro:
                    if 400 <= erro.status < 500 and erro.status != 429:
                        self.avisar(f'(BairroVivo recusou {item["tipo"]}: {erro}; descartado)')
                    else:
                        self._marcar_online(False)
                        break
                except OSError:
                    self._marcar_online(False)
                    break
                with self._trava:
                    if self.fila and self.fila[0]['id'] == item['id']:
                        self.fila.pop(0)
                        self._salvar_fila()
                self._marcar_online(True)

    def _marcar_online(self, ok):
        if ok:
            if self.online is False:
                self.avisar(f'(BairroVivo: conexão de volta; {self.pendentes()} envio(s) na fila)')
            self.online, self.espera = True, 2
        else:
            if self.online is not False:
                self.avisar("(BairroVivo fora do ar: guardando na fila e tentando de novo)")
            self.online = False
            self.espera = min(60, self.espera * 2)

    def _carregar_fila(self):
        try:
            with open(self.arquivo_fila, encoding='utf-8') as f:
                return json.load(f)
        except (OSError, ValueError):
            return []

    def _salvar_fila(self):
        tmp = self.arquivo_fila + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.fila, f, ensure_ascii=False)
        os.replace(tmp, self.arquivo_fila)


def _agora_iso():
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')
