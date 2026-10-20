// tars_ia.ino — TARS, versão final: 2 braços (SG90 no PCA9685) + tela OLED + Bluetooth HC-05,
// para conversar com a IA do notebook (versao_final/ia/tars.py). A versão de teste continua em
// arduino/robo_bracos/. A diferença: o comando "m" liga/desliga o modo autônomo de forma explícita,
// e o tars.py usa isso para os braços ficarem quietos enquanto o microfone ouve.
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
// Comandos (uma linha cada, terminada em Enter), pelo USB (115200) ou pelo Bluetooth (9600):
//   a <ação>           saudar, dancar, feliz, triste, sim, nao, pensar, repouso
//   t <texto>          escreve na tela (sem acentos)
//   m <0|1>            modo autônomo: 0 = parado (conversa com a IA), 1 = coreografia
//   u <canal> <us>     pulso bruto, para calibrar   (ex.: "u 0 1500")
//   j <junta> <graus>  move um braço dentro dos limites (ex.: "j 0 45")
//   d                  liga/desliga o modo autônomo (atalho para o Monitor Serial)
// O robô responde "ok" quando termina (ou "erro ...").

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
void irPara(const float alvo[], int ms) {
  float inicio[N];
  memcpy(inicio, atual, sizeof(inicio));
  for (int t = 0; t <= ms; t += 20) {
    float s = ms > 0 ? (float)t / ms : 1;
    s = s * s * (3 - 2 * s);
    for (uint8_t i = 0; i < N; i++) moverJunta(i, inicio[i] + (alvo[i] - inicio[i]) * s);
    delay(20);
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
    passo(-25, -25, 1200); delay(800); passo(0, 0, 1200);
  } else if (!strcmp_P(nome, PSTR("sim"))) {
    for (uint8_t i = 0; i < 2; i++) { passo(25, 25, 250); passo(0, 0, 250); }
  } else if (!strcmp_P(nome, PSTR("nao"))) {
    for (uint8_t i = 0; i < 2; i++) { passo(20, -20, 250); passo(-20, 20, 250); }
    passo(0, 0, 250);
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
      passo(0, 0, 800); delay(2500);
      break;
    case 1:
      acaoP(PSTR("saudar")); delay(1000);
      break;
    case 2:
      mostrar(F("ANALISANDO\nO AMBIENTE..."));
      passo(30, 0, 600); delay(800);
      passo(0, 30, 800); delay(800);
      passo(0, 0, 600);
      break;
    case 3:
      mostrar(F("CAMINHANDO"));
      for (uint8_t i = 0; i < 3; i++) { passo(35, -35, 700); passo(-35, 35, 700); }
      passo(0, 0, 600);
      break;
    case 4:
      mostrar(F("MODO RODA"));
      passo(90, 90, 1200); delay(400);
      passo(-90, -90, 2000); delay(400);
      passo(0, 0, 1200);
      break;
    case 5:
      acaoP(PSTR("dancar")); delay(500);
      break;
    case 6:
      mostrar(F("PIADA:\nUM ROBO ENTRA\nNUM BAR..."));
      passo(20, -20, 500); delay(2000);
      mostrar(F("...ESQUECI O FIM.\nHUMOR 75%"));
      acaoP(PSTR("feliz"));
      break;
    case 7:
      mostrar(F("COOPER, ISSO NAO\nE POSSIVEL.\n\nNAO. E NECESSARIO."));
      passo(-25, -25, 1200); delay(2500);
      passo(0, 0, 1200);
      break;
    case 8:
      mostrar(F("EM ESPERA"));
      passo(0, 0, 700); delay(5000);
      break;
    default:
      cena = 0;
  }
}

void processar(char *linha, Stream &resp) {
  char cmd = linha[0];
  char *arg = linha[1] ? linha + 2 : linha + 1;   // o que vem depois de "x "
  char *resto;
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
    mostrar(demo ? F("DEMONSTRACAO") : F("PRONTO"));
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
  Serial.println(F("Comandos: a <acao> | t <texto> | m <0|1> | u <canal> <us> | j <junta> <graus> | d"));
  Serial.println(F("Modo autonomo ligado: 'd' desliga"));
}

void loop() {
  lerComandos();
  if (demo && (long)(millis() - esperarAte) >= 0) coreografia();
}
