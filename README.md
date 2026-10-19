# Robô TARS: MDF 3 mm, corte a laser, micro servos SG90

Robô inspirado no TARS (*Interestelar*): 4 blocos verticais lado a lado.
- **Corpo:** os 2 blocos do meio, uma caixa só com um vinco gravado. Guarda toda a eletrônica e toda a fiação.
- **Braços:** os 2 blocos de fora. Cada um gira em torno de um eixo **no meio da sua altura**, movido por um SG90.
- **Tela:** um OLED 0,96" na frente.

Demonstração 3D interativa: https://claude.ai/artifact/CNWZmAH6V9aymZm9zFhAPm (privada; compartilhe pelo menu Share).

## Para o técnico do laser → pasta `laser/`

| Arquivo | Uso |
|---|---|
| `00_pente_de_teste.dxf` | cortar **antes**, para conferir o kerf |
| `chapa_1.dxf` | as 37 peças numa chapa de **900 × 600 mm**, MDF 3 mm, em mm, escala 1:1. Camada CORTE (vermelha) e GRAVACAO (azul) |
| `chapa_1.svg` | prévia com o nome de cada peça (não vai para o laser) |
| `LEIA-ME_tecnico.txt` | instruções curtas para o técnico |

O DXF foi gerado direto de `projeto.py`, sem precisar do Fusion. Para regenerar depois de mudar alguma medida:
```bash
python laser/exportar_laser.py
```
O exportador **se recusa a gerar o arquivo** se alguma verificação de projeto falhar.

---

## Medidas dos componentes (de onde vieram)

| Componente | Medidas usadas | Fonte |
|---|---|---|
| **SG90** | corpo 22,7 × 12,1 × 22,7 mm; abas de 32,4 mm, 2,4 mm de espessura, a 15,9 mm da base; furos Ø2,2 a 1,9 mm da ponta das abas; eixo a 5,8 mm da ponta do corpo; topo do eixo a 30,7 mm; 1,8 kgf·cm; 250 mm de cabo | desenho "SG90 Servo - Dimensions", [Aus Electronics Direct TA0132](https://www.auselectronicsdirect.com.au/assets/brochures/TA0132.pdf) |
| Horn duplo do SG90 | 32 mm, cubo Ø6,9, braço de 1,5 mm, furos a 4–14 mm do centro | mesmo documento, p. 5 |
| **Arduino Uno R3** | 68,58 × 53,34 mm; furos (13,97; 2,54), (15,24; 50,8), (66,04; 7,62), (66,04; 35,56) | desenho oficial Arduino |
| **PCA9685** | 62,5 × 25,4 mm; furos Ø2,5 com espaçamento 55,88 × 19,05 | [Adafruit 815](https://www.adafruit.com/product/815), [guia Adafruit](https://learn.adafruit.com/16-channel-pwm-servo-driver), [fórum Adafruit](https://forums.adafruit.com/viewtopic.php?f=19&t=32487) |
| **OLED 0,96" SSD1306** | área visível de 21,7 × 10,9 mm → janela de 23 × 12 mm. A placa varia de 27 a 30 mm, então vai **colada**, sem furos | [DFRobot DFR0650](https://wiki.dfrobot.com/dfr0650/), [Tinytronics](https://www.tinytronics.nl/shop/en/displays/oled/0.96-inch-oled-display-128*64-pixels-white-i2c) |
| Chave KCD1 | recorte de 19 × 12 mm (encaixe padrão; lixar se ficar justo) | anúncios de fabricantes (sem datasheet oficial) |

> Os SG90 de fabricantes diferentes variam alguns décimos de milímetro. A janela tem 0,2 mm de folga por lado. Quando os servos chegarem, **confira o SG90 com paquímetro** antes de cortar, principalmente o comprimento do corpo (22,7 mm).

## Arquitetura

| Item | Valor |
|---|---|
| Altura × largura × profundidade | 303 × 150 × 84 mm |
| Bloco | 36 × 84 mm |
| Eixo dos braços | Z = 153 mm, no meio do braço de 294 mm |
| Curso | −90° a +90° (os 180° do SG90) |
| Vão entre os blocos | 3 mm |

**Por que o eixo no meio:** o SG90 dá só 1,8 kgf·cm. Com o eixo perto do topo, o braço de cerca de 190 g exigiria quase isso. Com o eixo no meio, o braço fica equilibrado como uma gangorra, e o servo só vence atrito e aceleração: **0,28 kgf·cm, folga de 6,3×**.

**Mancal de MDF:** são 2 discos colados na lateral do corpo.
- O braço gira com o furo da lateral interna (Ø46,4) em volta do disco do eixo (Ø46).
- O disco de encosto (Ø64) segura o braço de lado.
- O peso do braço vai para o corpo, não para o eixo de plástico do SG90.
- Passe vela no mancal.

**O servo fica dentro do corpo:**
- A aba do SG90 encosta por dentro da lateral, presa com os 2 parafusos que vêm com o servo, em pré-furos de Ø1,4 que atravessam a lateral e o disco de encosto (6 mm de MDF).
- O eixo atravessa os discos até o horn duplo, que fica dentro do braço, parafusado no **anteparo** com M2.
- Antes, alargue 4 furos do horn (os de 10 e 14 mm do centro) para Ø2,1 mm.

**Caixas com encaixes dentados.** Ficam fixas e coladas a frente, as laterais, o topo e o fundo de cada caixa. Saem com parafusos:
- a **tampa traseira do corpo**, com 4 M3;
- a **tampa externa de cada braço**, com 4 M3 cada.

Os parafusos entram em reforços colados por dentro, com rasgo-T e porca.

## Verificações (`python fusion/RoboDoisBracos/projeto.py`)

```
OK  Ponte de MDF entre a janela do SG90 e o pré-furo da aba: 2.0 mm (mín. 2.0)
OK  Os dois SG90 dentro do corpo não se tocam: vão de 29.4 mm
OK  Topo do SG90 cabe na janela do disco de encosto e o ressalto no furo Ø20 do disco do eixo
OK  Horn e anteparo ficam dentro do braço (horn a 1.9 mm da lateral interna)
OK  Braço ↔ mesa em qualquer ângulo: 3.1 mm (mín. 3.0)
OK  Ombro: desequilíbrio 0.00 + aceleração 0.16 + atrito 0.12 = 0.28 kgf·cm; SG90 dá 1.8 → FS 6.3
OK  Centro de massa ↔ borda da base na pior pose: 36 mm (massa total 691 g)
OK  Uno deitado (com jumpers) e PCA9685 em pé cabem sem tocar SG90 nem reforços
OK  Janela da tela longe dos encaixes; pinos/conectores do OLED não alcançam o SG90
OK  Reforços da tampa traseira não tocam os SG90
OK  Cabo SG90 D → PCA9685 canal 0 (cabo do servo): precisa ~196 mm, tem 250 mm
OK  Cabo SG90 E → PCA9685 canal 1 (cabo do servo): precisa ~165 mm, tem 250 mm
OK  Cabo Uno A4/A5/5V/GND → PCA9685 (jumper macho-fêmea 20 cm): precisa ~80 mm, tem 200 mm
OK  Cabo PCA9685 → OLED SDA/SCL/VCC/GND (jumper fêmea-fêmea 30 cm): precisa ~225 mm, tem 300 mm
OK  Cabo Plugue da fonte → chave (fio 22 AWG 30 cm): precisa ~72 mm, tem 300 mm
OK  Cabo Chave → borne V+ do PCA9685 (fio 22 AWG 30 cm): precisa ~157 mm, tem 300 mm
OK  Todas as peças cabem na chapa 900×600
```
**Como os cabos são verificados:** o comprimento é estimado pelo caminho em "L" entre os conectores, mais 20%, mais 30 mm de sobra. Foi assim que apareceu que o **jumper de 20 cm não chega ao OLED**, e por isso a lista pede jumpers de 30 cm.

## Ligações

Todo o I²C é compartilhado: o PCA9685 fica no endereço 0x40 e o OLED no 0x3C.

| De | Para | Cabo |
|---|---|---|
| Uno A4 / A5 / 5V / GND | PCA9685 SDA / SCL / VCC / GND (conector de baixo) | 4 jumpers macho-fêmea de 20 cm |
| PCA9685 SDA / SCL / VCC / GND (conector de cima) | OLED SDA / SCL / VCC / GND | 4 jumpers fêmea-fêmea de 30 cm |
| *ou, sem soldar o 2º conector do PCA9685:* Uno SDA / SCL (ao lado do AREF), 3.3V, GND | OLED SDA / SCL / VCC / GND | 4 jumpers macho-fêmea de 30 cm |
| SG90 do braço D (+X) | PCA9685 canal 0 | cabo do servo (250 mm) |
| SG90 do braço E (−X) | PCA9685 canal 1 | cabo do servo (250 mm) |
| Bateria: 4 pilhas AA **alcalinas** no suporte (6 V), dentro do corpo | chave → borne V+/GND do PCA9685 e pino **Vin**/GND do Uno | jumpers |
| Capacitor de 470 µF | borne V+/GND do PCA9685 (respeitar a polaridade) | — |
| USB do Uno | janela na tampa traseira | cabo USB (alimenta o Uno) |

**Sem PCA9685** (`#define USAR_PCA9685 0` no `robo_bracos.ino`, o padrão atual): o sinal do servo do braço D vai no **D9** e o do braço E no **D6**; os fios vermelhos no **5V** do Uno e os marrons no **GND**. A bateria entra só no **Vin/GND** do Uno. O OLED continua no SDA/SCL. Para voltar ao PCA9685, mude para `1`.

**Onde fica cada componente:**
- **Uno:** deitado no fundo, com o USB voltado para a janela traseira.
- **PCA9685:** em pé na lateral E, metade da frente. O borne fica voltado para trás, acessível pela tampa.
- **OLED:** colado atrás da janela da frente.

Os pinos do OLED e os conectores saem cerca de 23 mm para trás e não alcançam o servo.

## Montagem

Guia completo, passo a passo e com checklist: [MONTAGEM.md](MONTAGEM.md). Roteiro de bancada para o celular: https://claude.ai/artifact/LCUTgscz8zunP4qHRRn4NE (privado; compartilhe pelo menu Share). Resumo:

1. **Cada componente sozinho**, na mesa, só com o USB: Uno, servo direito (D9), servo esquerdo (D6), OLED (A4/A5) e pilhas no multímetro. Centralize os servos com `u 0 1500` e `u 1 1500`.
2. **Teste de encaixe** de cada componente no corpo, sem ligar.
3. **Ensaio geral** fora do robô: tudo ligado, pilhas na mini protoboard (trilha + nos servos e no Vin), 5 minutos de coreografia.
4. **Montagem no corpo**, de baixo para cima: Uno, mini protoboard, servos, OLED, pilhas na tampa traseira; jumpers presos com cola quente.
5. **Braços**: horn no anteparo, braço em pé no eixo centralizado, vela no mancal.
6. **Calibrar** com `u <canal> <us>` e anotar `us0`/`us90` no sketch.

O projeto original usa um PCA9685 entre o Uno e os servos; ele continua disponível com `#define USAR_PCA9685 1` (veja a variante no fim do MONTAGEM.md).

## Pontos para testar antes da versão final

- [ ] **Encaixes:** pente de teste → kerf. Monte um canto de caixa avulso.
- [ ] **SG90 real:** medir o corpo; deve passar justo na janela. Os parafusos devem entrar firmes nos pré-furos de Ø1,4.
- [ ] **Mancal:** com vela, o braço deve girar à mão sem prender e sem folga visível.
- [ ] **Equilíbrio:** sem energia, o braço solto em qualquer ângulo deve ficar parado ou mexer pouco.
- [ ] **Cabos:** o jumper de 30 cm deve alcançar o OLED sem ficar esticado.

## Outros arquivos

- `fusion/RoboDoisBracos/RoboDoisBracos.py`: modelo 3D com juntas no Fusion (opcional, para os desenhos técnicos).
- `demo/`: demonstração 3D. Para refazer:
  ```bash
  python demo/gerar_demo.py
  ```
- `arduino/robo_bracos/robo_bracos.ino`: 2 servos + OLED + HC-05. Ao ligar, entra no **modo autônomo**: repete sozinho a `coreografia()` (9 cenas, fáceis de editar), sem notebook nem celular. Qualquer comando pausa a coreografia por 30 s; `d` liga/desliga.
