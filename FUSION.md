# Modelagem no Fusion 360: guia para o grupo

O professor vai avaliar a modelagem no Fusion e exige que **pelo menos 50% do projeto mecânico seja feito pelo grupo**. Este guia mostra **como vocês mesmos modelam e montam o robô** a partir das peças que já foram cortadas. Cada membro pode ficar com uma parte e explicá-la na apresentação.

> Os cálculos, o arquivo de corte e o script `fusion/RoboDoisBracos/RoboDoisBracos.py` foram gerados com ajuda de IA. Usem o script só como referência para conferir o resultado. Recomendo dizer ao professor, com transparência, o que foi feito com ajuda de IA e o que o grupo modelou.

## Divisão sugerida

| Membro | Parte | O que mostra na apresentação |
|---|---|---|
| 1 | Caixa do corpo (frente, trás, laterais, topo, fundo, base) | encaixes dentados, tampa removível |
| 2 | Braços (caixa, anteparo, tampa) | braço com eixo no meio (equilíbrio) |
| 3 | Mancal + servos + eletrônica (SG90, Uno, PCA9685, OLED, HC-05) | onde fica cada componente |
| 4 | Montagem final: juntas, simulação, desenhos, vista explodida | robô se mexendo no Fusion, desenho cotado |

## Medidas de referência

Origem no centro da base do corpo. X = lateral, Y = para trás, Z = para cima. Medidas em mm, MDF de 3 mm.

| Item | Posição |
|---|---|
| Corpo (caixa) | X −36 a 36 · Y −42 a 42 · Z 0 a 300 |
| Base | 72 × 84 × 3, embaixo do corpo (Z −3 a 0) |
| **Eixo dos ombros** | **Y = 0, Z = 153** |
| Disco de encosto (Ø64) | colado na lateral, X 36 a 39 |
| Disco do eixo (Ø46) | sobre o disco de encosto, X 39 a 42 |
| Braço direito (caixa) | X 39 a 75 · Y −42 a 42 · Z 6 a 300 (centrado no eixo) |
| Anteparo do horn | dentro do braço, X 46,4 a 49,4 |
| SG90 | dentro do corpo, aba encostada na face de dentro da lateral, eixo na linha Z = 153 |

O braço esquerdo é o espelho do direito.

## Passo a passo

### 1. Preparar
1. Crie um projeto novo e confira as unidades em **mm** (Configurações do documento).
2. Use as peças de `laser/pecas/`: **um DXF por tipo de peça**, na medida exata do modelo, sem a compensação do laser.

### 2. Modelar cada peça
Para cada DXF:
1. **Montar → Novo componente**, com o nome da peça (ex.: "Corpo lateral").
2. Com o componente ativo: **Inserir → Inserir DXF**, escolha o plano XY e o arquivo.
3. **Extrudar** a região da peça (o contorno, sem os furos) em **3 mm**.
4. Para peças repetidas (o nome termina em `_x2`, `_x4`…), copie e cole o componente (Ctrl+C / Ctrl+V) até ter a quantidade certa.

Dica: atribua o material **Madeira / MDF** (Modificar → Material físico) para o Fusion calcular massa e centro de gravidade.

### 3. Componentes comprados
Baixe do **GrabCAD** (gratuito) os modelos 3D em STEP de: *SG90 micro servo*, *Arduino Uno R3*, *PCA9685 16 channel*, *OLED 0.96 SSD1306*, *HC-05*.
- Carregue no Fusion e use **Inserir → Inserir no projeto atual**.
- Componentes reais deixam o modelo mais completo e mostram que o interior foi pensado.

### 4. Montar o corpo
1. Fixe o **fundo** no lugar (clique direito → **Fixar**, "Ground").
2. Encaixe as outras peças com **Montar → Junta**, tipo **Rígida**. Clique num ponto de uma peça (canto, meio de aresta) e no ponto correspondente da outra; o Fusion mostra os pontos de encaixe ao passar o mouse.
3. Na ordem: laterais → frente → topo → tampa traseira → base → reforços → discos do mancal.
4. Posicione os componentes comprados (SG90, Uno, PCA9685, OLED, HC-05) com juntas rígidas, conferindo com a tabela de medidas acima.

### 5. Montar os braços
1. Monte a caixa de cada braço com juntas rígidas: frente/trás, laterais, topo/fundo, anteparo e reforços.
2. **Junta de revolução no ombro:** **Montar → Junta**, tipo **Revolução**:
   - clique na aresta circular do **furo grande da lateral interna do braço**;
   - depois na aresta circular do **disco do eixo** (Ø46). Os dois ficam concêntricos.
3. **Limites:** clique direito na junta → **Editar limites da junta** → mínimo −90°, máximo +90°.
4. Arraste o braço com o mouse: ele deve girar em volta do eixo, sem bater no corpo.

### 6. Verificar
- **Inspecionar → Interferência:** selecione tudo e confira se não há peças se cruzando. Repita com os braços em outras posições.
- **Estudo de movimento** (Montar → Estudo de movimento): anime os dois ombros; serve para mostrar na apresentação.

### 7. Desenhos técnicos e vista explodida
1. **Arquivo → Novo desenho → Do projeto:**
   - vista frontal, lateral, superior e isométrica do conjunto, com as cotas principais (300 × 150 × 84);
   - **Tabela → Lista de peças** e **Balões**.
2. Uma folha por peça principal (lateral, frente, braço), com cotas.
3. **Vista explodida:** espaço de trabalho **Animação** → **Explosão automática: todos os níveis** → **Publicar vídeo**.

## Conferência final

- [ ] Todas as peças modeladas como componentes nomeados
- [ ] Corpo e braços montados com juntas; ombros com revolução de −90° a 90°
- [ ] Componentes eletrônicos no lugar (interior funcional)
- [ ] Sem interferências
- [ ] Desenho cotado + lista de peças + vista explodida
- [ ] Cada membro sabe explicar a parte que modelou
