# TARS Totem BairroVivo — GS CitizenTech 2026.2 (Project-Based Maker Lab)

Evolução do robô TARS, feito antes na disciplina, para o **BairroVivo**, a plataforma de zeladoria urbana do grupo. Com um **sensor ultrassônico** e **IA embarcada**, o TARS vira um **totem de atendimento**:
- percebe quem se aproxima;
- conversa por voz;
- registra problemas do bairro na API do BairroVivo, como poste apagado, buraco, lixo, calçada quebrada e mobiliário danificado;
- consulta protocolos;
- avisa sozinho quando a passagem em frente ao totem está obstruída.

## Integrantes

> ⚠️ **Preencher antes da entrega.** Sem o nome de todos, o grupo fica sem nota na GS.

| Nome completo | RM |
|---|---|
| _(preencher)_ | _(preencher)_ |
| _(preencher)_ | _(preencher)_ |
| _(preencher)_ | _(preencher)_ |
| _(preencher)_ | _(preencher)_ |
| _(preencher)_ | _(preencher)_ |

**Vídeo de demonstração (até 6 min):** _(link do YouTube — preencher)_

---

## 1. Problema

Problemas do bairro, como iluminação apagada, buracos, lixo e calçadas obstruídas, são comunicados por canais dispersos. Quem mais sofre com eles nem sempre usa aplicativo: idosos, pessoas com pouca familiaridade com celular e pessoas com deficiência visual. O BairroVivo organiza esses relatos numa plataforma única.

A parte física do MVP precisa levar essa plataforma para a rua: **um ponto de atendimento por voz, sem tela de toque e sem cadastro**, que também monitora o próprio espaço. A calçada em frente ao totem é um caso típico de "barreira à mobilidade".

## 2. Solução: o que evoluiu no robô

| | TARS antes (CP5) | TARS Totem BairroVivo (GS) |
|---|---|---|
| Sensores | nenhum (o microfone era do notebook) | **HC-SR04 ultrassônico** na frente, abaixo da tela |
| IA no Arduino | — | **modelo de presença treinado** (regressão logística, 92% de acerto) + regras de obstáculo e falha |
| Quando atende | quando alguém fala | **quando alguém chega perto**; quem só passa não é chamado |
| Microfone | sempre ligado | **só liga quando há alguém na frente** (privacidade) |
| IA no notebook | conversa livre (Ollama) | conversa + **entende o pedido** (categoria, local, descrição) e gera a saudação a partir do contexto do sensor |
| Integração | nenhuma | **API do BairroVivo**: ocorrências, consultas e telemetria, com autenticação do dispositivo e fila sem rede |
| Sem o notebook | coreografia | coreografia + **reage sozinho** ao sensor (acena, avisa obstrução e falha) |

## 3. Componentes

| Componente | Função | Novo na GS? |
|---|---|---|
| Arduino Uno (clone CH340) | lê o sensor, roda o modelo de presença, controla braços e tela | |
| **Sensor ultrassônico HC-SR04** | distância de 2 a 400 cm, 10 leituras por segundo | **sim** |
| PCA9685 (I²C 0x40) | sinal e energia dos servos | |
| 2 × micro servo SG90 | braços: 13 gestos | |
| OLED 0,96" SSD1306 (I²C 0x3C) | estado do atendimento, protocolo, avisos | |
| 4 pilhas AA (6 V) | energia dos servos e do Uno (Vin) | |
| 4 jumpers fêmea-macho de 30 cm (emendados se o sensor ficar por fora) | sensor ↔ Uno | **sim** |
| Notebook (Windows) | microfone, IA (Ollama), voz, ponte com a API | |
| Corpo em MDF 3 mm, corte a laser | 37 peças; 303 × 150 × 84 mm | furos para o sensor (opcional) |

### Ligações do sensor

| HC-SR04 | Uno |
|---|---|
| VCC | 5V (se o pino 5V estiver ocupado pelo PCA9685: 5V do conector ICSP ou mini protoboard) |
| GND | GND |
| Trig | **D7** |
| Echo | **D8** |

Os pinos D7 e D8 estão livres na montagem com o PCA9685. O resto das ligações não muda: veja [versao_final/README.md](versao_final/README.md#ligações).

### Onde o sensor fica

- No **meio da frente, abaixo da tela**, a 19 cm da base, com os dois transdutores um de cada lado do vinco, como "olhos".
- O `projeto.py` verifica que o sensor não encosta na tela, nos servos nem no PCA9685, e que os braços girando ficam fora do cone de detecção (15°). Veja [README.md](README.md#verificações-python-fusionrobodoisbracosprojetopy).
- **Com furos:** 2 furos de Ø16,6 mm. O DXF da frente já tem os furos.
- **Sem furar:** colado por fora com fita dupla-face, com uma moldura de EVA. Os fios entram pela tampa traseira, pela janela do USB ou pelo recorte da chave.
- Modelo 3D com o sensor e o cone de alcance: `demo/robo_demo.html` (botão "Focar no sensor").

## 4. Arquitetura

```
 HC-SR04 ─(10 Hz)─► Arduino Uno ─────────────────────────────── USB (JSON por linha) ───► notebook: tars.py --totem
                    │ presenca.h: modelo treinado                                          │
                    │   vazio / chegando / presente / saindo                               ├─ totem.py: decide o atendimento
                    │ + regras: obstáculo (20 s parado), falha (sem eco)                    │    (estado do sensor + conversa)
                    │ + confirmação (3 leituras iguais)                                    ├─ IA local (Ollama, llama3.2:3b):
                    │                                                                      │    saudação com contexto e
                    ├─► braços (PCA9685 → SG90), tela OLED                                 │    entendimento do pedido
                    │                                                                      ├─ voz (ElevenLabs / Microsoft / Windows)
                    └─ sem notícias do PC por 10 s → modo autônomo:                        └─ bairrovivo.py: ponte com a API
                       reage sozinho ao sensor                                                 X-Device-Key, fila em disco, reenvio
                                                                                                      │ HTTP
                                                                                                      ▼
                                                                                          API do BairroVivo (ou api_simulada.py)
                                                                                          ocorrências · consultas · telemetria
```

## 5. Integração entre o sensor e a IA

A decisão acontece em **três camadas**, cada uma com uma responsabilidade.

### Camada 1: modelo de presença embarcado (Arduino)

- **Entrada:** a cada 100 ms, o último segundo de leituras (10 distâncias). Leitura sem eco conta como 4 m, e um filtro de mediana de 3 tira os picos.
- **Características:**
  - distância média (m);
  - inclinação da reta, ou seja, a velocidade (m/s);
  - desvio em torno da reta, que mede o "tremido" do balanço de uma pessoa;
  - fração das leituras a menos de 1,5 m.
- **Modelo:** regressão logística multiclasse (softmax), com 20 números em ponto flutuante na flash do Uno ([modelo_presenca.h](versao_final/arduino/tars_ia/modelo_presenca.h)).
  - Treinado em Python puro por [presenca.py](versao_final/ia/presenca.py).
  - A mesma conta está em C em [presenca.h](versao_final/arduino/tars_ia/presenca.h); um teste compila o C no computador e confere que dá a mesma classe e a mesma confiança que o Python em 240 janelas.
- **Saída:** `vazio`, `chegando`, `presente` ou `saindo`, com a confiança.
- **Métricas** ([presenca_metricas.md](versao_final/ia/presenca_metricas.md)): **92,2% de acerto** em 2.000 janelas de teste que o modelo não viu.
  - O treino usa dados **sintéticos** que simulam o HC-SR04: ruído de 0,3 a 1,2 cm, até 5% de falhas de eco, ecos espúrios e o balanço de 0,5 a 4 cm de uma pessoa parada.
  - Com o sensor em mãos, `presenca.py gravar` grava leituras reais rotuladas, que entram no treino seguinte.
- **Regras sobre o modelo:**
  - **confirmação:** só muda de estado depois de 3 classificações iguais seguidas;
  - **obstáculo:** "presente" sem variar 2 cm por 20 s é um objeto, porque uma pessoa sempre balança;
  - **falha:** eco que nunca responde, como um fio solto, gera o estado `falha`.

### Camada 2: decisões do totem (notebook, `totem.py`)

| O sensor diz | O totem faz |
|---|---|
| `vazio` | espera com o **microfone desligado**; tela "BAIRROVIVO: CHEGUE PERTO" |
| `chegando` por menos de 1 s e depois `vazio` | nada: a pessoa só passou na calçada |
| `chegando` por 1 s ou `presente` | cumprimenta (camada 3) e começa o atendimento; liga o microfone |
| `presente` + silêncio de 15 s | oferece ajuda |
| `presente` + silêncio de 40 s | despede-se e não cumprimenta de novo até a pessoa sair |
| `vazio`/`saindo` por 2,5 s durante o atendimento | "Até logo!" e volta a esperar |
| `obstaculo` | registra **uma** ocorrência "Calçada / acessibilidade: possível obstrução", origem `sensor_fisico`, para revisão (no máximo uma a cada 30 min) |
| `falha` | avisa na tela e passa a atender **quando alguém fala**, sem o sensor |
| todo evento | vira telemetria na API (`/dispositivos/{id}/leituras`) |

### Camada 3: IA generativa local (Ollama, llama3.2:3b)

- **Saudação contextual:** recebe o JSON do contexto, como `{"evento": "chegando", "distancia_cm": 85, "periodo": "noite", "atendimentos_hoje": 3}`, e gera a fala no estilo do TARS.
- **Entendimento do pedido:** devolve, em JSON:
  - a intenção: `registrar`, `consultar`, `conversar` ou `encerrar`;
  - a categoria, entre as 5 do BairroVivo;
  - título, descrição, local, protocolo, a fala e o gesto.
- **Cuidados contra erros da IA:**
  - **Palavras-chave têm prioridade** nas decisões que mudam o que acontece, como "poste" → Iluminação ou "protocolo" → consulta. Se o Ollama cair, o totem continua funcionando só com elas.
  - **Confirmação por voz** antes de enviar: "Vou registrar: Iluminação, poste apagado, em Rua das Flores 120. Posso enviar?"
  - Toda ocorrência vai com `requer_revisao: true`. A IA **sugere** categoria e prioridade, e um operador decide. Seguimos o plano do BairroVivo: nada é declarado "emergência" por classificação automática.
  - O prompt proíbe inventar endereço, protocolo ou prazo, prometer solução e pedir dados pessoais.

### Protocolo serial (Arduino ↔ notebook)

| Direção | Mensagem | Significado |
|---|---|---|
| Arduino → PC | `{"ev":"estado","estado":"presente","d":62,"conf":93}` | mudou o que o sensor vê |
| Arduino → PC | `{"ev":"leitura","estado":"vazio","d":0,"conf":95}` | telemetria a cada 5 s |
| Arduino → PC | `{"ev":"bruto","d":61}` | leitura crua (10/s), só com `s 1` |
| Arduino → PC | `{"ev":"autonomo"}` | ficou 10 s sem notícias do PC e passou a decidir sozinho |
| PC → Arduino | `p` (a cada 3 s) | "estou aqui" |
| PC → Arduino | `s` · `s 1` · `s 0` | estado agora · liga/desliga as leituras cruas |
| PC → Arduino | `a <gesto>` · `t <texto>` · `m 0/1` | gesto · tela · coreografia |

## 6. Contrato da API

O mesmo contrato está implementado em [api_simulada.py](versao_final/ia/api_simulada.py), para testar sem o backend do grupo. Endereço e prefixo ficam em `bairrovivo_config.json` (modelo: `bairrovivo_config.exemplo.json`).
- **Autenticação do dispositivo:** cabeçalho `X-Device-Key`, com a chave fora do código (variável `BAIRROVIVO_CHAVE` ou `bairrovivo_chave.txt`, fora do Git).
- **Reenvio sem duplicar:** cabeçalho `Idempotency-Key`.

| Método e rota | Corpo | Resposta |
|---|---|---|
| `GET /api/saude` | — | `200 {"status":"ok"}` |
| `POST /api/dispositivos/{id}/leituras` | `{"dispositivo_id","tipo":"presenca_ultrassonico","evento","estado","distancia_cm","confianca","origem":"sensor_fisico","momento"}` | `201 {"id"}` |
| `POST /api/ocorrencias` | `{"titulo","descricao","categoria","local_texto","origem":"totem_voz"\|"sensor_fisico","prioridade_sugerida","texto_original","requer_revisao":true,"dispositivo_id","referencia_totem":{descricao,latitude,longitude},"momento"}` | `201 {"protocolo":"BV-0001","status":"Recebida"}` · `422` se a categoria ou um campo estiver errado |
| `GET /api/ocorrencias/{protocolo}` | — | `200 {protocolo, titulo, categoria, status, historico…}` · `404` |
| `PATCH /api/ocorrencias/{protocolo}` (só na simulada) | `{"status":"Em análise"}` | simula o operador mudando o status |

Categorias: `Buraco / pavimento`, `Iluminação`, `Descarte irregular`, `Calçada / acessibilidade`, `Mobiliário urbano`. Status: `Recebida → Em análise → Encaminhada → Em atendimento → Resolvida | Não procedente`.

## 7. Autonomia e situações de falha

| Situação | O que acontece | Como mostrar no vídeo |
|---|---|---|
| Notebook desligado ou cabo USB puxado | em 10 s, o Arduino volta a decidir sozinho: coreografia, e quando alguém chega ele acena e mostra "BAIRROVIVO… SEM CONEXAO" | tirar o USB com o robô nas pilhas |
| Internet ou API fora do ar | o relato vai para a fila em disco; o TARS avisa "guardei e envio quando voltar"; o reenvio é automático, sem duplicar | fechar o `8_api_simulada.bat`, registrar, abrir de novo e ver no painel |
| Ollama fora | saudação pronta + palavras-chave: o registro continua funcionando | fechar o Ollama |
| Sensor desconectado | estado `falha`, aviso na tela; o totem passa a atender por voz | soltar o fio do Echo |
| Objeto parado na frente | após 20 s, registra a obstrução uma vez, para revisão | deixar uma mochila na frente |
| Pessoa só passando | não é cumprimentada | passar andando na frente |
| Leitura com ruído ou pico | filtro de mediana + 3 confirmações | — |
| Chave errada / dado inválido | a API responde 401/422; não entra na fila (reenviar não resolveria) | — |

## 8. Instalação e execução

**Arduino**
1. No Arduino IDE, instale as bibliotecas **Adafruit PWM Servo Driver Library** e **Adafruit SSD1306**.
2. Abra `versao_final/arduino/tars_ia/tars_ia.ino`. Os arquivos `presenca.h` e `modelo_presenca.h` abrem junto, nas abas.
3. Ajuste `us0`/`us90` na tabela `juntas[]` e carregue no Uno.
4. Confira no Monitor Serial (115200): deve aparecer `Sensor HC-SR04 OK: … cm`.
5. Feche o IDE.

**Notebook (Windows)**: Python 3.12 e Ollama. O passo a passo completo está em [versao_final/README.md](versao_final/README.md#2-preparar-o-notebook-windows-uma-vez). Na pasta `versao_final/ia`, dê clique duplo em:

| Arquivo | O que faz |
|---|---|
| `1_instalar.bat` | bibliotecas + modelo de IA + autoteste |
| `8_api_simulada.bat` | sobe a API do BairroVivo simulada; o painel do operador fica em http://localhost:8000 (deixe aberto) |
| `7_totem_digitando.bat` | totem digitando; simule o sensor com `/chegou`, `/saiu`, `/obstaculo`, `/falha`, `/passou` |
| `6_totem_bairrovivo.bat` | **totem completo**: sensor + voz + API |
| `9_rodar_testes.bat` | os 30 testes automáticos |

Com o backend real do grupo: copie `bairrovivo_config.exemplo.json` para `bairrovivo_config.json`, troque a `url` e coloque a chave do dispositivo em `bairrovivo_chave.txt`. Na API simulada, a chave é `chave-demo`.

Sem robô e sem microfone, em qualquer sistema:
```
cd versao_final/ia
python api_simulada.py
python tars.py --totem --sem-robo --teclado
```
O primeiro comando fica rodando; abra outro terminal para o segundo.

## 9. Calibração e dados reais do sensor

Na pasta `versao_final/ia`, com o robô no USB:
```
python presenca.py ao-vivo                                     distância e classe em tempo real
python presenca.py gravar --rotulo presente --segundos 30      pessoa parada na frente
python presenca.py gravar --rotulo chegando --segundos 30      pessoa vindo de 3 m até o totem, várias vezes
python presenca.py gravar --rotulo saindo --segundos 30
python presenca.py gravar --rotulo vazio --segundos 30         ninguém (e gente passando longe)
python presenca.py treinar                                     treina com as gravações + sintéticos
```
O treino gera um novo `modelo_presenca.h` e atualiza `presenca_metricas.md`. Depois, carregue o sketch de novo no Arduino. Façam commit das gravações em `gravacoes/`: elas são evidência de calibração.

## 10. Testes

`9_rodar_testes.bat` ou `python -m unittest discover -s testes -v` (na pasta `versao_final/ia`). Os testes não precisam de robô, microfone nem Ollama.

| Arquivo | O que verifica |
|---|---|
| `test_presenca.py` | características; acerto do modelo acima de 85% em dados novos; casos claros; **C e Python dão o mesmo resultado** (compila `presenca.h` com g++) |
| `test_bairrovivo.py` | registro e consulta; **API fora do ar → fila em disco → reenvio quando volta**; reenvio sem duplicar; 401/422 fora da fila; limite da fila de telemetria |
| `test_robo.py` | eventos do sensor separados das respostas "ok"; batimento; cabo puxado não derruba o programa |
| `test_totem.py` | quem passa não é cumprimentado; cumprimento ao chegar; microfone desligado sem ninguém; saída; silêncio; telemetria; registro com confirmação; cancelamento; sem rede; consulta; obstáculo registrado uma vez; sensor com falha; saudação e extração pela IA |

O firmware também foi compilado para o ATmega328P: 30.834 bytes (94% da flash) e 974 bytes de RAM.

**Ainda falta testar com o sensor físico** e anotar aqui os resultados:
- [ ] Distância real × medida: 30, 60, 100 e 200 cm, com fita métrica.
- [ ] 10 aproximações → quantas viraram `chegando`/`presente`.
- [ ] 10 passagens na frente → quantas foram ignoradas.
- [ ] Objeto parado → `obstaculo` em ~20 s.
- [ ] Fio do Echo solto → `falha`.
- [ ] USB puxado → modo autônomo em 10 s.
- [ ] API fechada → fila → reenvio.

## 11. Roteiro do vídeo (até 6 min)

| Tempo | O quê |
|---|---|
| 0:00–0:40 | O problema: relatos dispersos e quem não usa aplicativo. O BairroVivo e o papel do totem |
| 0:40–1:30 | O robô: o sensor na frente, as ligações, o modelo 3D com o cone de alcance |
| 1:30–2:15 | Como a IA decide: as 3 camadas e o modelo treinado (mostrar a matriz de confusão) |
| 2:15–4:00 | **Demonstração:** alguém passa (não é chamado) → alguém chega (saudação) → "tem um poste apagado na Rua…" → confirmação → protocolo → aparece no painel → "qual o status do protocolo 1?" |
| 4:00–5:15 | **Falhas:** API fechada (fila e reenvio) · mochila na frente (obstrução registrada) · USB puxado (modo autônomo) |
| 5:15–6:00 | Resultados, limitações e próximos passos |

## 12. Segurança, privacidade e ética

- O **microfone só liga com alguém na frente**. O áudio não é gravado nem enviado: só o texto reconhecido vai para a IA local, e só o relato vai para a API.
- O totem **não pede nome, telefone, CPF nem e-mail**.
- O sensor ultrassônico mede só distância: não identifica pessoas.
- A chave do dispositivo fica fora do código e do Git. Na API, o dispositivo só cria leituras e ocorrências e consulta protocolos.
- A IA **sugere**, um operador **decide** (`requer_revisao: true`). Nada é tratado como emergência automaticamente.

## 13. Limitações

- O modelo foi treinado com **dados sintéticos**; os dados reais entram com `presenca.py gravar`. A acurácia real só será conhecida depois da calibração no local.
- O HC-SR04 tem um cone estreito (~15°): pessoas muito de lado não são vistas, e superfícies macias ou inclinadas refletem mal.
- O firmware usa 94% da flash do Uno: há pouco espaço para crescer sem otimizar.
- O reconhecimento de voz do Google e as vozes neurais precisam de internet; sem ela, use `--vosk` e `--voz-offline`.
- A integração foi testada com a API simulada. O backend real do grupo precisa seguir o contrato da seção 6, ou basta ajustar `bairrovivo_config.json`.
