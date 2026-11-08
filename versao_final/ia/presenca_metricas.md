# Modelo de presença do TARS: métricas

Gerado por `presenca.py treinar`. Treino: 6000 janelas (0 gravadas no robô, o resto sintético); teste: 2000 janelas sintéticas separadas, que o modelo não viu.

**Acurácia no teste: 92.2%**

| real ↓ / previsto → | vazio | chegando | presente | saindo | revocação |
|---|---|---|---|---|---|
| **vazio** | 481 | 12 | 0 | 7 | 96% |
| **chegando** | 31 | 433 | 33 | 3 | 87% |
| **presente** | 0 | 3 | 485 | 12 | 97% |
| **saindo** | 17 | 4 | 35 | 444 | 89% |
| precisão | 91% | 96% | 88% | 95% | |

Os dados sintéticos simulam o ruído do HC-SR04 (0,3–1,2 cm), falhas de eco (até 5%), ecos espúrios (até 2%) e o balanço natural de uma pessoa parada (0,5–4 cm). Com gravações reais em `gravacoes/` (`presenca.py gravar`), elas entram no treino.
