# Montagem do Robô TARS

Passo a passo para montar o robô depois do corte a laser. Leva de 2 a 3 tardes.

A ordem importa:
1. **testar cada componente sozinho**, na mesa;
2. **testar o encaixe** de cada um no corpo, sem ligar;
3. **ensaio geral**: tudo ligado junto, fora do robô, com as pilhas;
4. só então **montar dentro do robô**.

Se algo falhar, você sabe exatamente o quê. Depois de fechar o corpo, fica difícil mexer.

Este guia usa os **servos ligados direto no Uno**, sem o PCA9685 (é o padrão do código: `#define USAR_PCA9685 0`). Para montar com o PCA9685, veja [Variante com PCA9685](#variante-com-pca9685) no fim.

- Mapa das peças na chapa: https://claude.ai/artifact/1jdB73SS3mzryoovjYr6sd
- Demonstração 3D (ver como as peças se encaixam): https://claude.ai/artifact/CNWZmAH6V9aymZm9zFhAPm
- Roteiro de bancada para abrir no celular: https://claude.ai/artifact/LCUTgscz8zunP4qHRRn4NE
- Ligações e medidas: [README.md](README.md)

---

## Antes de começar

**Separe e identifique as 37 peças.** Use o mapa da chapa para saber qual é qual. Passe um pano levemente úmido para tirar a fuligem do laser das bordas.

**Monte tudo a seco primeiro, sem cola.** Encaixe as caixas para ver se os dentes entram:
- **Justo demais:** passe uma lixa fina de leve na lateral dos dentes.
- **Frouxo:** tudo bem, a cola preenche.

**Como saber a posição de cada peça:**
- **Face gravada (com o vinco) = face de fora.** Vale para a frente, a tampa traseira e o topo do corpo.
- **Laterais do corpo:** as duas são iguais. Os **4 furinhos pequenos ficam embaixo e na metade da frente** (eram para o PCA9685; servem de referência). Se a peça ficar de cabeça para baixo, a janela do servo sai do lugar.
- **Frente/trás dos braços:** os 2 rasgos do anteparo ficam mais perto da borda que encosta no corpo.

### Componentes
- Arduino Uno + cabo USB
- 2 micro servos SG90 (com os saquinhos de horns e parafusos)
- Tela OLED 0,96" I²C (4 pinos)
- Suporte para 4 pilhas AA + **4 pilhas AA alcalinas** (6 V)
- Opcional: módulo Bluetooth **HC-05** + resistores de **1 kΩ e 2 kΩ**

### Material de bancada (o laboratório costuma ter)
- **Jumpers macho-fêmea de 30 cm** (cerca de 15): o OLED fica no topo e o Uno no fundo, e jumpers de 20 cm não alcançam
- **Mini protoboard** (170 furos, ~47 × 35 mm): distribui a energia das pilhas dentro do corpo
- **Multímetro**
- Cola quente, fita dupla-face espessa, fita isolante
- Chaves de precisão, alicate de bico, lixa fina, estilete, vela comum
- Opcional: cola PVA, parafusos M2 × 8 + porcas (horn) e M3 × 12 + porcas (tampas)

### Software no notebook
1. **Arduino IDE** e, pelo *Gerenciador de Bibliotecas*:
   - *Adafruit SSD1306* (aceite instalar as dependências *Adafruit GFX* e *BusIO*)
   - a biblioteca *Servo* já vem com o IDE
2. Abra `arduino/robo_bracos/robo_bracos.ino`. Confira no topo: `#define USAR_PCA9685 0`.
3. Em *Ferramentas*: **Placa → Arduino Uno** e a **Porta** COM do Uno. Placas compatíveis podem precisar do **driver CH340**.

### Energia: o que pode e o que não pode
- As **4 pilhas AA alcalinas (6 V)** alimentam os servos **direto** e o Uno pelo pino **Vin**.
- ❌ **Nunca ligue as pilhas no pino 5V do Uno.** Novas, chegam a 6,4 V e queimam a placa.
- Pelo **Vin**, o cabo USB pode ficar ligado junto com as pilhas: o Uno escolhe sozinho a fonte.
- Bateria de 9 V não serve: não aguenta os servos.

---

## Onde cada componente fica no corpo

Por dentro, o corpo tem cerca de **66 × 78 mm de base** e **29 cm de altura**.

| Componente | Lugar |
|---|---|
| **Uno** | deitado **no fundo**, com o USB virado para a janela de baixo da tampa traseira |
| **Servos** | nas **janelas das laterais**, no meio da altura |
| **OLED** | atrás da **janela da frente**, perto do topo |
| **Mini protoboard** | em pé na **lateral esquerda** (oposta à tela), **metade da frente**, embaixo do servo |
| **Suporte de pilhas** | colado **por dentro da tampa traseira**, acima da janela do USB: ao tirar a tampa, as pilhas saem junto |
| **HC-05** (opcional) | lateral direita, abaixo do servo |

---

## Fase 1: Testar cada componente sozinho (na mesa, só com o USB, ~30 min)

Abra o **Monitor Serial** (lupa no canto do IDE) em **115200** e **Nova linha**. Teste **uma peça de cada vez**:

| # | Peça | Ligação | Teste | Passou se… |
|---|---|---|---|---|
| 1 | **Uno** | só o USB; clique em **Carregar** | aperte **RESET** | aparece `TARS ligando...`, `Servos direto no Uno...` e a lista de comandos |
| 2 | **Servo direito** | laranja → **D9**, vermelho → **5V**, marrom → **GND** | `d`, depois `j 0 45` e `a saudar` | ele gira e acena 3 vezes |
| 3 | **Servo esquerdo** | laranja → **D6**, vermelho → **5V** (o outro, ao lado do RES), marrom → **GND** | `j 1 45` | ele gira |
| 4 | **OLED** | GND → **GND**, VDD → **3.3V**, SCK → **A5**, SDA → **A4** | **RESET**, depois `t OLA` | `Tela OK` no Monitor e o texto na tela |
| 5 | **Pilhas** | só o multímetro | meça os fios do suporte | cerca de **6 V**, com o **vermelho = +** |

> O Uno tem dois pinos **5V** e três **GND** (dois na fileira POWER e um ao lado do pino 13). Pelo USB, um servo de cada vez ou os dois juntos funcionam, desde que soltos na mesa.

**Centralizar os servos (no fim do teste 3):**
1. Mande `u 0 1500` com o servo direito ligado e `u 1 1500` com o esquerdo.
2. Desligue o USB nessa posição e **não gire mais os eixos com a mão**. Os braços serão encaixados com os servos centralizados.

---

## Fase 2: Testar o encaixe (sem ligar nada, ~15 min)

Coloque cada peça no lugar dela e confira:
- [ ] **Uno no fundo:** cabe deitado, e o **USB fica alinhado** com a janela da tampa traseira.
- [ ] **Servos:** passam justos na janela; os parafusinhos do saquinho entram firmes nos pré-furos.
- [ ] **OLED:** a área preta aparece inteira pela janela da frente.
- [ ] **Mini protoboard:** cabe na lateral esquerda sem encostar no servo.
- [ ] **Suporte de pilhas na tampa traseira:** a tampa **fecha** sem bater no Uno nem nos servos.
- [ ] **Fios:** os jumpers de **30 cm** vão do OLED (topo) ao Uno (fundo) sem ficarem esticados; os cabos dos servos (25 cm) sobram.

Se algo não couber, resolva agora: é muito mais fácil do que com tudo ligado.

---

## Fase 3: Ensaio geral (tudo ligado junto, fora do robô, ~20 min)

Monte a ligação **final**, já com os jumpers do comprimento certo:

```
PILHAS (+) ──► trilha + da mini protoboard ──► vermelhos dos 2 servos
                                           └─► Vin do Uno
PILHAS (−) ──► trilha − da mini protoboard ──► marrons dos 2 servos
                                           └─► GND do Uno

Uno D9   ──► laranja do servo direito
Uno D6   ──► laranja do servo esquerdo
Uno 3.3V ──► OLED VDD      Uno GND ──► OLED GND
Uno A5   ──► OLED SCK      Uno A4  ──► OLED SDA
```

| De | Para |
|---|---|
| Pilhas **+** (vermelho) | trilha **+** da mini protoboard |
| Pilhas **−** (preto) | trilha **−** da mini protoboard |
| Trilha **+** | **vermelhos** dos 2 servos e **Vin** do Uno |
| Trilha **−** | **marrons** dos 2 servos e **GND** do Uno |
| Uno **D9** / **D6** | **laranja** do servo direito / esquerdo |
| Uno **3.3V / GND / A5 / A4** | OLED **VDD / GND / SCK / SDA** |

> ❌ A trilha **+** (6 V das pilhas) **nunca** vai no pino **5V** do Uno. Os vermelhos dos servos saem do 5V do Uno e passam para a trilha +.

1. **Sem as pilhas**, só com o USB: os 2 servos e a tela funcionam juntos? Mande `a dancar`.
2. **Tire o USB e coloque as pilhas.** O robô deve **ligar sozinho**, mostrar "TARS / HUMOR 75%" e começar a **coreografia** (modo autônomo).
3. Deixe rodando **5 minutos**. Se o Uno reiniciar (a tela volta para "HUMOR 75%" no meio de uma cena), troque as pilhas por novas.

✅ Passou? A eletrônica está aprovada. Agora é só passar para dentro do robô.

---

## Fase 4: Preparar o horn (cerca de 15 min, para cada braço)

1. Pegue o **horn duplo** (o reto, de 2 braços) que vem com o SG90.
2. Prenda o horn no **anteparo**, com o cubo sobre o furo central e a face com o encaixe do eixo virada para fora:
   - **com parafusos:** alargue com broca de 2 mm os furos a **10 mm e 14 mm do centro** (2 de cada lado) e use 4 parafusos M2 × 8 com porcas;
   - **sem parafusos:** amarre com arame fino ou abraçadeira pelos furos, ou use uma gota de super cola **só nas pontas** do horn. Não cole o furo central: o eixo precisa entrar ali.

---

## Fase 5: Corpo (cerca de 1 h, mais secagem se usar cola)

1. **Discos de encosto** (os Ø64 com janela retangular): um por fora de cada lateral.
   - Para alinhar, enfie 2 palitos finos ou clipes desdobrados pelos 2 pré-furos da lateral e do disco ao mesmo tempo.
   - As janelas retangulares precisam coincidir.
2. **Reforços do corpo** (4 plaquinhas com rasgo em T): por dentro das laterais, na borda de trás, perto dos furos da tampa traseira. Só são necessários se a tampa traseira for parafusada.
3. **Servos:** coloque cada SG90 **por dentro** da lateral, com o eixo dentro da janela e o fio saindo por baixo.
   - A aba encosta na face de dentro.
   - Prenda com os 2 parafusos que vêm com o servo, nos pré-furos. Não aperte demais.
4. **Mini protoboard:** fita dupla-face na lateral esquerda, metade da frente, embaixo do servo.
5. **Uno no fundo:** fita dupla-face ou os espaçadores M3, com o USB virado para a borda de trás.
6. **OLED:** fita dupla-face por trás da janela da frente, com os pinos para cima.
7. **Montar a caixa:** encaixe **fundo + laterais + frente + topo**. A tampa traseira fica solta até o fim.
8. **Base:** por baixo do fundo.

---

## Fase 6: Eletrônica dentro do corpo (cerca de 40 min)

1. Refaça **exatamente** as ligações da Fase 3, agora dentro do corpo.
2. **Suporte de pilhas:** fita dupla-face na face de dentro da **tampa traseira**, acima da janela do USB. Deixe os fios **com folga** para a tampa abrir.
3. **Prenda os fios:**
   - uma gota de **cola quente** na base de cada jumper, no Uno e na protoboard, para não soltarem com a vibração;
   - fita nos fios soltos, longe dos servos.
4. Confira se o **USB do Uno** está alinhado com a janela de baixo da tampa traseira.
5. **Teste antes de fechar:** coloque as pilhas e veja a coreografia funcionando.
6. Feche a tampa traseira.

---

## Fase 7: Braços (cerca de 1 h para os dois)

Para cada braço:

1. Monte a caixa a seco, ainda sem a tampa externa (a lateral com 4 furos nos cantos):
   - 2 peças de frente/trás;
   - a lateral interna, com o furo grande;
   - topo e fundo;
   - o **anteparo com o horn** encaixado nos 2 rasgos, com o **horn virado para a lateral interna** (o lado do furo grande).
2. **Reforços do braço** (4 por braço, opcionais se a tampa não for parafusada): por dentro, na frente e atrás, perto da borda da tampa, em cima e embaixo.
3. Feche a caixa, menos a tampa externa.

---

## Fase 8: Encaixar os braços no corpo (cerca de 30 min)

1. **Lubrifique** o furo grande da lateral interna do braço e a borda do disco do eixo (Ø46) com vela.
2. **Disco do eixo (Ø46 com furo central):** o braço centraliza esse disco sozinho.
   - Coloque o disco dentro do furo grande do braço.
   - Encaixe o braço no robô: o **eixo do servo entra no horn**, com o braço **em pé, alinhado com o corpo** (os servos estão centralizados desde a Fase 1).
   - Pelo furo central do anteparo, com o braço ainda aberto, aperte o **parafuso pequeno do horn** no eixo (vem no saquinho do SG90).
   - Se for colar o disco do eixo no disco de encosto, use **pouca** cola só no verso e não mexa no braço por 1 h.
3. Com as pilhas **fora**, gire o braço com a mão, **bem devagar**. Ele deve girar sem prender. Se raspar, passe mais vela.
4. Feche a tampa externa do braço. Repita para o outro braço.

---

## Fase 9: Calibrar e testar (cerca de 30 min)

1. Ligue o cabo USB e as pilhas. No Monitor Serial (o primeiro `u` desliga o modo autônomo):
   - mande `u 0 1500`: o braço direito deve ficar em pé, alinhado com o corpo;
   - procure com `u 0 <valor>` o pulso em que o braço fica **em pé** e o pulso em que fica **deitado para a frente** (90°), algo entre 550 e 2450;
   - faça o mesmo com o canal 1.
2. Anote os valores no sketch, na tabela `juntas[]`: `us0` é o braço em pé e `us90` é o braço à frente. Carregue de novo.
3. Teste com `j 0 45`, `j 1 -45` e assim por diante. Os braços devem ir para os ângulos pedidos, de −90° a +90°.
4. **Coreografia (modo autônomo):** já vem pronta em `coreografia()`, com 9 cenas curtas (saudar, caminhar, "modo roda", dança, piada, frase do filme...). Para mudar, edite as cenas. Ela começa sozinha ao ligar o robô. Qualquer comando a pausa por 30 s, e `d` a liga ou desliga.
5. Teste as ações: `a saudar`, `a dancar`, `a sim`, `a nao`, `t OLA TURMA`.
6. Desligue o cabo USB. Daqui em diante o robô funciona sem cabo: sozinho (modo autônomo) ou pelo Bluetooth.

**Teste final:**
- [ ] Ao colocar as pilhas, ele faz a coreografia sozinho.
- [ ] Os braços giram sem raspar.
- [ ] A tela mostra os textos.
- [ ] Funciona 5 minutos só com as pilhas.

### Comandos do Monitor Serial (e do Bluetooth)

| Comando | O que faz | Exemplo |
|---|---|---|
| `a <ação>` | executa uma ação: saudar, dancar, feliz, triste, sim, nao, pensar, repouso | `a saudar` |
| `t <texto>` | escreve na tela | `t OLA TURMA` |
| `u <canal> <us>` | pulso bruto no servo (para calibrar) | `u 0 1500` |
| `j <braço> <graus>` | move um braço dentro dos limites (−90 a 90) | `j 1 45` |
| `d` | liga ou desliga o modo autônomo (coreografia) | `d` |

### Mensagens do Monitor Serial ao ligar

| Mensagem | Significado |
|---|---|
| `Servos direto no Uno: D9 = braco D, D6 = braco E` | modo sem PCA9685 ativo |
| `Tela OK` / `Tela nao encontrada (0x3C)` | o OLED respondeu ou não; confira SDA/SCL e VDD/GND |
| `ERRO: SDA (A4) preso em 0` / `ERRO: SCL (A5) preso em 0` | esse fio está encostado no GND ou no pino errado |

---

## Fase 10: Bluetooth e comando de voz (opcional, cerca de 1 h)

Como funciona: o **notebook** ouve a voz, pergunta à IA (LLM local no **Ollama**), fala a resposta em voz alta e manda uma ação para o robô pelo **Bluetooth**. O robô mexe os braços e mostra o texto na tela. O código do Arduino já escuta o HC-05; não é preciso mudar nada nele.

```
voz → notebook (reconhecimento) → Ollama (IA) → resposta falada
                                               └→ Bluetooth → HC-05 → Arduino → braços + tela
```

### Ligar o HC-05
| HC-05 | Uno |
|---|---|
| **VCC** | **5V** (livre, porque os servos estão na trilha das pilhas) |
| **GND** | **GND** ao lado do pino 13 |
| **TXD** | **D10** |
| **RXD** | **D11 → resistor 1 kΩ → RXD**, e do RXD um **resistor 2 kΩ → GND** (divisor: protege o HC-05, que é de 3,3 V) |

Cole o HC-05 com fita dupla-face na face de dentro da lateral direita, abaixo do servo.

### Instalar no notebook
1. **Ollama:** instale pelo site ollama.com e baixe o modelo (uma vez só, cerca de 2 GB):
   ```bash
   ollama pull llama3.2:3b
   ```
   Se o notebook for lento, use `llama3.2:1b`. Se o CP4 usa outro modelo, troque `MODELO` no topo de `ia/tars.py`.
2. **Bibliotecas Python** (use Python 3.11 ou 3.12), a partir da pasta do projeto:
   ```bash
   pip install -r ia/requirements.txt
   ```
   São elas: `pyserial` (Bluetooth), `SpeechRecognition` e `pyaudio` (microfone), `pyttsx3` (voz).
3. Confira se está tudo certo, sem robô e sem microfone. Deve aparecer `autoteste ok`:
   ```bash
   python ia/tars.py --teste
   ```

### Parear o Bluetooth
1. Ligue o robô. O LED do HC-05 pisca **rápido**: ele está esperando conexão.
2. No Windows: **Configurações → Bluetooth e dispositivos → Adicionar dispositivo → Bluetooth → HC-05**. Senha: **1234** (alguns usam **0000**).
3. Descubra a porta: **Mais configurações de Bluetooth → aba Portas COM**. Anote a porta marcada como **"De saída"** (ex.: **COM5**). É ela que o programa usa.

### Testar em etapas
Só passe para a próxima etapa quando a anterior funcionar:

1. **IA sem robô**, digitando. Mostra a resposta e o comando que seria enviado:
   ```bash
   python ia/tars.py --sem-robo --teclado
   ```
2. **Robô pelo Bluetooth**, digitando. Troque COM5 pela sua porta. Digite "Oi, TARS": o robô deve acenar e mostrar a resposta na tela. O LED do HC-05 passa a piscar **devagar** (conectado):
   ```bash
   python ia/tars.py --porta COM5 --teclado
   ```
3. **Diagnóstico completo.** Mostra OK ou FALHA para cada item (Ollama, IA, voz em português, microfone, internet, Bluetooth, robô):
   ```bash
   python ia/tars.py --porta COM5 --diagnostico
   ```
4. **Tudo com voz:**
   ```bash
   python ia/tars.py --porta COM5
   ```
   Fale perto do microfone. A tela mostra **OUVINDO… → PENSANDO… → a resposta**, o notebook fala e os braços fazem a ação. Diga **"desligar"** para encerrar.

### Frases que disparam ações
| Diga | O robô faz |
|---|---|
| "Oi, TARS" / "Bom dia" / "Tchau" | acena (**sempre**, mesmo se a IA falhar) |
| "Dança pra gente" | passada alternada (**sempre**) |
| "Parabéns" / "Mandou bem" | comemora (**sempre**) |
| Qualquer outra pergunta | a IA responde e escolhe: sim, não, feliz, triste ou repouso |

Para mudar o jeito do TARS falar, edite o texto `PERSONALIDADE` em `ia/tars.py`. Para usar o script de voz do CP4 no lugar do `tars.py`, veja [CP5.md](CP5.md).

> **Reconhecimento de voz:** o `tars.py` usa o do Google, que **precisa de internet**. Para funcionar sem internet, baixe o modelo **vosk-model-small-pt-0.3** (alphacephei.com/vosk/models), descompacte em `ia/` e rode com `--vosk ia/vosk-model-small-pt-0.3`.

---

## Fase 11 (opcional): Pintura no estilo do filme

Pinte **depois** de tudo montado e testado, porque a cola não pega bem em tinta. Use primer e cinza grafite fosco em spray. **Proteja com fita** a janela da tela, os furos da tampa traseira e o vão entre corpo e braços, para a tinta não travar o mancal.

---

## Variante com PCA9685

O projeto original usa um driver **PCA9685** entre o Uno e os servos. Ele só vale a pena com **jumpers bons**: com fios improvisados, o contato no I²C falha e os servos não respondem.

1. No topo do `robo_bracos.ino`, troque para `#define USAR_PCA9685 1` e instale também a *Adafruit PWM Servo Driver Library*.
2. Ligações:

   | De | Para |
   |---|---|
   | Uno **A4 / A5 / 5V / GND** | PCA9685 **SDA / SCL / VCC / GND** |
   | Uno **SDA / SCL** (ao lado do AREF), **3.3V**, **GND** | OLED **SDA / SCK / VDD / GND** |
   | Servo direito / esquerdo | PCA9685 **canal 0 / 1** (marrom na fileira preta, GND) |
   | Pilhas + / − | **borne verde** do PCA9685, **V+ / GND** (tem proteção contra inversão) e **Vin / GND** do Uno |

3. Ao ligar, o Monitor Serial deve mostrar **`PCA9685 OK`**. Se mostrar `PCA9685 nao encontrado (0x40)`, o contato do SDA, SCL ou GND está ruim.
4. ❌ **Não ligue as pilhas nos pinos V+/GND das colunas dos servos:** eles não têm proteção, e um fio invertido ou encostado desliga a placa.
5. O PCA9685 vai em pé na lateral esquerda, nos 4 furinhos, no lugar da mini protoboard.

---

## Problemas comuns

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Monitor Serial mostra `⸮⸮⸮` ou caracteres estranhos | velocidade errada | ajuste para **115200** |
| Comandos não respondem | final de linha errado | ajuste para **Nova linha** |
| `Missing FQBN` ao compilar | placa não selecionada | *Ferramentas → Placa → Arduino Uno* |
| O Uno não aparece nas portas | falta o driver | instale o driver **CH340** |
| Tela apagada | fio trocado | confira SDA → A4 e SCK → A5; o Monitor avisa `Tela nao encontrada` |
| Servo não mexe | sinal no pino errado ou sem energia | laranja no **D9/D6**; vermelho na trilha + (ou no 5V, só com USB); marrom no GND |
| Servo treme ou o Arduino reinicia | falta de corrente | pilhas novas (troque as 4 juntas); confira as emendas da trilha + e − |
| Braço vai para trás em vez de para a frente | sentido invertido | troque o lado do `us90` na tabela `juntas[]` |
| Braço trava no meio do giro | disco do eixo descentralizado ou cola no mancal | passe vela; se não resolver, lixe de leve a borda do disco Ø46 |
| Encaixe muito frouxo | kerf diferente do previsto | cola PVA preenche folgas pequenas |
| Encaixe não entra | kerf menor que o previsto ou MDF mais grosso | lixe de leve a lateral dos dentes |
| HC-05 não aparece no Windows | robô desligado ou HC-05 sem energia | o LED do HC-05 tem que piscar |
| `tars.py` não abre a porta COM | porta errada ou outro programa usando | use a porta **"De saída"**; feche o Monitor Serial da Arduino IDE |
| Robô não reage pelo Bluetooth | TXD/RXD trocados ou sem o divisor | HC-05 **TXD → D10**; **D11 → 1 kΩ → RXD**; RXD → 2 kΩ → GND |
| "Perdi a conexão com o meu cérebro" | Ollama fechado ou modelo não baixado | abra o Ollama; confira com `ollama list` |
| Não entende a voz | barulho, microfone longe ou sem internet | fale perto do microfone; teste com `--teclado` |
| Voz em inglês | Windows sem voz em português | Configurações → Hora e idioma → Fala → adicionar voz Português (Brasil) |

---

## Checklist

- [ ] Peças identificadas e montadas a seco
- [ ] Fase 1: Uno, servo direito, servo esquerdo, OLED e pilhas testados um a um
- [ ] Servos centralizados (`u 0 1500` / `u 1 1500`)
- [ ] Fase 2: todos os componentes cabem no corpo e a tampa traseira fecha
- [ ] Fase 3: ensaio geral com as pilhas, 5 minutos de coreografia sem reiniciar
- [ ] Horns presos nos anteparos
- [ ] Servos, mini protoboard, Uno e OLED instalados no corpo
- [ ] Ligações refeitas dentro do corpo, jumpers presos com cola quente, testadas antes de fechar
- [ ] Braços montados, giram livres à mão; tampas fechadas
- [ ] Servos calibrados (`us0` / `us90`) e coreografia pronta
- [ ] (Opcional) HC-05 ligado com o divisor de tensão, pareado, `tars.py` respondendo
