// tars_ia.ino — TARS, versão final: 2 braços (SG90 no PCA9685) + tela OLED, para conversar com
// a IA do notebook (versao_final/ia/tars.py) pelo cabo USB (ou pelo Bluetooth HC-05, opcional).
// A versão de teste continua em arduino/robo_bracos/. A diferença: o comando "m" liga/desliga o
// modo autônomo de forma explícita, e o tars.py usa isso para os braços ficarem quietos enquanto
// o microfone ouve.
// Bibliotecas (Gerenciador de Bibliotecas da IDE): "Adafruit PWM Servo Driver Library",
// "Adafruit SSD1306" e "Adafruit GFX Library". Servo e SoftwareSerial já vêm com a IDE.
//
// Ligações (montagem final):
//   Uno A4 / A5 / 5V / GND      → PCA9685 SDA / SCL / VCC / GND (conector de pinos dobrados)
//   Uno SDA / SCL (ao lado do AREF), 3.3V, GND → OLED SDA / SCK / VDD / GND
//   Servo braço D → PCA9685 canal 0 | servo braço E → canal 1 (marrom na fileira preta, GND)
//   Pilhas (4 × AA, 6 V) → borne verde V+ / GND do PCA9685; do borne V+ um jumper ao Vin do Uno.
//     (Nunca no pino 5V: 6 V queima o Uno.) Pelo Vin, o cabo USB pode ficar ligado junto.
//   HC-05: +5V → 5V (ao lado do RES), GND → GND, TX → D10, RX ← D11 pelo divisor
//     (D11 →1 kΩ→ RX →2 kΩ→ GND): o RX do HC-05 é de 3,3 V.
//
//   Sensor ultrassônico HC-SR04 (GS CitizenTech): VCC → 5V, GND → GND, Trig → D7, Echo → D8.
//
// Comandos (uma linha cada, terminada em Enter), pelo USB (115200) ou pelo Bluetooth (9600):
//   a <ação>           saudar, dancar, feliz, triste, sim, nao, pensar, repouso,
//                      andar, roda, piada (a tela pisca), duvida, susto
//   t <texto>          escreve na tela (sem acentos)
//   m <0|1>            modo autônomo: 0 = parado (conversa com a IA), 1 = coreografia
//   u <canal> <us>     pulso bruto, para calibrar   (ex.: "u 0 1500")
//   j <junta> <graus>  move um braço dentro dos limites (ex.: "j 0 45")
//   d                  liga/desliga o modo autônomo (atalho para o Monitor Serial)
//   s                  estado do sensor agora | s 1 / s 0: liga/desliga as leituras brutas (10 por s)
//   p                  "estou aqui" do computador (sem resposta). Depois do 1º, se ficar 10 s sem
//                      nenhum comando, o robô entende que o computador caiu e volta ao modo autônomo.
// O robô responde "ok" quando termina (ou "erro ..."). O sensor manda eventos em JSON, uma linha
// cada: {"ev":"estado","estado":"presente","d":62,"conf":93} quando muda o que ele vê, e
// {"ev":"leitura",...} a cada 5 s.

// 1 = servos no PCA9685 (projeto original). 0 = servos direto no Uno, sem PCA9685:
//   servo braço D: sinal → D9 | servo braço E: sinal → D6 | vermelho → 5V do Uno | marrom → GND.
//   (D10/D11 ficam livres para o HC-05.) A bateria entra só no Vin/GND do Uno.
#define USAR_PCA9685 1

#include <Wire.h>
#include <SoftwareSerial.h>
#if USAR_PCA9685
#include <Adafruit_PWMServoDriver.h>
#else
#include <Servo.h>
#endif
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "presenca.h"   // classificador treinado em versao_final/ia/presenca.py

#if USAR_PCA9685
Adafruit_PWMServoDriver pca(0x40);
#else
Servo servos[2];
const uint8_t PINOS_SERVO[2] = {9, 6};   // canal 0 = braço D, canal 1 = braço E
#endif
Adafruit_SSD1306 tela(128, 64, &Wire, -1);
SoftwareSerial bt(10, 11);   // RX ← TXD do HC-05, TX → RXD do HC-05 (pelo divisor)
bool temTela = false;

// O oscilador interno do PCA9685 varia entre placas (~23–27 MHz). Se "u 0 1500" não deixar
// o servo no meio do curso, ajuste aqui (ou meça a saída com um frequencímetro: deve dar 50 Hz).
const uint32_t OSCILADOR_HZ = 27000000;

void escreverPulso(uint8_t canal, int us) {
#if USAR_PCA9685
  pca.writeMicroseconds(canal, us);
#else
  if (canal < 2) servos[canal].writeMicroseconds(us);
#endif
}

struct Junta {
  uint8_t canal;
  int us0, us90;        // pulso com o braço em pé (0°) e deitado à frente (90°) — calibrar com "u"
  int angMin, angMax;   // mesmos limites das juntas no Fusion (projeto.py)
};

// 0° = braço em pé ao lado do corpo (servo centralizado), +90° = à frente, −90° = para trás.
// Os servos estão espelhados dentro do corpo, por isso us90 vai para lados opostos.
// SG90: ~500–2400 µs para 180° (varia até 10° entre unidades) — calibre cada um com "u".
Junta juntas[] = {
  {0, 1500, 2450, -90, 90},  // braço D
  {1, 1500,  550, -90, 90},  // braço E
};
const uint8_t N = sizeof(juntas) / sizeof(juntas[0]);

float atual[N] = {0, 0};   // repouso: os 4 blocos alinhados, como um monolito

void cabecalho() {
  tela.clearDisplay();
  tela.setTextColor(SSD1306_WHITE);
  tela.setTextSize(2);
  tela.setCursor(0, 0);
  tela.print(F("TARS"));
  tela.setTextSize(1);
  tela.setCursor(0, 22);      // abaixo: quebra de linha automática, até ~100 caracteres
}

// Duas versões: texto vindo do computador (RAM) e textos fixos com F("...") (flash).
// A RAM do Uno é de 2 KB e metade já é a imagem da tela, então os textos fixos ficam na flash.
void mostrar(const char *msg) {
  if (!temTela) return;
  cabecalho();
  tela.print(msg);
  tela.display();
}

void mostrar(const __FlashStringHelper *msg) {
  if (!temTela) return;
  cabecalho();
  tela.print(msg);
  tela.display();
}

void moverJunta(uint8_t i, float graus) {
  const Junta &j = juntas[i];
  graus = constrain(graus, j.angMin, j.angMax);
  escreverPulso(j.canal, j.us0 + (j.us90 - j.us0) * graus / 90.0);
  atual[i] = graus;
}

// Leva os braços até `alvo` em `ms` milissegundos com aceleração suave (smoothstep):
// menos tranco nos encaixes de MDF e no horn.
// O sensor continua lendo durante o movimento; se alguém chegar no meio da coreografia, ela para.
void atualizarSensor();
bool interromper = false;

void esperar(unsigned long ms) {
  unsigned long t0 = millis();
  while (millis() - t0 < ms && !interromper) atualizarSensor();
}

void irPara(const float alvo[], int ms) {
  float inicio[N];
  memcpy(inicio, atual, sizeof(inicio));
  for (int t = 0; t <= ms; t += 20) {
    if (interromper) return;
    float s = ms > 0 ? (float)t / ms : 1;
    s = s * s * (3 - 2 * s);
    for (uint8_t i = 0; i < N; i++) moverJunta(i, inicio[i] + (alvo[i] - inicio[i]) * s);
    unsigned long t0 = millis();
    atualizarSensor();
    unsigned long gasto = millis() - t0;
    if (gasto < 20) delay(20 - gasto);
  }
  for (uint8_t i = 0; i < N; i++) moverJunta(i, alvo[i]);
}

void passo(float d, float e, int ms) {
  const float alvo[N] = {d, e};
  irPara(alvo, ms);
}

// Comportamentos que a IA pode pedir. Retorna false se o nome não existir.
bool acao(const char *nome) {
  if (!strcmp_P(nome, PSTR("saudar"))) {
    mostrar(F("OLA! :)"));
    passo(80, 0, 500);
    for (uint8_t i = 0; i < 3; i++) { passo(50, 0, 250); passo(85, 0, 250); }
    passo(0, 0, 600);
  } else if (!strcmp_P(nome, PSTR("dancar"))) {
    mostrar(F("MODO DANCA"));
    for (uint8_t i = 0; i < 4; i++) { passo(35, -35, 450); passo(-35, 35, 450); }
    passo(0, 0, 500);
  } else if (!strcmp_P(nome, PSTR("feliz"))) {
    for (uint8_t i = 0; i < 2; i++) { passo(60, 60, 350); passo(0, 0, 350); }
  } else if (!strcmp_P(nome, PSTR("triste"))) {
    passo(-25, -25, 1200); esperar(800); passo(0, 0, 1200);
  } else if (!strcmp_P(nome, PSTR("sim"))) {
    for (uint8_t i = 0; i < 2; i++) { passo(25, 25, 250); passo(0, 0, 250); }
  } else if (!strcmp_P(nome, PSTR("nao"))) {
    for (uint8_t i = 0; i < 2; i++) { passo(20, -20, 250); passo(-20, 20, 250); }
    passo(0, 0, 250);
  } else if (!strcmp_P(nome, PSTR("andar"))) {    // no filme, o TARS anda balançando os blocos
    for (uint8_t i = 0; i < 3; i++) { passo(35, -35, 600); passo(-35, 35, 600); }
    passo(0, 0, 500);
  } else if (!strcmp_P(nome, PSTR("roda"))) {     // os blocos giram juntos, como a roda do filme
    passo(90, 90, 900); esperar(200);
    passo(-90, -90, 1500); esperar(200);
    passo(0, 0, 900);
  } else if (!strcmp_P(nome, PSTR("piada"))) {    // a "luz de piada": a tela pisca
    for (uint8_t i = 0; i < 3; i++) {
      if (temTela) tela.invertDisplay(true);
      passo(15, -15, 200);
      if (temTela) tela.invertDisplay(false);
      passo(-15, 15, 200);
    }
    passo(0, 0, 300);
  } else if (!strcmp_P(nome, PSTR("duvida"))) {   // "encolhe os ombros"
    passo(-20, -20, 300); esperar(700); passo(0, 0, 400);
  } else if (!strcmp_P(nome, PSTR("susto"))) {
    passo(70, 70, 150); esperar(800); passo(0, 0, 1000);
  } else if (!strcmp_P(nome, PSTR("pensar"))) {
    passo(30, 0, 500);
  } else if (!strcmp_P(nome, PSTR("repouso"))) {
    passo(0, 0, 700);
  } else {
    return false;
  }
  return true;
}

// Chama uma ação pelo nome guardado na flash: a RAM do Uno é curta.
void acaoP(PGM_P nome) {
  char buf[8];
  strncpy_P(buf, nome, sizeof(buf) - 1);
  buf[sizeof(buf) - 1] = 0;
  acao(buf);
}

// ── Modo autônomo ────────────────────────────────────────────────────────────
// Ao ligar, o robô repete a coreografia sozinho, sem notebook nem celular. Ela é dividida em
// cenas curtas (até ~7 s) e o robô lê os comandos entre uma cena e outra. Assim, o celular ou o
// notebook podem assumir a qualquer momento: depois de cada comando, a coreografia espera
// PAUSA_MS sem comandos e então continua.
//   "d" liga/desliga o modo autônomo | "u" (calibração) desliga, para os braços não se mexerem.
const unsigned long PAUSA_MS = 30000;
bool demo = true;
unsigned long esperarAte = 0;   // a coreografia só roda depois deste instante (millis)
uint8_t cena = 0;

// Para mudar a coreografia, edite as cenas: passo(bracoD, bracoE, ms) move os braços
// (−90 a 90 graus), mostrar(F("...")) escreve na tela (sem acentos, \n quebra a linha) e
// acaoP(PSTR("...")) reaproveita as ações acima. Cada cena deve terminar com os braços em pé (0, 0).
void coreografia() {
  switch (cena++) {
    case 0:
      mostrar(F("HUMOR 75%\nHONESTIDADE 90%"));
      passo(0, 0, 800); esperar(2500);
      break;
    case 1:
      acaoP(PSTR("saudar")); esperar(1000);
      break;
    case 2:
      mostrar(F("ANALISANDO\nO AMBIENTE..."));
      passo(30, 0, 600); esperar(800);
      passo(0, 30, 800); esperar(800);
      passo(0, 0, 600);
      break;
    case 3:
      mostrar(F("CAMINHANDO"));
      for (uint8_t i = 0; i < 3; i++) { passo(35, -35, 700); passo(-35, 35, 700); }
      passo(0, 0, 600);
      break;
    case 4:
      mostrar(F("MODO RODA"));
      passo(90, 90, 1200); esperar(400);
      passo(-90, -90, 2000); esperar(400);
      passo(0, 0, 1200);
      break;
    case 5:
      acaoP(PSTR("dancar")); esperar(500);
      break;
    case 6:
      mostrar(F("PIADA:\nUM ROBO ENTRA\nNUM BAR..."));
      passo(20, -20, 500); esperar(2000);
      mostrar(F("...ESQUECI O FIM.\nHUMOR 75%"));
      acaoP(PSTR("piada"));
      break;
    case 7:
      mostrar(F("COOPER, ISSO NAO\nE POSSIVEL.\n\nNAO. E NECESSARIO."));
      passo(-25, -25, 1200); esperar(2500);
      passo(0, 0, 1200);
      break;
    case 8:
      mostrar(F("EM ESPERA"));
      passo(0, 0, 700); esperar(5000);
      break;
    default:
      cena = 0;
  }
}

// ── Sensor ultrassônico HC-SR04 (GS CitizenTech) ─────────────────────────────────
// 10 leituras por segundo; a cada leitura, o classificador (presenca.h) olha o último segundo e
// diz se a frente está vazia, se alguém está chegando, parado na frente ou saindo. Uma mudança só
// vale depois de CONFIRMAR classificações iguais seguidas (evita piscar com ruído). Duas regras
// completam o modelo: "presente" sem mexer nem 2 cm por OBSTACULO_MS é um objeto (passagem
// obstruída), e eco que nunca responde é sensor com falha (fio solto).
const uint8_t PINO_TRIG = 7, PINO_ECHO = 8;
const uint16_t SEM_ECO = 0, FALHA_SENSOR = 0xFFFF;
const uint8_t CONFIRMAR = 3;
const unsigned long OBSTACULO_MS = 20000;
const unsigned long BATIMENTO_MS = 10000;   // sem notícias do computador por 10 s: decide sozinho
const unsigned long TELEMETRIA_MS = 5000;
enum Estado { E_VAZIO, E_CHEGANDO, E_PRESENTE, E_SAINDO, E_OBSTACULO, E_FALHA };   // 0–3 = classes do modelo

uint16_t leituras[PRESENCA_N_JANELA];
uint8_t nLeituras = 0, falhasSeguidas = 0;
uint8_t estado = E_VAZIO, candidato = E_VAZIO, repeticoes = 0;
uint16_t distancia = 0, refParado = 0;
float confianca = 0;
unsigned long ultimaLeitura = 0, paradoDesde = 0, ultimaTelemetria = 0, ultimoBatimento = 0;
bool batimentoVisto = false, brutas = false, atendendoLocal = false;
int8_t reacaoPendente = -1;
Stream *saida = &Serial;   // eventos vão para onde chegou o último comando (USB ou Bluetooth)

// → distância em cm; SEM_ECO se não há nada até ~4 m; FALHA_SENSOR se o eco não responde.
uint16_t medirCm() {
  unsigned long t0 = micros();
  while (digitalRead(PINO_ECHO))   // eco preso em 1 (com o pull-up, é o fio do Echo solto)
    if (micros() - t0 > 50000UL) return FALHA_SENSOR;
  digitalWrite(PINO_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PINO_TRIG, LOW);
  t0 = micros();
  while (!digitalRead(PINO_ECHO))  // o HC-SR04 sobe o eco ~0,5 ms depois do disparo
    if (micros() - t0 > 5000UL) return FALHA_SENSOR;
  t0 = micros();
  while (digitalRead(PINO_ECHO))
    if (micros() - t0 > 25000UL) return SEM_ECO;
  uint16_t cm = (micros() - t0) / 58;
  return cm > PRESENCA_ALCANCE_CM ? SEM_ECO : cm;
}

void imprimirEstado(uint8_t e) {
  switch (e) {
    case E_VAZIO: saida->print(F("vazio")); break;
    case E_CHEGANDO: saida->print(F("chegando")); break;
    case E_PRESENTE: saida->print(F("presente")); break;
    case E_SAINDO: saida->print(F("saindo")); break;
    case E_OBSTACULO: saida->print(F("obstaculo")); break;
    default: saida->print(F("falha"));
  }
}

void emitir(const __FlashStringHelper *tipo) {
  saida->print(F("{\"ev\":\""));
  saida->print(tipo);
  saida->print(F("\",\"estado\":\""));
  imprimirEstado(estado);
  saida->print(F("\",\"d\":"));
  saida->print(distancia);
  saida->print(F(",\"conf\":"));
  saida->print((int)(confianca * 100));
  saida->println('}');
}

// Sem o computador (modo autônomo), o próprio robô reage; com ele, só avisa e o computador decide.
void aoMudarEstado() {
  if (!demo) return;
  if ((estado == E_CHEGANDO || estado == E_PRESENTE) && !atendendoLocal) interromper = true;
  else if (estado == E_VAZIO && !atendendoLocal) return;
  reacaoPendente = estado;
}

void atualizarSensor() {
  // Sem sensor (ou com o fio solto), cada tentativa espera até 50 ms: tenta de novo só a cada 2 s,
  // para os braços e a coreografia não ficarem lentos.
  if (millis() - ultimaLeitura < (estado == E_FALHA ? 2000UL : 100UL)) return;
  ultimaLeitura = millis();
  uint16_t d = medirCm();
  if (brutas) {
    saida->print(F("{\"ev\":\"bruto\",\"d\":"));
    saida->print(d == FALHA_SENSOR ? -1 : (int)d);
    saida->println('}');
  }
  uint8_t novo;
  if (d == FALHA_SENSOR) {
    if (falhasSeguidas < 255) falhasSeguidas++;
    if (falhasSeguidas < 10) return;
    novo = E_FALHA;
    confianca = 1;
  } else {
    falhasSeguidas = 0;
    distancia = d;
    memmove(leituras, leituras + 1, sizeof(leituras) - sizeof(leituras[0]));
    leituras[PRESENCA_N_JANELA - 1] = d;
    if (nLeituras < PRESENCA_N_JANELA) { nLeituras++; return; }
    novo = presenca_classificar(leituras, &confianca);
    if (novo == E_PRESENTE) {
      float f[PRESENCA_N_CARAC];
      presenca_caracteristicas(leituras, f);
      uint16_t cm = f[0] * 100 + 0.5f;
      if (!paradoDesde || abs((int)cm - (int)refParado) > 2) { paradoDesde = millis(); refParado = cm; }
      else if (millis() - paradoDesde > OBSTACULO_MS) novo = E_OBSTACULO;
    } else {
      paradoDesde = 0;
    }
  }
  if (novo == candidato) { if (repeticoes < 255) repeticoes++; }
  else { candidato = novo; repeticoes = 1; }
  if (novo != estado && repeticoes >= (novo >= E_OBSTACULO ? 1 : CONFIRMAR)) {
    estado = novo;
    emitir(F("estado"));
    aoMudarEstado();
  }
  if (millis() - ultimaTelemetria >= TELEMETRIA_MS) {
    ultimaTelemetria = millis();
    emitir(F("leitura"));
  }
}

void reagir(uint8_t e) {
  interromper = false;
  switch (e) {
    case E_CHEGANDO:
    case E_PRESENTE:
      if (atendendoLocal) return;
      atendendoLocal = true;
      acaoP(PSTR("saudar"));
      mostrar(F("BAIRROVIVO\nOLA! O ATENDIMENTO\nPOR VOZ ESTA\nSEM CONEXAO AGORA"));
      break;
    case E_VAZIO:
      atendendoLocal = false;
      mostrar(F("ATE LOGO!"));
      passo(0, 0, 600);
      esperarAte = millis() + 3000;
      break;
    case E_OBSTACULO:
      atendendoLocal = true;   // fica parado: a coreografia não roda com algo na frente
      mostrar(F("PASSAGEM\nOBSTRUIDA?\nAVISE A ZELADORIA"));
      acaoP(PSTR("duvida"));
      break;
    case E_FALHA:
      atendendoLocal = false;
      mostrar(F("SENSOR SEM\nRESPOSTA:\nCONFIRA D7/D8"));
      esperarAte = millis() + 3000;
      break;
  }
}

void verificarBatimento() {
  if (demo || !batimentoVisto || millis() - ultimoBatimento < BATIMENTO_MS) return;
  batimentoVisto = false;
  demo = true;
  cena = 0;
  esperarAte = millis();
  mostrar(F("SEM CONEXAO COM\nO COMPUTADOR:\nMODO AUTONOMO"));
  saida->println(F("{\"ev\":\"autonomo\"}"));
  aoMudarEstado();
}

void processar(char *linha, Stream &resp) {
  char cmd = linha[0];
  char *arg = linha[1] ? linha + 2 : linha + 1;   // o que vem depois de "x "
  char *resto;
  saida = &resp;
  ultimoBatimento = millis();
  if (cmd == 'p') { batimentoVisto = true; return; }   // computador ativo: sem resposta
  esperarAte = millis() + PAUSA_MS;
  if (cmd == 'a') {
    if (acao(arg)) resp.println(F("ok"));
    else { resp.print(F("erro acao: ")); resp.println(arg); }
  } else if (cmd == 't') {
    mostrar(arg);
    resp.println(F("ok"));
  } else if (cmd == 'u') {
    demo = false;   // calibrando: o modo autônomo não mexe nos braços
    long canal = strtol(arg, &resto, 10);
    long us = strtol(resto, NULL, 10);
    escreverPulso(canal, us);
    resp.print(F("ok canal ")); resp.print(canal); resp.print(F(" = ")); resp.println(us);
  } else if (cmd == 'j') {
    long i = strtol(arg, &resto, 10);
    long graus = strtol(resto, NULL, 10);
    if (i >= 0 && i < N) { moverJunta(i, graus); resp.println(F("ok")); }
    else resp.println(F("erro junta"));
  } else if (cmd == 'm' || cmd == 'd') {
    bool antes = demo;
    demo = cmd == 'm' ? strtol(arg, NULL, 10) != 0 : !demo;
    if (demo && !antes) { cena = 0; esperarAte = millis(); }
    if (!demo && antes) passo(0, 0, 600);   // para com os braços em pé
    if (demo) batimentoVisto = false;       // o computador saiu de propósito
    atendendoLocal = false;
    mostrar(demo ? F("DEMONSTRACAO") : F("PRONTO"));
    resp.println(F("ok"));
  } else if (cmd == 's') {
    if (*arg == '1' || *arg == '0') brutas = *arg == '1';
    else emitir(F("estado"));
    resp.println(F("ok"));
  } else {
    resp.println(F("erro comando"));
  }
}

// Junta os caracteres de cada porta até o Enter e executa a linha.
struct Entrada { Stream *porta; char buf[64]; uint8_t n; };   // RAM do Uno é curta (2 KB); o tars.py manda até 63
Entrada entradas[] = {{&Serial, {}, 0}, {&bt, {}, 0}};

void lerComandos() {
  for (Entrada &e : entradas) {
    while (e.porta->available()) {
      char c = e.porta->read();
      if (c == '\r') continue;
      if (c == '\n') {
        e.buf[e.n] = 0;
        if (e.n) processar(e.buf, *e.porta);
        e.n = 0;
      } else if (e.n < sizeof(e.buf) - 1) {
        e.buf[e.n++] = c;
      }
    }
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println(F("TARS ligando..."));
  bt.begin(9600);             // velocidade de fábrica do HC-05
  // SDA e SCL ficam em 1 quando livres; em 0, o fio está encostado no GND (ou o módulo está com defeito).
  pinMode(SDA, INPUT_PULLUP);
  pinMode(SCL, INPUT_PULLUP);
  delay(5);
  if (!digitalRead(SDA)) Serial.println(F("ERRO: SDA (A4) preso em 0 - encostado no GND?"));
  if (!digitalRead(SCL)) Serial.println(F("ERRO: SCL (A5) preso em 0 - encostado no GND?"));
  // Um fio solto ou encostado no SDA/SCL travaria o I²C para sempre; com o timeout o Uno segue.
  Wire.begin();
  Wire.setWireTimeout(25000, true);
#if USAR_PCA9685
  Wire.beginTransmission(0x40);
  Serial.println(Wire.endTransmission() == 0 ? F("PCA9685 OK")
                                             : F("PCA9685 nao encontrado (0x40): confira SDA/SCL/VCC/GND"));
  pca.begin();
  pca.setOscillatorFrequency(OSCILADOR_HZ);
  pca.setPWMFreq(50);
  delay(10);
  for (uint8_t i = 0; i < N; i++) moverJunta(i, atual[i]);
#else
  // Um servo de cada vez: os dois arrancando juntos puxam corrente demais e podem reiniciar o Uno.
  for (uint8_t i = 0; i < N; i++) {
    servos[juntas[i].canal].attach(PINOS_SERVO[juntas[i].canal], 500, 2500);
    moverJunta(i, atual[i]);
    delay(300);
  }
  Serial.println(F("Servos direto no Uno: D9 = braco D, D6 = braco E"));
#endif
  // tela.begin() diz que deu certo mesmo sem tela, então primeiro vê se algo responde no 0x3C.
  Wire.beginTransmission(0x3C);
  temTela = Wire.endTransmission() == 0 && tela.begin(SSD1306_SWITCHCAPVCC, 0x3C);   // sem tela, o resto funciona igual
  mostrar(F("HUMOR 75%\nHONESTIDADE 90%"));
  Serial.println(temTela ? F("Tela OK") : F("Tela nao encontrada (0x3C)"));
  pinMode(PINO_TRIG, OUTPUT);
  digitalWrite(PINO_TRIG, LOW);
  pinMode(PINO_ECHO, INPUT_PULLUP);   // fio do Echo solto fica em 1: o robô percebe a falha
  uint16_t d = medirCm();
  if (d == FALHA_SENSOR) Serial.println(F("Sensor HC-SR04 sem resposta: confira Trig D7, Echo D8, 5V e GND"));
  else { Serial.print(F("Sensor HC-SR04 OK: ")); Serial.print(d); Serial.println(F(" cm (0 = nada ate 4 m)")); }
  Serial.println(F("Comandos: a <acao> | t <texto> | m <0|1> | u <canal> <us> | j <junta> <graus> | d | s"));
  Serial.println(F("Modo autonomo ligado: 'd' desliga"));
}

void loop() {
  lerComandos();
  atualizarSensor();
  verificarBatimento();
  if (reacaoPendente >= 0) {
    uint8_t e = reacaoPendente;
    reacaoPendente = -1;
    reagir(e);
  } else if (demo && !atendendoLocal && (long)(millis() - esperarAte) >= 0) {
    coreografia();
    if (interromper) cena = 0;   // alguém chegou no meio: recomeça do início depois
  }
  interromper = false;
}
