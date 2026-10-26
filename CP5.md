# CP5: apresentação do TARS

Máximo de 10 minutos, com todos os membros presentes e cada um explicando o que fez. O texto falado está em [APRESENTACAO.md](APRESENTACAO.md); aqui ficam os critérios, a demonstração e o plano B.

## Critérios do professor e como o robô atende

| Critério | Como o TARS atende | Onde está |
|---|---|---|
| 1) IA: comando de voz, voz sintetizada, LLM | o notebook ouve (reconhecimento de voz), pensa com uma LLM local (**Ollama**, llama3.2:3b) e responde com voz neural (**ElevenLabs**, com a Microsoft e o Windows de reserva) | `versao_final/ia/tars.py` |
| 2) Atuador mecânico + atuador luminoso | 2 servos SG90 movem os braços (13 gestos); a **tela OLED** mostra o estado, as respostas e pisca como a "luz de piada" | `versao_final/arduino/tars_ia/tars_ia.ino` |
| 3) A voz muda o comportamento | "Oi, TARS" acena; "Caminhe" anda; "Conta uma piada" conta, ri e pisca a tela; "Ajuste o humor para 10%" deixa a IA séria e mostra `HUMOR 10%` | frases e gestos em [versao_final/README.md](versao_final/README.md#3-conversar) |
| 4) Projeto mecânico ≥ 50% do grupo | corpo e braços modelados pelo grupo no Fusion, com verificações de projeto em `projeto.py` | [FUSION.md](FUSION.md), [README.md](README.md#projeto-mecânico) |
| Acabamento | MDF cortado a laser com encaixes dentados, vinco gravado, eletrônica escondida no corpo | [MONTAGEM.md](MONTAGEM.md) |

## Demonstração (cerca de 4 minutos)

Ordem pensada para mostrar uma coisa nova em cada frase:

| # | Diga | O que o público vê |
|---|---|---|
| 1 | "Oi, TARS!" | acena, "OLÁ" na tela e responde |
| 2 | "Quem é você?" | se apresenta com a fala do filme |
| 3 | "Caminhe um pouco" | anda balançando os blocos |
| 4 | "Conta uma piada" | conta a piada parado; no fim, a tela pisca, os braços balançam e ele ri |
| 5 | "Ajuste o humor para 10%" | `HUMOR 10%` na tela |
| 6 | "Conta outra piada" | a resposta sai mais seca: o ajuste muda o jeito da IA |
| 7 | "Ajuste o humor para 100%" | "Vou providenciar uma luz de piada", piscando a tela |
| 8 | "Você acha que a gente merece nota máxima?" | a IA responde com personalidade e escolhe o gesto |
| 9 | "Dança pra gente!" | dança |
| 10 | "Tchau, TARS" e depois "desligar" | acena e volta à coreografia sozinho |

Ensaiem **em voz alta e com barulho de fundo**: o reconhecimento de voz erra mais com ruído.

## Antes de apresentar

- [ ] Robô com pilhas novas, cabo USB ligado no notebook, **Arduino IDE fechado**
- [ ] Ollama aberto; `3_diagnostico.bat` **sem nenhuma FALHA**
- [ ] Internet funcionando (reconhecimento do Google e voz da ElevenLabs), ou o plano B abaixo
- [ ] `4_conversar_por_voz.bat` aberto, com "IA pronta" e "TARS pronto"
- [ ] Volume do notebook alto; se possível, uma caixa de som
- [ ] Testar as frases 1, 3 e 4 antes de chamarem o grupo
- [ ] Fusion aberto no modelo montado, com a vista explodida pronta
- [ ] Levar 4 pilhas AA reserva, carregador do notebook e extensão de tomada

## Plano B

| Se acontecer | Faça |
|---|---|
| O microfone não entende (sala barulhenta) | feche e abra o `2_testar_digitando.bat`; digite as frases. A IA, a voz e o robô funcionam igual |
| Sem internet | `python tars.py --porta auto --baud 115200 --vosk vosk-model-small-pt-0.3 --voz-offline` (modelo Vosk baixado antes, em alphacephei.com/vosk/models) |
| A ElevenLabs falha (créditos, chave) | nada a fazer: a voz da Microsoft assume sozinha |
| A IA demora | normal na 1ª pergunta; o `tars.py` aquece a IA ao abrir. Notebook lento: `--modelo llama3.2:1b` |
| O robô não responde | feche o Arduino IDE; tire e recoloque o USB; abra o `.bat` de novo |
| Servo travou ou braço soltou | tire as pilhas, recoloque o braço em pé, ligue de novo |
| Nada funciona | ligado só nas pilhas, o robô faz a **coreografia sozinho**: explique o projeto com ela |
