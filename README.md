# Robô TARS

Robô de mesa inspirado no TARS, de *Interestelar*. São 4 blocos de MDF lado a lado, como no filme: os 2 do meio formam o corpo e os 2 de fora são os braços, cada um movido por um micro servo. Uma tela OLED na frente mostra o que ele está pensando e falando.

O TARS conversa por voz:
1. Você fala com ele.
2. O notebook entende a frase e uma IA que roda no próprio notebook escolhe a resposta.
3. O notebook fala a resposta com uma voz natural.
4. Ao mesmo tempo, o robô mexe os braços e escreve a resposta na tela.

Ligado só nas pilhas, sem notebook, ele faz uma coreografia sozinho.

**Estado atual:** o robô está montado dentro do corpo e funciona com o cabo USB ligado ao notebook. Já funcionam a conversa por voz, os 13 gestos, a voz da ElevenLabs, a risada nas piadas e o modo autônomo nas pilhas. Faltam ajustes físicos: firmar a junção braço–servo e calibrar os servos (`us0`/`us90`).

- **Para apresentar:** [APRESENTACAO.md](APRESENTACAO.md) (texto e roteiro) e [CP5.md](CP5.md) (critérios, plano B e checklist do dia).
- **Para ligar e usar:** [versao_final/README.md](versao_final/README.md).
- **Para montar:** [MONTAGEM.md](MONTAGEM.md).

## Como funciona

```
  você fala ──► microfone do notebook
                    │
                    ▼
        reconhecimento de voz (Google; ou Vosk, sem internet)
                    │  "Oi, TARS, conta uma piada"
                    ▼
        falas do filme e palavras-chave ──► resposta na hora
                    │  (o resto)
                    ▼
        IA local no Ollama (llama3.2:3b) ──► {"fala": "...", "acao": "piada"}
                    │
          ┌─────────┴──────────────────────────────┐
          ▼                                        ▼
  voz do TARS (ElevenLabs;              cabo USB ──► Arduino Uno
  reserva: Microsoft e Windows)                      ├─► PCA9685 ──► 2 × SG90 (braços)
          │                                          └─► OLED (OUVINDO… / PENSANDO… / resposta)
          ▼
  alto-falante do notebook
```

A voz é gerada **antes** de o gesto ser enviado, para os braços e a fala começarem juntos. Nas piadas, o TARS conta a piada parado e, no fim, ri: a tela pisca (a "luz de piada" do filme) e os braços balançam.

## O que tem no repositório

| Pasta / arquivo | O que é |
|---|---|
| [`versao_final/`](versao_final/README.md) | **código da apresentação**: `arduino/tars_ia/tars_ia.ino` (Arduino) e `ia/tars.py` com os `.bat` de clique duplo (notebook, Windows) |
| [`APRESENTACAO.md`](APRESENTACAO.md) | texto para explicar o projeto, dividido por apresentador |
| [`CP5.md`](CP5.md) | critérios da avaliação, roteiro de 10 min, frases da demonstração, plano B |
| [`MONTAGEM.md`](MONTAGEM.md) | montagem passo a passo, do teste de cada peça ao robô fechado |
| [`FUSION.md`](FUSION.md) | guia de modelagem no Fusion 360 |
| `fusion/RoboDoisBracos/` | `projeto.py` (todas as medidas e verificações do projeto) e o modelo 3D com juntas no Fusion |
| `laser/` | arquivos de corte (DXF) para o técnico do laser |
| `arduino/robo_bracos/` e `ia/` | versão de teste usada na bancada (servos direto no Uno ou no PCA9685) |
| `arduino/tinkercad/` | versão para simular no Tinkercad ([TINKERCAD.md](arduino/tinkercad/TINKERCAD.md)) |
| `demo/` | demonstração 3D interativa (`python demo/gerar_demo.py`) |

## Hardware

| Componente | Função |
|---|---|
| Arduino Uno (clone com chip CH340) | recebe os comandos pelo USB e controla o resto |
| PCA9685 (endereço I²C 0x40) | gera o sinal dos servos e distribui a energia das pilhas para eles |
| 2 × micro servo SG90 | um em cada braço, de −90° a +90° |
| OLED 0,96" SSD1306 (I²C 0x3C) | mostra o estado, as respostas e a "luz de piada" |
| 4 pilhas AA alcalinas (6 V) no suporte | movem os servos e alimentam o Uno pelo Vin |
| Notebook Windows | microfone, IA (Ollama), voz e alto-falante |
| Corpo em MDF 3 mm, corte a laser | 37 peças, 303 × 150 × 84 mm, cerca de 690 g |

### Ligações (montagem atual)

| De | Para |
|---|---|
| Uno **A4 / A5 / 5V / GND** | PCA9685 **SDA / SCL / VCC / GND** |
| Uno **SDA / SCL** (ao lado do AREF), **3.3V**, **GND** | OLED **SDA / SCK / VDD / GND** |
| Servo do braço direito / esquerdo | PCA9685 **canal 0 / 1** (fio marrom na fileira GND) |
| Pilhas **+ / −** | **borne verde V+ / GND** do PCA9685 (se os servos não mexem, confira a polaridade) |
| Borne **V+** | Uno **Vin** (jumper) |
| Cabo USB do notebook | USB do Uno (janela da tampa traseira) |

❌ Nunca ligue as pilhas no pino **5V** do Uno. O HC-05 (Bluetooth) é opcional: o projeto usa o cabo USB. As ligações do HC-05 estão em [versao_final/README.md](versao_final/README.md#bluetooth-opcional).

## Projeto mecânico

Demonstração 3D interativa: https://claude.ai/artifact/CNWZmAH6V9aymZm9zFhAPm (privada; compartilhe pelo menu Share). Encaixe do braço em 3D: https://claude.ai/artifact/54J58Fm5kRra3gw5K6yQXq.

### Para o técnico do laser → pasta `laser/`

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

### Medidas dos componentes (de onde vieram)

| Componente | Medidas usadas | Fonte |
|---|---|---|
| **SG90** | corpo 22,7 × 12,1 × 22,7 mm; abas de 32,4 mm, 2,4 mm de espessura, a 15,9 mm da base; furos Ø2,2 a 1,9 mm da ponta das abas; eixo a 5,8 mm da ponta do corpo; topo do eixo a 30,7 mm; 1,8 kgf·cm; 250 mm de cabo | desenho "SG90 Servo - Dimensions", [Aus Electronics Direct TA0132](https://www.auselectronicsdirect.com.au/assets/brochures/TA0132.pdf) |
| Horn duplo do SG90 | 32 mm, cubo Ø6,9, braço de 1,5 mm, furos a 4–14 mm do centro | mesmo documento, p. 5 |
| **Arduino Uno R3** | 68,58 × 53,34 mm; furos (13,97; 2,54), (15,24; 50,8), (66,04; 7,62), (66,04; 35,56) | desenho oficial Arduino |
| **PCA9685** | 62,5 × 25,4 mm; furos Ø2,5 com espaçamento 55,88 × 19,05 | [Adafruit 815](https://www.adafruit.com/product/815), [guia Adafruit](https://learn.adafruit.com/16-channel-pwm-servo-driver), [fórum Adafruit](https://forums.adafruit.com/viewtopic.php?f=19&t=32487) |
| **OLED 0,96" SSD1306** | área visível de 21,7 × 10,9 mm → janela de 23 × 12 mm. A placa varia de 27 a 30 mm, então vai **colada**, sem furos | [DFRobot DFR0650](https://wiki.dfrobot.com/dfr0650/), [Tinytronics](https://www.tinytronics.nl/shop/en/displays/oled/0.96-inch-oled-display-128*64-pixels-white-i2c) |
| Chave KCD1 | recorte de 19 × 12 mm (encaixe padrão; lixar se ficar justo) | anúncios de fabricantes (sem datasheet oficial) |

> Os SG90 de fabricantes diferentes variam alguns décimos de milímetro. A janela tem 0,2 mm de folga por lado. Quando os servos chegarem, **confira o SG90 com paquímetro** antes de cortar, principalmente o comprimento do corpo (22,7 mm).

### Arquitetura

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

### Verificações (`python fusion/RoboDoisBracos/projeto.py`)

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

## Montagem

O guia completo, com checklist, está em [MONTAGEM.md](MONTAGEM.md). O roteiro de bancada para o celular está em https://claude.ai/artifact/LCUTgscz8zunP4qHRRn4NE. Resumo da ordem que deu certo:

1. **Cada componente sozinho**, na mesa, só com o USB: Uno, cada servo, OLED.
2. **Teste de encaixe** de cada componente no corpo, sem ligar.
3. **Ensaio geral** fora do robô, com as pilhas: coreografia por alguns minutos.
4. **Montagem no corpo**: Uno deitado no fundo, PCA9685 em pé na lateral, OLED atrás da janela da frente, pilhas acessíveis pela tampa traseira.
5. **Braços**: com o servo centralizado (`a repouso`), encaixe o braço em pé.
6. **Calibrar** com `u <canal> <us>` e anotar `us0`/`us90` na tabela `juntas[]` do `tars_ia.ino`.

## Pendências

- [ ] **Braço com folga:** prender o horn no eixo com o parafuso pequeno do SG90 e o braço no horn. Se faltarem os discos do mancal, usar um anel de papelão ou EVA entre o braço e o corpo (veja [MONTAGEM.md](MONTAGEM.md#problemas-comuns)).
- [ ] **Calibração** dos dois servos (`us0` / `us90`).
- [ ] **Ensaio da apresentação** na sala, com `3_diagnostico.bat` sem nenhuma FALHA.
