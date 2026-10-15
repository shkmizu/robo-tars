# Testar o código do TARS no Tinkercad

O Tinkercad Circuits não tem o PCA9685, o OLED SSD1306 nem o Bluetooth HC-05. Por isso este teste usa o [`tinkercad_tars.ino`](tinkercad_tars.ino), que tem **a mesma lógica** do `robo_bracos.ino` (comandos, ações, limites, movimento suave) com o hardware trocado:

| No robô | No Tinkercad |
|---|---|
| PCA9685 + 2 SG90 | 2 × **Micro servo** direto nos pinos **9** e **10** |
| OLED SSD1306 | **LCD 16 x 2 (I2C)** |
| HC-05 (comandos do `tars.py`) | **Monitor Serial** (você digita os comandos) |

## Montar o circuito

1. Entre em tinkercad.com → **Circuitos → Criar novo circuito**.
2. Arraste para a área de trabalho: **Arduino Uno R3**, 2 × **Micro servo** e 1 × **LCD 16 x 2 (I2C)**.
3. Ligue os fios:

   | Componente | Pino | Arduino |
   |---|---|---|
   | Servo 1 (braço D) | Sinal | **D9** |
   | Servo 2 (braço E) | Sinal | **D10** |
   | Servos | Potência / Terra | **5V** / **GND** |
   | LCD I2C | GND / VCC | **GND** / **5V** |
   | LCD I2C | SDA / SCL | **A4** / **A5** |

4. Clique em **Código → Texto** (confirme a troca), apague o que estiver lá e cole o conteúdo de `tinkercad_tars.ino`.
5. Clique em **Iniciar simulação** e abra o **Monitor Serial** (embaixo do código).

## Testes

Digite cada comando no Monitor Serial e clique em **Enviar**:

| Comando | Resultado esperado | O que testa |
|---|---|---|
| `a saudar` | servo 1 acena 3 vezes; LCD: "OLA! :)"; Monitor: `ok` | ação de cumprimento |
| `a dancar` | servos alternam (passada); LCD: "MODO DANCA" | ação de dança |
| `a sim` / `a nao` | servos balançam juntos / alternados | respostas da IA |
| `t Ola turma` | LCD mostra "Ola turma" | mensagens da IA na tela |
| `j 0 45` | servo 1 vai para 45°; `ok junta 0 em 45.00` | comando de ângulo |
| `j 0 150` | servo 1 para em **90** (`em 90.00`) | **limite de segurança** |
| `j 1 -60` | servo 2 vai para −60° | sentido espelhado do braço E |
| `a voar` | `erro acao: voar` | ação inválida não trava |
| `x` | `erro comando` | comando inválido não trava |
| `d` | coreografia em loop; `d` de novo para parar | modo demonstração |

Os comandos `a ...` e `t ...` são exatamente o que o `tars.py` manda ao robô pelo Bluetooth. Se eles funcionarem aqui, a parte do Arduino está certa.

## O que o Tinkercad NÃO testa

- o PCA9685, o OLED e o HC-05 de verdade (a fiação e as bibliotecas reais);
- a memória: o Uno real tem a tela OLED, que ocupa 1 KB a mais;
- a voz e a IA (`tars.py`), que rodam no notebook.

Esses só se confirmam com o robô montado: siga a Fase 8 do [MONTAGEM.md](../../MONTAGEM.md).
