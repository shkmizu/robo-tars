"""
api_simulada.py — uma API do BairroVivo de mentira, para testar o TARS sem o backend do grupo.
Implementa o mesmo contrato descrito em CITIZENTECH.md e guarda tudo em api_simulada_dados.json.

  python api_simulada.py                 sobe em http://localhost:8000 (chave do dispositivo: chave-demo)
  python api_simulada.py --porta 8001 --chave outra

Abra http://localhost:8000 no navegador: é um painel de operador com as ocorrências e as leituras
do sensor, que se atualiza sozinho. Para simular a API fora do ar, feche este programa (Ctrl+C):
o TARS guarda tudo na fila e reenvia quando ela voltar.
"""
import argparse, html, json, os, re, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
CATEGORIAS = ('Buraco / pavimento', 'Iluminação', 'Descarte irregular', 'Calçada / acessibilidade',
              'Mobiliário urbano')
STATUS = ('Recebida', 'Em análise', 'Encaminhada', 'Em atendimento', 'Resolvida', 'Não procedente')


class Banco:
    def __init__(self, arquivo):
        self.arquivo, self.trava = arquivo, threading.Lock()
        try:
            with open(arquivo, encoding='utf-8') as f:
                self.d = json.load(f)
        except (OSError, ValueError):
            self.d = {'ocorrencias': [], 'leituras': [], 'idempotencia': {}}

    def salvar(self):
        with open(self.arquivo, 'w', encoding='utf-8') as f:
            json.dump(self.d, f, ensure_ascii=False, indent=1)


def criar_servidor(porta=8000, chave='chave-demo', arquivo=os.path.join(AQUI, 'api_simulada_dados.json'),
                   silencioso=False):
    banco = Banco(arquivo)

    class Tratador(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            if not silencioso:
                print(f'[API] {self.command} {self.path} → {args[1] if len(args) > 1 else ""}')

        def _json(self, status, corpo):
            dados = json.dumps(corpo, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

        def _corpo(self):
            n = int(self.headers.get('Content-Length') or 0)
            try:
                return json.loads(self.rfile.read(n) or b'{}')
            except ValueError:
                return None

        def _autorizado(self):
            if self.headers.get('X-Device-Key') == chave:
                return True
            self._json(401, {'erro': 'X-Device-Key ausente ou inválida'})
            return False

        def do_GET(self):
            if self.path in ('/', '/painel'):
                return self._painel()
            if self.path == '/api/saude':
                return self._json(200, {'status': 'ok'})
            if self.path == '/api/ocorrencias':
                with banco.trava:
                    return self._json(200, banco.d['ocorrencias'])
            m = re.fullmatch(r'/api/ocorrencias/([\w-]+)', self.path)
            if m:
                if not self._autorizado():
                    return
                with banco.trava:
                    oc = next((o for o in banco.d['ocorrencias'] if o['protocolo'].upper() == m[1].upper()), None)
                return self._json(200, oc) if oc else self._json(404, {'erro': 'protocolo não encontrado'})
            self._json(404, {'erro': 'rota não existe'})

        def do_POST(self):
            m = re.fullmatch(r'/api/dispositivos/([\w-]+)/leituras', self.path)
            if self.path != '/api/ocorrencias' and not m:
                return self._json(404, {'erro': 'rota não existe'})
            if not self._autorizado():
                return
            corpo = self._corpo()
            if not isinstance(corpo, dict):
                return self._json(400, {'erro': 'JSON inválido'})
            chave_id = self.headers.get('Idempotency-Key')
            with banco.trava:
                if chave_id and chave_id in banco.d['idempotencia']:      # reenvio: mesma resposta
                    return self._json(201, banco.d['idempotencia'][chave_id])
                if m:
                    corpo['id'] = len(banco.d['leituras']) + 1
                    banco.d['leituras'] = (banco.d['leituras'] + [corpo])[-500:]
                    resp = {'id': corpo['id']}
                else:
                    faltando = [c for c in ('titulo', 'descricao', 'categoria') if not corpo.get(c)]
                    if faltando or corpo['categoria'] not in CATEGORIAS:
                        return self._json(422, {'erro': 'campos inválidos', 'faltando': faltando,
                                                'categorias_validas': CATEGORIAS})
                    protocolo = f'BV-{len(banco.d["ocorrencias"]) + 1:04d}'
                    oc = dict(corpo, protocolo=protocolo, status='Recebida', criada_em=time.strftime('%Y-%m-%d %H:%M:%S'),
                              historico=[{'status': 'Recebida', 'em': time.strftime('%Y-%m-%d %H:%M:%S')}])
                    banco.d['ocorrencias'].append(oc)
                    resp = {'protocolo': protocolo, 'status': 'Recebida'}
                if chave_id:
                    banco.d['idempotencia'][chave_id] = resp
                banco.salvar()
            self._json(201, resp)

        def do_PATCH(self):
            """Simula o operador mudando o status: PATCH /api/ocorrencias/BV-0001 {"status": "Em análise"}"""
            m = re.fullmatch(r'/api/ocorrencias/([\w-]+)', self.path)
            corpo = self._corpo() or {}
            if not m or corpo.get('status') not in STATUS:
                return self._json(422, {'erro': 'use {"status": um de ' + ', '.join(STATUS) + '}'})
            with banco.trava:
                oc = next((o for o in banco.d['ocorrencias'] if o['protocolo'].upper() == m[1].upper()), None)
                if not oc:
                    return self._json(404, {'erro': 'protocolo não encontrado'})
                oc['status'] = corpo['status']
                oc['historico'].append({'status': corpo['status'], 'em': time.strftime('%Y-%m-%d %H:%M:%S')})
                banco.salvar()
            self._json(200, oc)

        def _painel(self):
            with banco.trava:
                ocs = list(reversed(banco.d['ocorrencias']))[:30]
                leituras = list(reversed(banco.d['leituras']))[:12]
            e = html.escape
            linhas = ''.join(
                f'<tr><td>{e(o["protocolo"])}</td><td>{e(o["categoria"])}</td><td>{e(o["titulo"])}</td>'
                f'<td>{e(o.get("origem", ""))}</td><td>{e(o["status"])}</td><td>{e(o["criada_em"])}</td></tr>' for o in ocs)
            sens = ''.join(
                f'<tr><td>{e(str(l.get("momento", "")))}</td><td>{e(str(l.get("evento", "")))}</td>'
                f'<td>{e(str(l.get("estado", "")))}</td><td>{e(str(l.get("distancia_cm", "")))}</td></tr>' for l in leituras)
            pagina = f'''<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="2">
<title>BairroVivo — painel (API simulada)</title>
<style>body{{font:15px system-ui,sans-serif;margin:24px;background:#f4f6f3;color:#1d2420}}
table{{border-collapse:collapse;width:100%;margin-bottom:28px;background:#fff}}
td,th{{border:1px solid #cfd6cf;padding:6px 8px;text-align:left}}th{{background:#e3e9e2}}
.aviso{{color:#7a4a12}}</style>
<h1>BairroVivo — painel do operador</h1>
<p class="aviso">API simulada para demonstração: os dados abaixo são de teste.</p>
<h2>Ocorrências ({len(banco.d["ocorrencias"])})</h2>
<table><tr><th>Protocolo</th><th>Categoria</th><th>Título</th><th>Origem</th><th>Status</th><th>Criada em</th></tr>{linhas}</table>
<h2>Últimas leituras do sensor do totem</h2>
<table><tr><th>Momento</th><th>Evento</th><th>Estado</th><th>Distância (cm)</th></tr>{sens}</table>'''
            dados = pagina.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

    return ThreadingHTTPServer(('0.0.0.0', porta), Tratador)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='API simulada do BairroVivo')
    ap.add_argument('--porta', type=int, default=8000)
    ap.add_argument('--chave', default='chave-demo')
    a = ap.parse_args()
    srv = criar_servidor(a.porta, a.chave)
    print(f'API simulada do BairroVivo em http://localhost:{a.porta}  (painel: abra no navegador)')
    print(f'Chave do dispositivo: {a.chave}   — Ctrl+C para "derrubar" a API')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
