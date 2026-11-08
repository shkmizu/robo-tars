"""Totem do BairroVivo: o que o TARS faz em cada situação do sensor e da conversa.
Sem Ollama, sem microfone e sem robô: a IA, a voz e a API são trocadas por versões de teste."""
import json, unittest
from unittest import mock

import _base  # noqa: F401
import tars
import totem


class RelogioFalso:
    def __init__(self):
        self.t = 1_700_000_000.0   # um instante fixo; o teste avança o tempo à mão

    def __call__(self):
        return self.t


class PonteFalsa:
    def __init__(self, online=True):
        self.online, self.ocorrencias, self.leituras = online, [], []
        self.cfg = {'local': {'descricao': 'Totem de teste'}}

    def enviar_evento_sensor(self, ev):
        self.leituras.append(ev)

    def registrar_ocorrencia(self, r):
        self.ocorrencias.append(dict(r))
        return (f'BV-{len(self.ocorrencias):04d}', {}) if self.online else (None, None)

    def consultar(self, protocolo):
        if not self.online:
            raise OSError('sem rede')
        n = int(protocolo.split('-')[1])
        return {'titulo': self.ocorrencias[n - 1]['titulo'], 'status': 'Em análise'} if n <= len(self.ocorrencias) else None


class Cenario(unittest.TestCase):
    def setUp(self, llm=None):
        self.rel = RelogioFalso()
        self.robo = tars.Robo(None)
        self.robo._enviar = lambda linha, esperar: self.comandos.append(linha)
        self.comandos, self.falas, self.roteiro = [], [], []
        self.ponte = PonteFalsa()
        for alvo, nome, valor in ((totem, 'perguntar_llm', llm or self._sem_llm),
                                  (totem, 'decidir', lambda *a, **k: ('Resposta da IA.', 'repouso')),
                                  (totem.time, 'sleep', lambda s: None)):
            trocar = mock.patch.object(alvo, nome, valor)
            trocar.start()
            self.addCleanup(trocar.stop)
        self.t = totem.Totem(self.robo, self.ponte, lambda f: (lambda: self.falas.append(f)), self._ouvir,
                             relogio=self.rel, log=lambda *a: None)
        self.t.esperar_proximo()

    @staticmethod
    def _sem_llm(*a, **k):
        raise OSError('Ollama desligado no teste')

    def _ouvir(self, timeout=None):
        if self.roteiro:
            return self.roteiro.pop(0)
        self.rel.t += timeout or 6
        return ''

    def sensor(self, estado, d=60):
        self.robo.eventos.put({'ev': 'estado', 'estado': estado, 'd': d, 'conf': 90})

    def dizer(self, *frases):
        self.roteiro += list(frases)
        for _ in frases:
            self.t.passo()

    def ultima(self):
        return self.falas[-1] if self.falas else ''


class TestPresenca(Cenario):
    def test_quem_so_passa_nao_e_cumprimentado(self):
        self.sensor('chegando', 140)
        self.t.passo()
        self.sensor('vazio', 0)
        self.t.passo()
        self.assertEqual(self.t.fase, 'espera')
        self.assertEqual(self.falas, [])

    def test_chegou_e_ficou_cumprimenta_conforme_o_periodo(self):
        self.sensor('chegando', 120)
        self.t.passo()
        self.rel.t += 1.2
        self.t.passo()
        self.assertEqual(self.t.fase, 'conversa')
        self.assertIn('BairroVivo', self.ultima())
        self.assertIn('a saudar', self.comandos)

    def test_microfone_desligado_sem_ninguem(self):
        self.roteiro = ['isto não deveria ser ouvido']
        for _ in range(5):
            self.t.passo()
        self.assertEqual(self.roteiro, ['isto não deveria ser ouvido'])

    def test_pessoa_foi_embora_encerra(self):
        self.sensor('presente')
        self.t.passo()
        self.sensor('vazio', 0)
        self.rel.t += 3
        self.t.passo()
        self.t.passo()
        self.assertEqual(self.ultima(), 'Até logo!')
        self.assertEqual(self.t.fase, 'espera')

    def test_silencio_oferece_ajuda_e_depois_se_despede(self):
        self.sensor('presente')
        self.t.passo()
        for _ in range(3):
            self.t.passo()
        self.assertIn('Posso ajudar?', self.ultima())
        for _ in range(5):
            self.t.passo()
        self.assertIn('Obrigado', self.ultima())
        self.assertEqual(self.t.fase, 'aguardando_saida')
        self.t.passo()                                # ainda na frente: não cumprimenta de novo
        self.assertEqual(self.t.fase, 'aguardando_saida')

    def test_eventos_do_sensor_viram_telemetria(self):
        self.sensor('presente')
        self.robo.eventos.put({'ev': 'leitura', 'estado': 'presente', 'd': 61, 'conf': 88})
        self.t.passo()
        self.assertEqual([e['ev'] for e in self.ponte.leituras], ['estado', 'leitura'])


class TestOcorrencias(Cenario):
    def chegar(self):
        self.sensor('presente')
        self.t.passo()

    def test_registra_poste_apagado_por_voz_com_confirmacao(self):
        self.chegar()
        self.dizer('Tem um poste apagado aqui perto')
        self.assertEqual(self.t.fase, 'pedindo_local')
        self.dizer('Rua das Flores, 120')
        self.assertIn('Posso enviar?', self.ultima())
        self.dizer('sim, pode enviar')
        oc = self.ponte.ocorrencias[0]
        self.assertEqual((oc['categoria'], oc['local_texto'], oc['origem'], oc['prioridade_sugerida']),
                         ('Iluminação', 'Rua das Flores, 120', 'totem_voz', 'Média'))
        self.assertIn('B V, número 1', self.ultima())
        self.assertIn('t PROTOCOLO BV-0001', self.comandos)

    def test_local_dito_junto_vai_direto_para_confirmacao(self):
        self.chegar()
        self.dizer('tem um poste apagado na Rua das Flores 120')
        self.assertEqual(self.t.fase, 'confirmando')
        self.assertEqual(self.t.rascunho['local_texto'], 'Rua das Flores 120')

    def test_nao_cancela_o_registro(self):
        self.chegar()
        self.dizer('tem lixo jogado na esquina da rua 3', 'esquina da rua 3', 'não, está errado')
        self.assertEqual(self.ponte.ocorrencias, [])
        self.assertEqual(self.t.fase, 'conversa')

    def test_sem_rede_guarda_e_avisa(self):
        self.ponte.online = False
        self.chegar()
        self.dizer('um buraco enorme na avenida Brasil', 'avenida Brasil 500', 'sim')
        self.assertIn('Guardei', self.ultima())

    def test_consulta_protocolo(self):
        self.ponte.ocorrencias.append({'titulo': 'Banco quebrado'})
        self.chegar()
        self.dizer('quero saber o andamento do protocolo 1')
        self.assertIn('Em análise', self.ultima())
        self.dizer('e o protocolo 7?')
        self.assertIn('Não encontrei', self.ultima())

    def test_consulta_pede_o_numero(self):
        self.ponte.ocorrencias.append({'titulo': 'Banco quebrado'})
        self.chegar()
        self.dizer('quero consultar meu protocolo', 'é o 1')
        self.assertIn('Em análise', self.ultima())

    def test_obstaculo_registra_uma_vez_para_revisao(self):
        self.sensor('obstaculo', 45)
        self.t.passo()
        self.sensor('vazio', 0)
        self.sensor('obstaculo', 44)
        self.t.passo()
        self.assertEqual(len(self.ponte.ocorrencias), 1)
        oc = self.ponte.ocorrencias[0]
        self.assertEqual((oc['categoria'], oc['origem']), ('Calçada / acessibilidade', 'sensor_fisico'))

    def test_sensor_com_falha_atende_quando_alguem_fala(self):
        self.sensor('falha', 0)
        self.roteiro = ['tem uma placa caída na praça da matriz']
        self.t.passo()
        self.assertEqual(self.t.fase, 'confirmando')
        self.assertEqual(self.t.rascunho['local_texto'], 'praça da matriz')
        self.assertEqual(self.t.rascunho['categoria'], 'Mobiliário urbano')


class TestComIA(Cenario):
    def setUp(self):
        def llm(historico, modelo, sistema=None, timeout=None):
            if 'cumprimente' in sistema.lower():
                return json.dumps({'fala': 'Boa noite, humano. Algum poste te deixou no escuro?', 'acao': 'saudar'})
            return json.dumps({'intencao': 'registrar', 'categoria': 'Calçada / acessibilidade',
                               'titulo': 'Calçada quebrada', 'descricao': 'Calçada com buraco e sem rampa',
                               'local': 'Rua Augusta 300', 'fala': '', 'acao': 'sim'})
        super().setUp(llm)

    def test_saudacao_gerada_pela_ia_e_campos_extraidos(self):
        self.sensor('presente')
        self.t.passo()
        self.assertIn('poste', self.ultima())
        self.dizer('a calçada da Rua Augusta 300 está quebrada e sem rampa')
        self.assertEqual(self.t.fase, 'confirmando')          # a IA já trouxe o local
        self.assertEqual(self.t.rascunho['titulo'], 'Calçada quebrada')
        self.assertEqual(self.t.rascunho['prioridade_sugerida'], 'Alta')


if __name__ == '__main__':
    unittest.main()
