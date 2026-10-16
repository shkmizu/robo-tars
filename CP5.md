# CP5: apresentação do TARS (segunda, 19/10/2026)

Máximo de 10 minutos, com todos os membros presentes e cada um explicando o que fez.

## Critérios do professor e como o robô atende

| Critério | Como o TARS atende | Onde está |
|---|---|---|
| 1) IA do CP4: comando de voz, voz sintetizada, LLM | o notebook ouve (reconhecimento de voz), pensa (LLM local no **Ollama**) e responde em voz alta (pyttsx3 ou a voz do CP4) | `ia/tars.py` |
| 2) Atuador mecânico + atuador luminoso | 2 servos SG90 movem os braços; **display OLED** mostra o estado e as respostas | `arduino/robo_bracos/robo_bracos.ino` |
| 3) A voz muda o comportamento | "Oi, TARS" → acena + "OLÁ!" na tela; "Dança" → passada; a LLM também escolhe sim/não/feliz/triste | ações no Arduino + palavras-chave em `tars.py` |
| 4) Projeto mecânico ≥ 50% do grupo | modelagem e montagem no Fusion feitas pelo grupo | [FUSION.md](FUSION.md) |
| Acabamento | encaixes dentados limpos, vinco gravado, pintura opcional | [MONTAGEM.md](MONTAGEM.md), Fase 8 |

## Como funciona

```
 voz ──► notebook: reconhecimento ──► Ollama (LLM local) ──► {"fala": "...", "acao": "saudar"}
                                                                  │                   │
                                                  voz sintetizada ◄┘                   │ Bluetooth (HC-05)
                                                                                       ▼
                                                     Arduino Uno ──► PCA9685 ──► 2 × SG90 (braços)
                                                                └──► OLED (estado e resposta)
```

A tela mostra **OUVINDO… → PENSANDO… → a resposta**, e os braços fazem a ação ao mesmo tempo em que o notebook fala.

## Preparar o notebook (fazer até sábado)

1. **Ollama:** instale (ollama.com) e baixe um modelo que fale bem português:
   ```bash
   ollama pull llama3.2:3b
   ```
   Se o notebook for lento, use `llama3.2:1b`. Se o CP4 já usa outro modelo, mude `MODELO` no topo de `tars.py`.
2. **Bibliotecas Python.** Use **Python 3.11 ou 3.12**, porque o `pyaudio` (microfone) costuma não instalar em versões mais novas:
   ```bash
   pip install -r ia/requirements.txt
   ```
3. **Reconhecimento de voz offline** (seguro contra falta de internet na sala): baixe o modelo **vosk-model-small-pt-0.3** (cerca de 30 MB) em alphacephei.com/vosk/models e descompacte na pasta `ia/`.
4. **Parear o HC-05** (robô ligado, LED do HC-05 piscando rápido):
   - Windows: Configurações → Bluetooth → Adicionar dispositivo → **HC-05**, senha **1234** (ou 0000).
   - Depois: Mais opções de Bluetooth → **Portas COM** → anote a porta **"De saída"** (ex.: COM5).
5. **Diagnóstico:** confere Ollama, IA, voz em português, microfone, internet ou Vosk, portas e robô, e diz o que falta. Rode também **na sala, antes de apresentar**:
   ```bash
   python ia/tars.py --porta COM5 --diagnostico
   ```
   Para conferir o Vosk, acrescente `--vosk ia/vosk-model-small-pt-0.3`.
6. **Testar em etapas**, cada uma só depois da anterior funcionar:
   ```bash
   python ia/tars.py --teste
   ```
   ```bash
   python ia/tars.py --sem-robo --teclado
   ```
   ```bash
   python ia/tars.py --porta COM5 --teclado
   ```
   ```bash
   python ia/tars.py --porta COM5
   ```
   As etapas são: autoteste; IA sem robô, digitando; robô pelo Bluetooth, digitando; tudo com voz.

### Usar com o script do CP4

Se o grupo prefere manter o script do CP4 (reconhecimento de voz e voz já prontos), basta acrescentar:

```python
from tars import Robo, decidir          # tars.py na mesma pasta do script

robo, historico = Robo('COM5'), []
# ... onde o script já tem o texto reconhecido:
fala, acao = decidir(texto_reconhecido, historico)
robo.texto(fala)
robo.acao(acao)
# ... e o script fala `fala` como já fazia
```

**Personalidade:** o texto `PERSONALIDADE` em `tars.py` define o jeito do TARS. Personalizem: é a cara do grupo.

## Roteiro de 10 minutos (sugestão)

| Tempo | Quem | O quê |
|---|---|---|
| 0:00–1:00 | Membro 1 | O que é o TARS, por que o formato de 4 blocos, tamanho (30 × 15 × 8,4 cm) |
| 1:00–3:00 | Membros 1 e 2 | Mecânica: caixas com encaixe dentado, braço com eixo no meio (equilibrado → o SG90 aguenta), mancal de MDF |
| 3:00–4:30 | Membro 4 | Fusion no notebook: modelo montado, braço girando pela junta, vista explodida |
| 4:30–6:00 | Membro 3 | Eletrônica: Uno, PCA9685, OLED, HC-05, bateria; como a IA fala com o robô |
| 6:00–9:00 | Todos | **Demonstração por voz** (frases abaixo) |
| 9:00–10:00 | — | Perguntas |

### Frases ensaiadas para a demonstração
| Diga | O robô faz |
|---|---|
| "Oi, TARS!" | acena, mostra "OLÁ!" e responde |
| "Qual é o seu nível de honestidade?" | responde com a personalidade (LLM) |
| "Dança pra gente!" | passada alternada com os braços |
| "Você acha que a gente merece os 2 pontos extras?" | a LLM escolhe sim/feliz e responde |
| "Tchau, TARS" | acena de despedida |

Ensaiem as frases **em voz alta, na sala ou num lugar com barulho**: o reconhecimento de voz erra mais com ruído.

## Plano B (levar pronto)

| Se acontecer | Faça |
|---|---|
| Microfone não entende (sala barulhenta) | rode com `--teclado` e digite as frases; a IA, a voz do TARS e o robô funcionam igual |
| Sem internet na sala | rode com `--vosk ia/vosk-model-small-pt-0.3` (reconhecimento offline) |
| Bluetooth não conecta | cabo USB: tire o fio do **5V** do Uno (o resto continua), ligue o USB e rode com `--porta COMx --baud 115200`, onde COMx é a porta do cabo |
| Ollama lento | use um modelo menor (`llama3.2:1b`). O `tars.py` já aquece a IA ao iniciar: espere "IA pronta" |
| Servo travou | desligue a chave, gire o braço com a mão até ficar em pé, ligue de novo |

## No dia

- [ ] Chegar cedo: Ollama aberto, HC-05 pareado, **`--diagnostico` sem nenhuma FALHA**, `tars.py` rodando com "IA pronta"
- [ ] Levar: robô com pilhas carregadas, **4 pilhas reserva carregadas**, notebook + carregador, cabo USB (plano B), extensão de tomada
- [ ] Plano C, se a IA falhar: o robô funciona sozinho no **modo autônomo** (é só ligar a chave)
- [ ] Testar as 5 frases antes de chamarem o grupo
- [ ] Fusion aberto no modelo montado e vídeo da vista explodida pronto
- [ ] Cada membro sabe a sua parte do roteiro
