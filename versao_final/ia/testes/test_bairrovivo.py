"""Ponte com a API: registro, consulta, fila sem rede, reenvio sem duplicar, chave e validação."""
import json, os, socket, tempfile, threading, time, unittest

import _base  # noqa: F401
import api_simulada
import bairrovivo


def porta_livre():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class TestPonte(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.dados = os.path.join(self.pasta, 'api.json')
        self.porta = porta_livre()
        self.srv = None
        self.subir()
        cfg = dict(bairrovivo.CONFIG_PADRAO, url=f'http://127.0.0.1:{self.porta}', chave='k', timeout_s=2)
        self.avisos = []
        self.ponte = bairrovivo.Ponte(cfg, arquivo_fila=os.path.join(self.pasta, 'fila.json'), avisar=self.avisos.append)

    def tearDown(self):
        self.ponte.parar()
        self.derrubar()

    def subir(self):
        self.srv = api_simulada.criar_servidor(self.porta, 'k', self.dados, silencioso=True)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def derrubar(self):
        if self.srv:
            self.srv.shutdown()
            self.srv.server_close()
            self.srv = None

    def api(self):
        with open(self.dados, encoding='utf-8') as f:
            return json.load(f)

    def esperar_fila_vazia(self, prazo=20):
        fim = time.time() + prazo
        while self.ponte.pendentes() and time.time() < fim:
            time.sleep(0.2)
        return self.ponte.pendentes() == 0

    def test_registra_e_consulta(self):
        prot, _ = self.ponte.registrar_ocorrencia({'titulo': 'Poste apagado', 'descricao': 'Rua A',
                                                   'categoria': 'Iluminação', 'origem': 'totem_voz'})
        self.assertEqual(prot, 'BV-0001')
        oc = self.ponte.consultar(prot)
        self.assertEqual(oc['status'], 'Recebida')
        self.assertTrue(oc['requer_revisao'])          # sugestão automática sempre vai para revisão
        self.assertIsNone(self.ponte.consultar('BV-9999'))

    def test_sem_rede_guarda_e_reenvia_quando_volta(self):
        self.derrubar()
        prot, _ = self.ponte.registrar_ocorrencia({'titulo': 'Buraco', 'descricao': 'Rua B',
                                                   'categoria': 'Buraco / pavimento'})
        self.ponte.enviar_evento_sensor({'ev': 'estado', 'estado': 'presente', 'd': 60, 'conf': 91})
        self.assertIsNone(prot)
        self.assertEqual(self.ponte.pendentes(), 2)
        self.assertFalse(self.ponte.online)
        # a fila está no disco: sobrevive se o programa fechar
        with open(self.ponte.arquivo_fila, encoding='utf-8') as f:
            self.assertEqual(len(json.load(f)), 2)
        self.subir()
        self.assertTrue(self.esperar_fila_vazia())
        d = self.api()
        self.assertEqual([o['titulo'] for o in d['ocorrencias']], ['Buraco'])
        self.assertEqual(d['leituras'][0]['estado'], 'presente')
        self.assertEqual(d['leituras'][0]['origem'], 'sensor_fisico')

    def test_reenvio_com_mesma_chave_nao_duplica(self):
        item = self.ponte._item('POST', '/ocorrencias', {'titulo': 'Lixo', 'descricao': 'x',
                                                         'categoria': 'Descarte irregular'}, 'ocorrencia')
        r1, r2 = self.ponte._requisicao(item), self.ponte._requisicao(item)
        self.assertEqual(r1, r2)
        self.assertEqual(len(self.api()['ocorrencias']), 1)

    def test_chave_errada_e_dado_invalido_nao_vao_para_fila(self):
        with self.assertRaises(bairrovivo.ErroAPI) as ctx:
            self.ponte.registrar_ocorrencia({'titulo': 'x', 'descricao': 'y', 'categoria': 'Inexistente'})
        self.assertEqual(ctx.exception.status, 422)
        self.ponte.cfg['chave'] = 'errada'
        with self.assertRaises(bairrovivo.ErroAPI) as ctx:
            self.ponte.registrar_ocorrencia({'titulo': 'x', 'descricao': 'y', 'categoria': 'Iluminação'})
        self.assertEqual(ctx.exception.status, 401)
        self.assertEqual(self.ponte.pendentes(), 0)

    def test_fila_de_leituras_tem_limite(self):
        self.derrubar()
        self.ponte.cfg['max_leituras_na_fila'] = 5
        self.ponte.registrar_ocorrencia({'titulo': 'Banco', 'descricao': 'x', 'categoria': 'Mobiliário urbano'})
        for i in range(12):
            self.ponte.enviar_evento_sensor({'ev': 'leitura', 'estado': 'vazio', 'd': i, 'conf': 90})
        tipos = [i['tipo'] for i in self.ponte.fila]
        self.assertEqual(tipos.count('leitura'), 5)
        self.assertEqual(tipos.count('ocorrencia'), 1)    # ocorrência nunca é descartada
        self.assertEqual(self.ponte.fila[-1]['corpo']['distancia_cm'], 11)   # ficam as mais novas


if __name__ == '__main__':
    unittest.main()
