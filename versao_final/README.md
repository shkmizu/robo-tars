# TARS — versão final (IA + Bluetooth)

Código para a apresentação: o robô conversa com a IA do notebook pelo **Bluetooth HC-05** (ou pelo cabo USB) e, sem notebook, faz a coreografia sozinho.

A versão de teste continua em `arduino/robo_bracos/` e `ia/tars.py`, sem mudanças.

| Pasta | O que é |
|---|---|
| `arduino/tars_ia/tars_ia.ino` | programa do Arduino (servos no PCA9685, tela OLED, HC-05) |
| `ia/tars.py` | programa do notebook: ouve, pergunta à IA (Ollama), fala e manda o robô agir |
| `ia/requirements.txt` | bibliotecas Python |

## O que muda em relação à versão de teste

| | Teste (`robo_bracos`) | Final (`tars_ia`) |
|---|---|---|
| Coreografia enquanto a IA ouve | volta sozinha depois de 30 s sem comando | fica **desligada** durante a conversa (comando `m 0`) |
| Ao sair do `tars.py` ("desligar" ou Ctrl+C) | nada muda | o robô **volta à coreografia** (`m 1`) |
| Novo comando | — | `m 0` / `m 1`: modo autônomo desligado / ligado |

Sem o notebook, os dois funcionam igual: ao ligar as pilhas, o robô faz a coreografia sozinho.

## Ligações (montagem final)

| De | Para |
|---|---|
| Uno **A4 / A5 / 5V / GND** | PCA9685 **SDA / SCL / VCC / GND** (conector de pinos dobrados) |
| Uno **SDA / SCL** (os 2 pinos ao lado do AREF), **3.3V**, **GND** | OLED **SDA / SCK / VDD / GND** |
| Servo braço direito / esquerdo | PCA9685 **canal 0 / 1** (marrom na fileira preta, GND) |
| Pilhas **+ / −** | **borne verde V+ / GND** do PCA9685 (confira o "V+": se os servos não mexem, inverta) |
| Borne **V+** (junto com o fio das pilhas) | Uno **Vin** (jumper macho-macho) |
| HC-05 **+5V / GND / TX** | Uno **5V** (ao lado do RES) / **GND** / **D10** |
| Uno **D11** → **1 kΩ** → HC-05 **RX** | e do RX → **2 kΩ** → **GND** (o RX do HC-05 é de 3,3 V) |

❌ Nunca ligue as pilhas no pino **5V** do Uno.

## Carregar no Arduino

1. Arduino IDE → *Gerenciar Bibliotecas*: **Adafruit PWM Servo Driver Library** e **Adafruit SSD1306** (com as dependências).
2. Abra `versao_final/arduino/tars_ia/tars_ia.ino`.
3. Calibração: copie para a tabela `juntas[]` os valores `us0` / `us90` que vocês acharam com a versão de teste.
4. *Placa: Arduino Uno*, porta COM do Uno → **Carregar**.
5. Monitor Serial (115200, Nova linha) → RESET: deve aparecer `PCA9685 OK` e `Tela OK`.

## Preparar o notebook (Windows)

1. **Ollama** (ollama.com) e o modelo: `ollama pull llama3.2:3b`
2. **Python 3.11 ou 3.12**, e na pasta `versao_final/ia`:
   ```
   pip install -r requirements.txt
   python tars.py --teste
   ```
   Deve aparecer `autoteste ok`.
3. **Voz em português:** Configurações → Hora e idioma → Fala → Português (Brasil).
4. **Parear o HC-05:** Configurações → Bluetooth → Adicionar dispositivo → **HC-05**, senha **1234** (ou 0000). Em *Mais configurações de Bluetooth → Portas COM*, anote a porta **"De saída"** (ex.: COM5).

## Pelo cabo USB, sem Bluetooth (o mais simples)

O HC-05 é opcional: pelo cabo USB a IA comanda o robô do mesmo jeito.
1. Ligue o cabo USB do notebook no Uno (pela janela da tampa traseira). As pilhas continuam no borne verde: elas movem os servos.
2. Descubra a porta: Arduino IDE → *Ferramentas → Porta*, ou Gerenciador de Dispositivos → *Portas (COM e LPT)* → "USB-SERIAL CH340 (COM3)".
3. Feche o Monitor Serial e rode, na pasta `versao_final/ia`, trocando COM3 pela sua porta:
   ```
   python tars.py --porta COM3 --baud 115200 --teclado
   python tars.py --porta COM3 --baud 115200
   ```
   O `--baud 115200` é obrigatório no cabo. Ao abrir a porta o Uno reinicia; o `tars.py` já espera 2 s por isso.

## Usar

Feche o Monitor Serial do Arduino IDE antes (ele ocupa a porta). Na pasta `versao_final/ia`:

| Para | Comando |
|---|---|
| Testar a IA sem robô | `python tars.py --sem-robo --teclado` |
| Robô pelo Bluetooth, digitando | `python tars.py --porta COM5 --teclado` |
| Conferir tudo antes de apresentar | `python tars.py --porta COM5 --diagnostico` |
| **Apresentação, por voz** | `python tars.py --porta COM5` |
| Plano B: pelo cabo USB | `python tars.py --porta COM3 --baud 115200` (COM3 = porta do cabo) |
| Sem internet | acrescente `--vosk vosk-model-small-pt-0.3` (modelo em alphacephei.com/vosk/models) |

Na conversa, a tela mostra **OUVINDO… → PENSANDO… → a resposta**, o notebook fala e os braços fazem a ação. "Oi, TARS" sempre acena, "Dança pra gente" sempre dança e "Parabéns" sempre comemora, mesmo se a IA falhar. Diga **"desligar"** para encerrar: o robô volta à coreografia.

Para mudar o jeito do TARS falar, edite `PERSONALIDADE` no topo de `ia/tars.py`.
