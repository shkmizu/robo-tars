"""Comunicação com o Arduino: eventos JSON separados dos "ok", batimento e cabo desconectado."""
import queue, threading, unittest

import _base  # noqa: F401
import tars


class SerialFalso:
    def __init__(self, linhas):
        self.entrada = queue.Queue()
        for l in linhas:
            self.entrada.put(l)
        self.escrito = []
        self.quebrado = False

    def readline(self):
        if self.quebrado:
            raise OSError('cabo puxado')
        try:
            return (self.entrada.get(timeout=0.05) + '\n').encode()
        except queue.Empty:
            return b''

    def write(self, dados):
        if self.quebrado:
            raise OSError('cabo puxado')
        self.escrito.append(dados.decode().strip())
        if not dados.startswith(b'p'):
            self.entrada.put('ok')


def robo_com(serial):
    r = tars.Robo(None)
    r.serial = serial
    threading.Thread(target=r._ler, daemon=True).start()
    return r


class TestRobo(unittest.TestCase):
    def test_eventos_vao_para_a_fila_e_ok_para_os_comandos(self):
        s = SerialFalso(['TARS ligando...', '{"ev":"estado","estado":"presente","d":62,"conf":93}', 'lixo{'])
        r = robo_com(s)
        r.texto('OLÁ')
        self.assertEqual(s.escrito, ['t OLA'])
        ev = r.eventos.get(timeout=1)
        self.assertEqual(ev, {'ev': 'estado', 'estado': 'presente', 'd': 62, 'conf': 93})
        self.assertTrue(r.eventos.empty())

    def test_batimento_e_comandos_do_sensor(self):
        s = SerialFalso([])
        r = robo_com(s)
        r.leituras_brutas(True)
        r.pedir_estado_sensor()
        r._escrever('p')
        self.assertEqual(s.escrito, ['s 1', 's', 'p'])

    def test_cabo_puxado_nao_derruba(self):
        s = SerialFalso([])
        r = robo_com(s)
        s.quebrado = True
        r.acao('saudar')                      # não levanta exceção
        self.assertIsNone(r.serial)
        self.assertEqual(r.eventos.get(timeout=1)['ev'], 'desconectado')
        r.texto('continua')                   # sem robô: só imprime


if __name__ == '__main__':
    unittest.main()
