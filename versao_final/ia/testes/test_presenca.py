"""Modelo de presença: características, precisão e a versão em C (presenca.h) dando o mesmo resultado."""
import os, random, shutil, subprocess, tempfile, unittest

import _base  # noqa: F401
import presenca as P


class TestCaracteristicas(unittest.TestCase):
    def test_parado_a_meio_metro(self):
        media, incl, desvio, perto = P.caracteristicas([50] * 10)
        self.assertAlmostEqual(media, 0.5)
        self.assertAlmostEqual(incl, 0.0)
        self.assertAlmostEqual(desvio, 0.0)
        self.assertEqual(perto, 1.0)

    def test_aproximando_a_1_m_por_s(self):
        _, incl, desvio, _ = P.caracteristicas([200 - 10 * i for i in range(10)])
        self.assertAlmostEqual(incl, -1.0, places=6)
        self.assertAlmostEqual(desvio, 0.0, places=6)

    def test_sem_eco_conta_como_longe_e_pico_isolado_some(self):
        self.assertAlmostEqual(P.caracteristicas([0] * 10)[0], P.ALCANCE_CM / 100)
        self.assertAlmostEqual(P.caracteristicas([50] * 4 + [300] + [50] * 5)[0], 0.5)   # mediana de 3


class TestModelo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modelo = P.carregar_header()

    def test_header_gerado_acerta_dados_novos(self):
        acc, _ = P.avaliar(self.modelo, P.dados_sinteticos(800, semente=123))
        self.assertGreater(acc, 0.85)

    def test_casos_claros(self):
        self.assertEqual(P.prever(self.modelo, [0] * 10)[0], 'vazio')
        self.assertEqual(P.prever(self.modelo, [60, 61, 59, 60, 62, 61, 60, 59, 60, 61])[0], 'presente')
        self.assertEqual(P.prever(self.modelo, [250 - 12 * i for i in range(10)])[0], 'chegando')
        self.assertEqual(P.prever(self.modelo, [60 + 12 * i for i in range(10)])[0], 'saindo')

    def test_header_le_o_que_exportou(self):
        m = P.treinar(P.dados_sinteticos(200, semente=1), epocas=5)
        with tempfile.TemporaryDirectory() as d:
            arq = os.path.join(d, 'm.h')
            P.exportar_header(m, arq)
            lido = P.carregar_header(arq)
        for chave in ('media', 'escala', 'vies'):
            for a, b in zip(m[chave], lido[chave]):
                self.assertAlmostEqual(a, b, places=5)


@unittest.skipUnless(shutil.which('g++'), 'sem g++ para compilar presenca.h no computador')
class TestPresencaEmC(unittest.TestCase):
    def test_c_e_python_concordam(self):
        modelo = P.carregar_header()
        rnd = random.Random(7)
        janelas = [P.amostra_sintetica(rnd, c) for _ in range(60) for c in P.CLASSES]
        pasta = os.path.join(_base.IA, '..', 'arduino', 'tars_ia')
        linhas = ',\n'.join('{' + ','.join(map(str, j)) + '}' for j in janelas)
        prog = f'''#include <stdio.h>
#include "presenca.h"
static const uint16_t J[][10] = {{{linhas}}};
int main() {{ for (unsigned i = 0; i < sizeof(J) / sizeof(J[0]); i++) {{ float c; int k = presenca_classificar(J[i], &c);
  printf("%d %.6f\\n", k, c); }} return 0; }}'''
        with tempfile.TemporaryDirectory() as d:
            fonte, exe = os.path.join(d, 't.cpp'), os.path.join(d, 't')
            with open(fonte, 'w') as f:
                f.write(prog)
            subprocess.run(['g++', '-O2', '-I', pasta, fonte, '-o', exe], check=True)
            saida = subprocess.run([exe], capture_output=True, text=True, check=True).stdout.split('\n')
        for j, linha in zip(janelas, saida):
            k, conf = linha.split()
            classe, p = P.prever(modelo, j)
            self.assertEqual(P.CLASSES[int(k)], classe)
            self.assertAlmostEqual(float(conf), max(p), places=3)


if __name__ == '__main__':
    unittest.main()
