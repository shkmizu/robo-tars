# TARS — texto de apresentação

Texto para falar em cerca de 10 minutos, dividido entre 4 apresentadores. Troquem "Pessoa 1…4" pelos nomes e ajustem cada parte para contar o que **cada um** fez. Os tempos são aproximados. A lista de frases da demonstração e o plano B estão em [CP5.md](CP5.md).

---

## Abertura — Pessoa 1 (≈ 1 min)

> Boa tarde. Este é o TARS, o nosso robô de mesa inspirado no robô do filme *Interestelar*.
>
> No filme, o TARS é um monolito feito de quatro blocos, que conversa com a tripulação, tem senso de humor ajustável e anda girando os próprios blocos. A gente quis trazer isso para a mesa: um robô que **escuta, pensa, responde com voz e se mexe**, com a personalidade do personagem.
>
> Ele tem 30 centímetros de altura e quatro blocos de MDF. Os dois do meio são o corpo, onde fica toda a eletrônica. Os dois de fora são os braços, cada um movido por um motor. Na frente, uma pequena tela mostra o que ele está fazendo.
>
> Vamos mostrar como ele foi pensado, construído e programado, e no fim vocês vão conversar com ele.

---

## Projeto mecânico — Pessoa 2 (≈ 2 min)

> A parte mecânica foi toda modelada pelo grupo no **Fusion 360** e cortada a laser em **MDF de 3 milímetros**: são 37 peças numa única chapa.
>
> As caixas usam **encaixes dentados**, como um quebra-cabeça: as peças se travam umas nas outras e o robô fica firme. A tampa de trás sai, para dar acesso à eletrônica e ao cabo USB.
>
> A decisão mais importante foi **onde colocar o eixo dos braços**. O motor que a gente usa, o micro servo SG90, é pequeno e tem pouca força: 1,8 kgf·cm. Cada braço pesa perto de 190 gramas. Se o eixo ficasse no alto, como um ombro, o motor teria que segurar todo esse peso e mal daria conta. Por isso o eixo fica **no meio da altura do braço**: o braço funciona como uma gangorra equilibrada, e o motor só precisa vencer o atrito. Com isso a força necessária caiu para 0,28 kgf·cm, uma folga de mais de **6 vezes**.
>
> Antes de cortar, a gente escreveu um script que confere o projeto automaticamente:
> - se os servos cabem dentro do corpo sem se tocar;
> - se o braço não bate na mesa em nenhum ângulo;
> - se o robô não tomba;
> - se cada cabo tem comprimento suficiente.
>
> Foi esse script que mostrou que um jumper de 20 centímetros não chegaria até a tela, antes de a gente comprar.

*(mostrar no Fusion: o modelo montado, o braço girando pela junta e a vista explodida)*

---

## Eletrônica — Pessoa 3 (≈ 2 min)

> Dentro do corpo fica um **Arduino Uno**, que é o "sistema nervoso" do robô. Ligados a ele estão:
> - uma placa **PCA9685**, que controla os servos dos dois braços;
> - uma **tela OLED**, que mostra o que o TARS está fazendo: "ouvindo", "pensando" e a resposta;
> - **quatro pilhas AA**, que alimentam os motores.
>
> A placa e a tela conversam com o Arduino pelo mesmo par de fios, um barramento chamado **I²C**, cada uma com seu endereço.
>
> Uma coisa que aprendemos: os motores não podem ser alimentados pelo Arduino. Quando o servo puxa corrente, a tensão cai e o Arduino reinicia. Por isso as pilhas alimentam os servos direto pela placa PCA9685, e o Arduino recebe energia pela entrada própria para isso.
>
> O robô funciona **sozinho**: ligado só nas pilhas, ele faz uma coreografia de nove cenas, com falas do filme na tela. Quando o notebook se conecta pelo cabo USB, a coreografia para e ele passa a obedecer à IA.
>
> No caminho, a gente teve problemas bem reais:
> - jumpers velhos com mau contato;
> - pilhas ligadas com a polaridade invertida, e os motores não mexiam;
> - a tela que só acendia apertando o fio.
>
> A gente resolveu testando **cada componente sozinho** antes de montar tudo junto, e só depois fechou o corpo.

---

## Inteligência artificial e voz — Pessoa 4 (≈ 2 min)

> A inteligência do TARS fica no notebook. Quando vocês falam, acontecem quatro coisas, em sequência:
>
> 1. **Ouvir:** o microfone grava a frase e o reconhecimento de voz transforma em texto.
> 2. **Pensar:** o texto vai para uma **IA que roda no próprio notebook**, o modelo Llama 3.2 no programa Ollama, sem depender de serviço pago. A gente escreveu a personalidade dele: humor em 75%, honestidade em 90%, respostas curtas, secas e um pouco irônicas, como no filme. A IA devolve duas coisas: **o que falar** e **qual gesto fazer**.
> 3. **Falar:** a resposta vira voz com a **ElevenLabs**, uma voz neural bem natural. Se faltar internet, ele troca sozinho para outra voz e continua funcionando.
> 4. **Agir:** o notebook manda o gesto e o texto pelo cabo USB, e o Arduino mexe os braços e escreve na tela.
>
> Ele tem **13 gestos**, como acenar, andar, dançar, concordar, discordar e o modo roda do filme. Algumas frases funcionam mesmo se a IA falhar: "Oi, TARS" sempre acena. Também colocamos falas do filme: dá para pedir para ele **ajustar o próprio humor**, e isso muda de verdade o jeito da IA responder. E quando conta uma piada, ele faz como no filme: termina a piada sério e só depois acende a **"luz de piada"**, a tela piscando, e ri.
>
> Também deu trabalho fazer a voz e o movimento saírem **juntos**. No começo, o braço mexia antes e a voz vinha atrasada e cortada. A solução foi gerar o áudio antes de mandar o gesto, tocar a fala enquanto ela ainda chega da internet e manter a saída de som do notebook sempre ligada.

---

## Demonstração — todos (≈ 2–3 min)

> Agora a gente vai conversar com ele.

Use as frases do [CP5.md](CP5.md#demonstração-cerca-de-4-minutos), nesta ordem resumida:
1. "Oi, TARS!"
2. "Quem é você?"
3. "Caminhe um pouco"
4. "Conta uma piada"
5. "Ajuste o humor para 10%", depois "Conta outra piada"
6. "Você acha que a gente merece nota máxima?"
7. "Tchau, TARS"

Se der tempo, convidem o professor a fazer uma pergunta.

---

## Encerramento — Pessoa 1 (≈ 30 s)

> Resumindo: o TARS junta **projeto mecânico** (o braço equilibrado e as caixas com encaixe), **eletrônica** (Arduino, PCA9685, tela e pilhas) e **inteligência artificial** (reconhecimento de voz, uma IA local e voz neural) num robô só, com a personalidade do filme.
>
> Os próximos passos seriam:
> - deixar a IA e a voz rodando direto no robô, sem o notebook;
> - colocar uma bateria recarregável;
> - fazer os blocos realmente girarem para ele andar.
>
> Obrigado. Humor em 75%: aceitamos perguntas.

---

## Perguntas que podem aparecer

| Pergunta | Resposta curta |
|---|---|
| Por que a IA roda no notebook e não no Arduino? | O Arduino tem 2 KB de memória; um modelo de linguagem precisa de gigabytes. O Arduino cuida do corpo; o notebook, da mente |
| Precisa de internet? | A IA, não: ela roda no notebook. O reconhecimento do Google e a voz da ElevenLabs, sim. Sem internet, ele usa o reconhecimento Vosk e a voz do Windows, os dois offline |
| Por que o PCA9685, se o Arduino controla servos sozinho? | Ele gera o sinal dos servos sem ocupar o Arduino e recebe a energia das pilhas direto, separada do Arduino |
| Como a IA escolhe o gesto? | Ela responde num formato fixo, `{"fala": "...", "acao": "..."}`, escolhendo um gesto de uma lista. Algumas palavras, como "oi" e "dança", forçam o gesto certo |
| Quanto custou? | Uno, PCA9685, 2 servos SG90, tela OLED, pilhas e o MDF. A IA e as vozes da Microsoft são gratuitas; a ElevenLabs tem plano grátis |
| O que deu mais trabalho? | (cada um responde com a sua parte: encaixes, mau contato dos fios, sincronizar voz e movimento…) |
