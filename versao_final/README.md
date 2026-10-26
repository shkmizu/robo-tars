# TARS — versão final (apresentação)

O robô conversa com a IA do notebook pelo **cabo USB**:
- o notebook ouve, pensa (Ollama) e fala com a voz do TARS;
- o robô mexe os braços e mostra a resposta na tela;
- sem o notebook, ligado só nas pilhas, ele faz a coreografia sozinho.

| Arquivo | O que é |
|---|---|
| `arduino/tars_ia/tars_ia.ino` | programa do Arduino: servos no PCA9685, tela OLED, 13 gestos, coreografia |
| `ia/tars.py` | programa do notebook: ouve, pergunta à IA, fala e manda o robô agir |
| `ia/1_instalar.bat` … `ia/5_escolher_voz.bat` | atalhos de clique duplo para o Windows |
| `ia/requirements.txt` | bibliotecas Python |

A versão de teste, usada na bancada, continua em `arduino/robo_bracos/` e `ia/` na raiz do repositório.

## Ligações

| De | Para |
|---|---|
| Uno **A4 / A5 / 5V / GND** | PCA9685 **SDA / SCL / VCC / GND** |
| Uno **SDA / SCL** (os 2 pinos ao lado do AREF), **3.3V**, **GND** | OLED **SDA / SCK / VDD / GND** |
| Servo do braço direito / esquerdo | PCA9685 **canal 0 / 1** (marrom na fileira preta, GND) |
| Pilhas **+ / −** | **borne verde V+ / GND** do PCA9685 (se os servos não mexem, inverta) |
| Borne **V+** (junto com o fio das pilhas) | Uno **Vin** (jumper macho-macho) |
| Notebook | USB do Uno, pela janela da tampa traseira |

❌ Nunca ligue as pilhas no pino **5V** do Uno. As pilhas movem os servos. O cabo USB pode ficar ligado junto com elas.

## 1. Carregar o programa no Arduino

1. Arduino IDE → *Gerenciar Bibliotecas*: instale **Adafruit PWM Servo Driver Library** e **Adafruit SSD1306** (aceite as dependências).
2. Abra `versao_final/arduino/tars_ia/tars_ia.ino`.
3. **Calibração:** na tabela `juntas[]`, coloque os valores `us0` (braço em pé) e `us90` (braço à frente) de cada servo.
4. *Ferramentas → Placa: Arduino Uno*, escolha a porta do Uno e clique em **Carregar**.
5. Abra o Monitor Serial (115200, Nova linha) e aperte RESET: deve aparecer `PCA9685 OK` e `Tela OK`.
6. **Feche o Arduino IDE** antes de usar a IA, porque o Monitor Serial ocupa a porta.

## 2. Preparar o notebook (Windows, uma vez)

1. **Baixar o código:** https://github.com/shkmizu/robo-tars/archive/refs/heads/claude/relaxed-lamport-gdcxxg.zip
   - Descompacte o ZIP.
   - O código está no branch `claude/relaxed-lamport-gdcxxg`. No GitHub, troque para esse branch e use *Code → Download ZIP*.
2. **Python 3.12:** https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
   - Na instalação, marque **"Add python.exe to PATH"**.
   - Tem que ser o 3.12 (ou 3.11): no Python mais novo, o `pyaudio` (microfone) não instala.
   - Se já tiver outro Python, pode manter: os `.bat` escolhem o 3.12 sozinhos.
3. **Ollama** (ollama.com/download): é o programa que roda a IA no próprio notebook.
4. Na pasta `versao_final/ia`, dê clique duplo nos arquivos, nesta ordem:

| Arquivo | O que faz |
|---|---|
| `1_instalar.bat` | instala as bibliotecas e baixa a IA (cerca de 2 GB, só na primeira vez). No fim deve aparecer `autoteste ok` |
| `5_escolher_voz.bat` | ouve e escolhe a voz do TARS (veja [Voz](#voz-do-tars)) |
| `2_testar_digitando.bat` | conversa **digitando**, com o robô no USB |
| `3_diagnostico.bat` | confere IA, voz, microfone, internet e robô: tudo tem que dar **OK** |
| `4_conversar_por_voz.bat` | **apresentação**: conversa por voz |

Os `.bat` acham sozinhos a porta do Uno (`--porta auto`) e usam a velocidade do cabo (`--baud 115200`).

## 3. Conversar

A tela do robô mostra **OUVINDO… → PENSANDO… → a resposta**. Ao mesmo tempo, o notebook fala e os braços fazem o gesto. A voz é gerada antes de o gesto ser enviado, para os dois começarem juntos. Diga **"desligar"** para encerrar: o robô volta à coreografia.

Durante a conversa, a coreografia fica desligada (comando `m 0`), para os servos não fazerem barulho perto do microfone. Ao sair, ela volta (`m 1`), inclusive com Ctrl+C.

### Frases garantidas (respondem mesmo se a IA falhar)

| Diga | O TARS faz |
|---|---|
| "Oi, TARS" / "Bom dia" / "Tchau" | acena |
| "Dança pra gente" | dança |
| "Parabéns" / "Mandou bem" | comemora |
| "Caminhe" / "Anda" | **andar**: balança os blocos como no filme |
| "Rola" / "Modo roda" | **roda**: os blocos giram juntos |
| "Conta uma piada" | conta a piada **parado** e, no fim, faz o gesto **piada**: a tela pisca (a "luz de piada" do filme), os braços balançam e ele **ri** |

### Falas do filme e ajustes (respondem na hora, sem esperar a IA)

| Diga | O TARS faz |
|---|---|
| "Ajuste o humor para 60%" | muda o humor da IA e mostra `HUMOR 60%` na tela. Com 0% ele fica sério; com 100%, faz piada em tudo. A partir de 90%, "providencia a luz de piada" |
| "Honestidade 100 por cento" | muda a honestidade da IA |
| "Qual o seu nível de humor?" | informa o ajuste atual |
| "Quem é você?" / "Se apresente" | apresentação do TARS |
| "Você está brincando?" | explica a luz de piada, piscando a tela |
| "Isso não é possível" | "Não. É necessário." |
| "Posso confiar em você?" | "Honestidade em 90 por cento. Os outros 10 são diplomacia." |
| "Qual sua missão?" | "Ajudar a humanidade. E fazer piadas sobre ela no caminho." |

Qualquer outra frase vai para a IA, que responde em até 2 frases curtas e escolhe um dos 13 gestos. Para mudar o jeito do TARS, edite `PERSONALIDADE` no topo de `ia/tars.py`. Para criar falas fixas, edite a lista `FILME`.

## Voz do TARS

`5_escolher_voz.bat` (ou `python tars.py --escolher-voz`):
- digite um número para ouvir a amostra;
- digite `g` + número (ex.: `g7`) para gravar a escolha;
- a escolha fica em `ia/voz.txt`, só neste notebook.

O grupo usa a **7**.

| Nº | Voz | Observação |
|---|---|---|
| 1 | Microsoft Antonio, brasileira | grátis, padrão se nada for gravado |
| 2 | Microsoft Francisca, brasileira | grátis |
| 3 | Microsoft Thalita, brasileira | grátis, mais expressiva |
| 4 | Microsoft Andrew, multilíngue | grátis, bem natural, leve sotaque |
| 5 | Microsoft Brian, multilíngue | grátis, descontraída |
| 6 | Microsoft Ava, multilíngue | grátis |
| **7** | **ElevenLabs Brian**, multilíngue | **a do grupo**, funciona no plano grátis |
| 8–11 | ElevenLabs Talis, Fabio Oliveira, Thiago Morais, Sávio (brasileiras) | vozes da biblioteca: pela API exigem plano pago (Starter) |

**ElevenLabs:**
- **Chave:** em elevenlabs.io, vá em *Developers → API Keys* e crie uma chave com permissão de *Text to Speech*. Na primeira vez que você escolher uma voz [ElevenLabs], o `5_escolher_voz.bat` pede a chave e a guarda em `ia/elevenlabs_chave.txt`, que **não vai para o GitHub**.
- **Créditos:** o plano grátis dá cerca de 10 mil caracteres por mês.
- **Modelos:** as falas usam o modelo `eleven_flash_v2_5`, o mais rápido. A risada das piadas usa o `eleven_v3`, que entende `[laughs]`. Ela é gerada uma vez por conversa e reaproveitada. As opções ficam no topo de `ia/tars.py`:
  - `ELEVEN_MODELO = 'eleven_multilingual_v2'`: voz mais natural, mas começa a falar mais devagar;
  - `RISADA = ''`: desliga a risada.
- A fala começa a tocar **enquanto ainda está chegando**, sem esperar a frase inteira.

**Se algo falhar:** a voz escolhida passa sozinha para a da Microsoft e, sem internet, para a voz do Windows (ou rode com `--voz-offline`). Para a saída de som não "dormir" e cortar o começo das falas, o `tars.py` a mantém aberta tocando silêncio.

## Comandos do Arduino

Pelo Monitor Serial (115200, Nova linha), pelo `tars.py` ou pelo Bluetooth:

| Comando | O que faz |
|---|---|
| `a <gesto>` | `saudar`, `dancar`, `feliz`, `triste`, `sim`, `nao`, `pensar`, `repouso`, `andar`, `roda`, `piada`, `duvida`, `susto` |
| `t <texto>` | escreve na tela (sem acentos) |
| `m 0` / `m 1` | coreografia desligada / ligada |
| `d` | liga ou desliga a coreografia (atalho) |
| `u <canal> <us>` | pulso bruto, para calibrar (ex.: `u 0 1500`); desliga a coreografia |
| `j <braço> <graus>` | move um braço de −90 a 90 graus (ex.: `j 0 45`) |

O robô responde `ok` ao terminar, ou `erro …`. A coreografia autônoma tem 9 cenas, editáveis em `coreografia()`. Depois de qualquer comando, ela espera 30 s antes de voltar.

## Sem os `.bat` (linha de comando, Windows ou Mac)

Na pasta `versao_final/ia`:

```
pip install -r requirements.txt
ollama pull llama3.2:3b
python tars.py --teste
python tars.py --porta auto --baud 115200 --teclado
python tars.py --porta auto --baud 115200
```

| Opção | Para quê |
|---|---|
| `--porta COM5` | porta fixa, em vez de `auto` |
| `--sem-robo` | testar a IA sem o robô |
| `--vosk vosk-model-small-pt-0.3` | reconhecimento de voz **sem internet** (modelo em alphacephei.com/vosk/models) |
| `--voz-offline` | voz do sistema, sem internet |
| `--mudo` | só texto, sem falar |
| `--modelo llama3.2:1b` | IA menor, para notebook lento |

No **Mac**:
- use `python3`;
- antes, rode `brew install portaudio`, porque o `pyaudio` precisa dele;
- ligue o Uno por um adaptador USB-C;
- dê permissão de microfone ao Terminal.

## Bluetooth (opcional)

O HC-05 substitui o cabo USB. O Arduino já escuta os dois.

| HC-05 | Uno |
|---|---|
| **+5V / GND** | **5V** (ao lado do RES) / **GND** |
| **TX** | **D10** |
| **RX** | **D11 → 1 kΩ → RX**, e do RX um **2 kΩ → GND** (o RX do HC-05 é de 3,3 V) |

Pareie no Windows (Configurações → Bluetooth → **HC-05**, senha **1234** ou **0000**). Depois, em *Mais configurações de Bluetooth → Portas COM*, anote a porta **"De saída"** e rode `python tars.py --porta COM5`, sem `--baud`, porque o Bluetooth usa 9600.

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| `pyaudio` não instala ("Microsoft Visual C++ 14.0 is required") | o Python é novo demais: instale o 3.12 (link acima) e rode o `1_instalar.bat` de novo |
| `'ollama' is not recognized` | instale o Ollama; se já instalou, reinicie o notebook |
| "Não achei o Arduino no USB" | troque o cabo ou a porta USB; no Gerenciador de Dispositivos deve aparecer "USB-SERIAL CH340" (senão, instale o driver CH340) |
| "Acesso negado" na porta COM | feche o Arduino IDE |
| Servos não mexem, mas `PCA9685 OK` | pilhas invertidas no borne verde, ou fracas |
| Tela apagada | confira SDA/SCK; depois de mexer nos fios, aperte RESET |
| Braço com folga | prenda o horn no eixo com o parafuso pequeno do SG90 e o braço no horn; use um anel de papelão ou EVA entre o braço e o corpo |
| "(voz falhou: …)" | sem internet ou chave/créditos da ElevenLabs: a voz de reserva assume. Leia o motivo na linha |
| "ElevenLabs 401" | chave errada: rode o `5_escolher_voz.bat` e cole de novo (ou apague `elevenlabs_chave.txt`) |
| "ElevenLabs 402" ou "paid_plan_required" | voz da biblioteca no plano grátis: use a 7 |
| "(risada indisponível: …)" | o `eleven_v3` não está liberado: ele conta a piada sem rir |
| Começo da fala cortado | se aparecer "(não consegui manter a saída de som aberta…)", confira se o `pyaudio` instalou |
| "Perdi a conexão com o meu cérebro" | Ollama fechado ou modelo não baixado: abra o Ollama e rode `ollama list` |
| Não entende a voz | fale perto do microfone; teste com o `2_testar_digitando.bat`; sem internet, use `--vosk` |
