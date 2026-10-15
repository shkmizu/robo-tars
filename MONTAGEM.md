# Montagem do Robô TARS

Passo a passo para montar o robô depois do corte a laser. Leva de 2 a 3 tardes, contando a secagem da cola.

A ordem importa: **teste a eletrônica antes de montar a madeira**, porque depois de fechar o corpo fica difícil mexer.

- Mapa das peças na chapa: https://claude.ai/artifact/1jdB73SS3mzryoovjYr6sd
- Demonstração 3D (ver como as peças se encaixam): https://claude.ai/artifact/CNWZmAH6V9aymZm9zFhAPm
- Lista de compras e ligações: [README.md](README.md)

---

## Antes de começar

**Separe e identifique as 37 peças.** Use o mapa da chapa para saber qual é qual. Passe um pano levemente úmido para tirar a fuligem do laser das bordas.

**Monte tudo a seco primeiro, sem cola.** Encaixe as caixas para ver se os dentes entram:
- **Justo demais:** passe uma lixa fina de leve na lateral dos dentes.
- **Frouxo:** tudo bem, a cola preenche.

**Como saber a posição de cada peça:**
- **Face gravada (com o vinco) = face de fora.** Vale para a frente, a tampa traseira e o topo do corpo.
- **Laterais do corpo:** as duas são iguais. Os **4 furinhos do PCA9685 ficam embaixo e na metade da frente**. Se a peça ficar de cabeça para baixo, a janela do servo sai do lugar.
- **Frente/trás dos braços:** os 2 rasgos do anteparo ficam mais perto da borda que encosta no corpo.

### Ferramentas e materiais
- Chaves de precisão (Phillips e fenda), alicate de bico, lixa fina, estilete
- Broca de 2 mm (furadeira ou morsa manual)
- Cola PVA, elásticos ou fita crepe, esquadro
- Fita dupla-face espessa, vela comum
- Parafusos: M3 × 12 + porcas (12), espaçadores M3 × 10 (4), espaçadores M2,5 × 10 (4), M2 × 8 + porcas (8)
- Bluetooth: módulo **HC-05**, resistores de **1 kΩ e 2 kΩ**, 4 jumpers macho-fêmea a mais
- No computador: Arduino IDE, **Python 3**, **Ollama**, microfone e caixa de som (ou os do notebook)

---

## Fase 1: Testar a eletrônica na mesa (cerca de 1 h)

1. Instale o **Arduino IDE** e, pelo *Gerenciador de Bibliotecas*, instale:
   - *Adafruit PWM Servo Driver Library*
   - *Adafruit SSD1306*
   - *Adafruit GFX Library*
2. Na mesa, sem madeira, faça as ligações:

   | De | Para | Cabo |
   |---|---|---|
   | Uno **A4 / A5 / 5V / GND** | PCA9685 **SDA / SCL / VCC / GND** | jumpers macho-fêmea 20 cm |
   | PCA9685 (o outro conector) | OLED **SDA / SCL / VCC / GND** | jumpers fêmea-fêmea 30 cm |
   | Servo do braço direito | PCA9685 **canal 0** (fio marrom no GND, fileira de baixo) | cabo do servo |
   | Servo do braço esquerdo | PCA9685 **canal 1** | cabo do servo |
   | Fonte 5 V | adaptador P4 → chave → borne **V+ / GND** do PCA9685 | fio 22 AWG |
   | Depois da chave | também no pino **5V** e **GND** do Uno (alimenta o Uno sem o cabo USB) | fio 22 AWG |
   | Capacitor 470 µF | mesmo borne (perna mais curta, −, no GND) | — |
   | HC-05 **VCC / GND** | **5V / GND** do Uno | jumpers macho-fêmea |
   | HC-05 **TXD** | Uno **D10** | jumper |
   | Uno **D11** → resistor 1 kΩ → HC-05 **RXD** | e do RXD → resistor 2 kΩ → **GND** (divisor: protege o HC-05, que é de 3,3 V) | jumpers + resistores |

   > **Sempre que ligar o cabo USB no Uno, solte o fio que vai da chave ao pino 5V do Uno.** O Uno fica alimentado só pelo USB e os servos continuam na fonte. Assim o Uno nunca recebe energia pelos dois lados ao mesmo tempo. Deixe esse fio num conector fácil de soltar.

3. Abra `arduino/robo_bracos/robo_bracos.ino`, conecte o Uno pelo USB e clique em **Carregar**.
4. Ligue a chave da fonte. A tela deve mostrar **"TARS / HUMOR 75% / HONESTIDADE 90%"**.
5. Abra o **Monitor Serial** (115200, "Nova linha") e mande `u 0 1500` e depois `u 1 1500`. Os dois servos vão para o **meio do curso**.
6. **Desligue com os servos nessa posição** e não gire mais os eixos com a mão. Os braços serão montados com os servos centralizados.

> Se algo não funcionar aqui, é muito mais fácil corrigir agora. Veja [Problemas comuns](#problemas-comuns).

---

## Fase 2: Preparar o horn (cerca de 15 min, para cada braço)

7. Pegue o **horn duplo** (o reto, de 2 braços) que vem com o SG90. Com broca de 2 mm, alargue os furos a **10 mm e 14 mm do centro**, 2 de cada lado.
8. Parafuse o horn no **anteparo** com 4 parafusos M2 × 8 e porcas. O cubo do horn fica sobre o furo central, e a face com o encaixe do eixo fica virada para o lado oposto às porcas.

---

## Fase 3: Corpo (cerca de 1 h, mais secagem)

9. **Discos de encosto** (os Ø64 com janela retangular): cole um por fora de cada lateral.
   - Para alinhar, enfie 2 palitos finos ou clipes desdobrados pelos 2 pré-furos da lateral e do disco ao mesmo tempo.
   - As janelas retangulares precisam coincidir.
   - Deixe secar uns 30 min.
10. **Reforços do corpo** (4 plaquinhas com rasgo em T): ficam por dentro das laterais, encostados na borda de trás, perto dos furos da tampa traseira.
    - **Truque de alinhamento:** encaixe a tampa traseira a seco, passe o parafuso M3 pela tampa e rosqueie numa porca colocada no rasgo do reforço.
    - Com o reforço preso pelo parafuso, passe cola na face que encosta na lateral e deixe secar.
    - Depois tire a tampa, que não leva cola.
11. **PCA9685** na lateral esquerda, a do lado oposto à tela: espaçadores M2,5 nos 4 furinhos. Os parafusos entram por fora e as cabeças ficam no vão entre a lateral e o braço.
    - O borne de parafuso fica virado **para trás**, para dar acesso pela tampa.
12. **Servos:** coloque cada SG90 **por dentro** da lateral, com o eixo **para cima** dentro da janela e o fio saindo por baixo.
    - A aba encosta na face de dentro.
    - Prenda com os 2 parafusos que vêm com o servo, nos pré-furos. Eles atravessam a lateral e o disco de encosto.
    - Não aperte demais.
13. **Arduino no fundo:** instale os 4 espaçadores M3 nos furos do fundo, com os parafusos por baixo. O USB fica virado para a borda de trás.
14. **OLED:** cole com fita dupla-face por trás da janela da frente. A janela fica no bloco da direita, perto do topo, e os pinos do OLED ficam para cima.
15. **Montar a caixa:** passe cola fina nos dentes e encaixe **fundo + laterais + frente + topo**.
    - Prenda com elásticos ou fita crepe e confira o esquadro.
    - Coloque a tampa traseira **sem cola**, só com os parafusos, para manter a caixa no formato enquanto seca.
    - Deixe secar 1 h; a cura total leva 24 h.
16. **Base:** cole por baixo do fundo. Os 4 furos largos ficam sobre as cabeças dos parafusos do Arduino.

---

## Fase 4: Eletrônica dentro do corpo (cerca de 40 min)

17. Encaixe o **Uno** nos espaçadores e prenda com parafusos M3 × 6.
18. Refaça as ligações da Fase 1 dentro do corpo: Uno → PCA9685, PCA9685 → OLED e servos nos canais 0 (direito) e 1 (esquerdo).
19. Na **tampa traseira**:
    - a **chave KCD1** entra por pressão no recorte retangular;
    - o plugue da fonte passa pelo furo redondo e liga no adaptador P4 com borne, dentro do corpo;
    - adaptador → chave → borne V+/GND do PCA9685, com o capacitor junto.
20. Confira se o **USB do Uno** está alinhado com a janela de baixo da tampa traseira. Prenda os fios soltos com fita para não encostarem nos servos.
    - Cole o **HC-05** com fita dupla-face na face de dentro da lateral direita, abaixo do servo.
21. **Teste de novo**, como no passo 4, antes de seguir.

---

## Fase 5: Braços (cerca de 1 h para os dois, mais secagem)

Para cada braço:

22. Monte a caixa a seco, ainda sem a tampa externa (a lateral com 4 furos nos cantos):
    - 2 peças de frente/trás;
    - a lateral interna, com o furo grande;
    - topo e fundo;
    - o **anteparo com o horn** encaixado nos 2 rasgos, com o **horn virado para a lateral interna** (o lado do furo grande).
23. **Reforços do braço** (4 por braço): use o mesmo truque do passo 10, com a tampa externa presa a seco pelos parafusos. Eles ficam por dentro, na frente e atrás, perto da borda da tampa, em cima e embaixo.
24. Cole a caixa toda, menos a tampa externa, e deixe secar.

---

## Fase 6: Encaixar os braços no corpo (cerca de 30 min)

25. **Lubrifique** o furo grande da lateral interna do braço e a borda do disco do eixo (Ø46) com vela.
26. **Disco do eixo (Ø46 com furo central)**: o braço centraliza esse disco sozinho.
    - Passe **pouca** cola só no verso do disco do eixo, a face que encosta no disco de encosto.
    - Coloque o disco dentro do furo grande do braço.
    - Encaixe o braço no robô: o **eixo do servo entra no horn**, com o braço **em pé, alinhado com o corpo**.
    - Pelo furo central do anteparo, com o braço ainda aberto, aperte o parafuso do horn no eixo.
    - **Não mexa no braço por 1 h.** Como o horn está centrado no eixo, o furo do braço posiciona o disco exatamente no lugar.
    - Cuidado para a cola não escorrer até o furo do braço; a vela ajuda a evitar que grude.
27. Depois de seco, gire o braço com a mão, **bem devagar e com a fonte desligada**. Ele deve girar sem prender. Se raspar, passe mais vela.
28. Feche a tampa externa do braço com 4 parafusos M3. Repita para o outro braço.

---

## Fase 7: Calibrar e testar (cerca de 30 min)

29. Solte o fio do 5V do Uno, ligue o cabo USB e a fonte. No Monitor Serial:
    - mande `u 0 1500`: o braço direito deve ficar em pé, alinhado com o corpo;
    - procure com `u 0 <valor>` o pulso em que o braço fica **deitado para a frente** (90°), algo entre 550 e 2450;
    - faça o mesmo com o canal 1.
30. Anote os valores no sketch, na tabela `juntas[]`: `us0` é o braço em pé e `us90` é o braço à frente. Carregue de novo.
31. Teste com `j 0 45`, `j 1 -45` e assim por diante. Os braços devem ir para os ângulos pedidos, de −90° a +90°.
32. **Coreografia:** escreva a sua dentro de `coreografia()` (há um exemplo da "passada" no comentário). Ative e desative com `d` no Monitor Serial.
33. Teste as ações: `a saudar`, `a dancar`, `a sim`, `a nao`, `t OLA TURMA`.
34. Desligue o cabo USB e **reconecte o fio do 5V do Uno**. Daqui em diante o robô funciona sem cabo, pelo Bluetooth.

### Comandos do Monitor Serial (e do Bluetooth)

| Comando | O que faz | Exemplo |
|---|---|---|
| `a <ação>` | executa uma ação: saudar, dancar, feliz, triste, sim, nao, pensar, repouso | `a saudar` |
| `t <texto>` | escreve na tela | `t OLA TURMA` |
| `u <canal> <us>` | pulso bruto no servo (para calibrar) | `u 0 1500` |
| `j <braço> <graus>` | move um braço dentro dos limites (−90 a 90) | `j 1 45` |
| `d` | liga ou desliga a coreografia | `d` |

---

## Fase 8: Bluetooth e comando de voz (cerca de 1 h)

Como funciona: o **notebook** ouve a voz, pergunta à IA (LLM local no **Ollama**), fala a resposta em voz alta e manda uma ação para o robô pelo **Bluetooth**. O robô mexe os braços e mostra o texto na tela.

```
voz → notebook (reconhecimento) → Ollama (IA) → resposta falada
                                               └→ Bluetooth → HC-05 → Arduino → braços + tela
```

### Instalar no notebook
35. **Ollama:** instale pelo site ollama.com e baixe o modelo (uma vez só, cerca de 2 GB):
    ```bash
    ollama pull llama3.2:3b
    ```
    Se o notebook for lento, use `llama3.2:1b`. Se o CP4 usa outro modelo, troque `MODELO` no topo de `ia/tars.py`.
36. **Bibliotecas Python** (use Python 3.11 ou 3.12), a partir da pasta do projeto:
    ```bash
    pip install -r ia/requirements.txt
    ```
    São elas: `pyserial` (Bluetooth), `SpeechRecognition` e `pyaudio` (microfone), `pyttsx3` (voz).
37. Confira se está tudo certo, sem robô e sem microfone. Deve aparecer `autoteste ok`:
    ```bash
    python ia/tars.py --teste
    ```

### Parear o Bluetooth
38. Ligue o robô na chave. O LED do HC-05 pisca **rápido**: ele está esperando conexão.
39. No Windows: **Configurações → Bluetooth e dispositivos → Adicionar dispositivo → Bluetooth → HC-05**. Senha: **1234** (alguns usam **0000**).
40. Descubra a porta: **Mais configurações de Bluetooth → aba Portas COM**. Anote a porta marcada como **"De saída"** (ex.: **COM5**). É ela que o programa usa.

### Testar em etapas
Só passe para a próxima etapa quando a anterior funcionar:

41. **IA sem robô**, digitando. Mostra a resposta e o comando que seria enviado:
    ```bash
    python ia/tars.py --sem-robo --teclado
    ```
42. **Robô pelo Bluetooth**, digitando. Troque COM5 pela sua porta. Digite "Oi, TARS": o robô deve acenar e mostrar a resposta na tela. O LED do HC-05 passa a piscar **devagar** (conectado):
    ```bash
    python ia/tars.py --porta COM5 --teclado
    ```
43. **Diagnóstico completo.** Mostra OK ou FALHA para cada item (Ollama, IA, voz em português, microfone, internet, Bluetooth, robô):
    ```bash
    python ia/tars.py --porta COM5 --diagnostico
    ```
44. **Tudo com voz:**
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

## Fase 9 (opcional): Pintura no estilo do filme

Pinte **depois** de tudo montado e testado, porque a cola não pega bem em tinta. Use primer e cinza grafite fosco em spray. **Proteja com fita** a janela da tela, os furos da tampa traseira e o vão entre corpo e braços, para a tinta não travar o mancal.

---

## Problemas comuns

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Tela apagada | fio trocado ou endereço do OLED | confira SDA/SCL; o Monitor Serial avisa "Tela nao encontrada" |
| Servo não mexe | fonte desligada ou sem GND comum | ligue a chave; o GND da fonte e o do Uno precisam se encontrar no PCA9685 |
| Servo treme ou o Arduino reinicia | falta de corrente | capacitor no borne; fonte de pelo menos 2 A |
| Braço vai para trás em vez de para a frente | sentido invertido | troque o lado do `us90` na tabela `juntas[]` |
| Braço trava no meio do giro | disco do eixo descentralizado ou cola no mancal | passe vela; se não resolver, lixe de leve a borda do disco Ø46 |
| Encaixe muito frouxo | kerf diferente do previsto | cola PVA preenche folgas pequenas |
| Encaixe não entra | kerf menor que o previsto ou MDF mais grosso | lixe de leve a lateral dos dentes |
| HC-05 não aparece no Windows | robô desligado ou HC-05 sem energia | ligue a chave; o LED do HC-05 tem que piscar |
| `tars.py` não abre a porta COM | porta errada ou outro programa usando | use a porta **"De saída"**; feche o Monitor Serial da Arduino IDE |
| Robô não reage pelo Bluetooth | TXD/RXD trocados ou sem o divisor | HC-05 **TXD → D10**; **D11 → 1 kΩ → RXD**; RXD → 2 kΩ → GND |
| "Perdi a conexão com o meu cérebro" | Ollama fechado ou modelo não baixado | abra o Ollama; confira com `ollama list` |
| Não entende a voz | barulho, microfone longe ou sem internet | fale perto do microfone; teste com `--teclado` |
| Voz em inglês | Windows sem voz em português | Configurações → Hora e idioma → Fala → adicionar voz Português (Brasil) |

---

## Checklist

- [ ] Peças identificadas e montadas a seco
- [ ] Eletrônica testada na mesa (tela acende, servos centralizados)
- [ ] Horns parafusados nos anteparos
- [ ] Discos de encosto e reforços colados nas laterais
- [ ] PCA9685, servos, Arduino e OLED instalados
- [ ] Caixa do corpo colada e no esquadro; base colada
- [ ] Ligações refeitas dentro do corpo e testadas
- [ ] Caixas dos braços coladas (menos as tampas)
- [ ] Discos do eixo colados com o braço no lugar
- [ ] Braços giram livres à mão; tampas fechadas
- [ ] Servos calibrados (`us0` / `us90`) e coreografia pronta
- [ ] HC-05 ligado (com o divisor de tensão) e colado dentro do corpo
- [ ] Ollama instalado, modelo baixado, `tars.py --teste` ok
- [ ] HC-05 pareado e porta COM "De saída" anotada
- [ ] Robô responde por voz: acena com "Oi, TARS" e dança com "Dança pra gente"
