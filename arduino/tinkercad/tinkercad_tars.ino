// tinkercad_tars.ino — versão de TESTE do robo_bracos.ino para o Tinkercad Circuits.
// Mesma lógica (comandos, ações, limites, movimento suave); só o hardware muda, porque o
// Tinkercad não tem PCA9685, OLED SSD1306 nem HC-05:
//   PCA9685 → servos direto nos pinos 9 (braço D) e 10 (braço E), biblioteca Servo
//   OLED    → "LCD 16 x 2 (I2C)" do Tinkercad (SDA→A4, SCL→A5)
//   HC-05   → Monitor Serial: digite os comandos que o tars.py mandaria pelo Bluetooth
//
// Comandos (Monitor Serial, uma linha por comando):
//   a <ação>           saudar, dancar, feliz, triste, sim, nao, pensar, repouso
//   t <texto>          escreve no display
//   u <canal> <us>     pulso bruto (canal 0 = braço D, 1 = braço E)
//   j <junta> <graus>  move um braço dentro dos limites (−90 a 90)
//   d                  liga/desliga a coreografia

#include <Servo.h>
#include <Adafruit_LiquidCrystal.h>

Servo servos[2];
const uint8_t PINOS[2] = {9, 10};
Adafruit_LiquidCrystal lcd(0);   // LCD I2C do Tinkercad (endereço 0x20)

struct Junta {
  uint8_t canal;
  int us0, us90;        // pulso com o braço em pé (0°) e deitado à frente (90°)
  int angMin, angMax;
};

// Mesmos valores do robo_bracos.ino: 0° = braço em pé, +90° = à frente, −90° = para trás.
Junta juntas[] = {
  {0, 1500, 2450, -90, 90},  // braço D
  {1, 1500,  550, -90, 90},  // braço E
};
const uint8_t N = sizeof(juntas) / sizeof(juntas[0]);

float atual[N] = {0, 0};
bool demo = false;

// No robô real a tela tem 8 linhas; aqui são 2 × 16 caracteres: "TARS" + o começo da mensagem.
void mostrar(const char *msg) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(F("TARS"));
  lcd.setCursor(0, 1);
  for (uint8_t i = 0; i < 16 && msg[i] && msg[i] != '\n'; i++) lcd.print(msg[i]);
  Serial.print(F("[tela] "));
  Serial.println(msg);
}

void mostrar(const __FlashStringHelper *msg) {
  char buf[33];
  strncpy_P(buf, (const char *)msg, sizeof(buf) - 1);
  buf[sizeof(buf) - 1] = 0;
  mostrar(buf);
}

void escreverPulso(uint8_t canal, int us) {
  if (canal < N) servos[canal].writeMicroseconds(us);
}

void moverJunta(uint8_t i, float graus) {
  const Junta &j = juntas[i];
  graus = constrain(graus, j.angMin, j.angMax);
  escreverPulso(j.canal, j.us0 + (j.us90 - j.us0) * graus / 90.0);
  atual[i] = graus;
}

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

// ── Igual ao robo_bracos.ino ──────────────────────────────────────────────
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

void coreografia() {
  // Teste a coreografia do grupo aqui antes de passar para o robo_bracos.ino.
  passo(35, -35, 700); passo(-35, 35, 700);
}

void processar(char *linha) {
  char cmd = linha[0];
  char *arg = linha[1] ? linha + 2 : linha + 1;
  char *resto;
  if (cmd == 'a') {
    if (acao(arg)) Serial.println(F("ok"));
    else { Serial.print(F("erro acao: ")); Serial.println(arg); }
  } else if (cmd == 't') {
    mostrar(arg);
    Serial.println(F("ok"));
  } else if (cmd == 'u') {
    long canal = strtol(arg, &resto, 10);
    long us = strtol(resto, NULL, 10);
    escreverPulso(canal, us);
    Serial.print(F("ok canal ")); Serial.print(canal); Serial.print(F(" = ")); Serial.println(us);
  } else if (cmd == 'j') {
    long i = strtol(arg, &resto, 10);
    long graus = strtol(resto, NULL, 10);
    if (i >= 0 && i < N) {
      moverJunta(i, graus);
      Serial.print(F("ok junta ")); Serial.print(i); Serial.print(F(" em ")); Serial.println(atual[i]);
    } else Serial.println(F("erro junta"));
  } else if (cmd == 'd') {
    demo = !demo;
    mostrar(demo ? F("DEMONSTRACAO") : F("PRONTO"));
    Serial.println(F("ok"));
  } else {
    Serial.println(F("erro comando"));
  }
}

char buf[72];
uint8_t n = 0;
unsigned long ultimoCaractere = 0;

// O Monitor Serial do Tinkercad não manda o Enter: a linha também termina quando
// os caracteres param de chegar por 100 ms.
void lerComandos() {
  while (Serial.available()) {
    char c = Serial.read();
    ultimoCaractere = millis();
    if (c == '\r') continue;
    if (c == '\n') {
      buf[n] = 0;
      if (n) processar(buf);
      n = 0;
    } else if (n < sizeof(buf) - 1) {
      buf[n++] = c;
    }
  }
  if (n && millis() - ultimoCaractere > 100) {
    buf[n] = 0;
    processar(buf);
    n = 0;
  }
}

void setup() {
  Serial.begin(9600);
  for (uint8_t i = 0; i < N; i++) servos[i].attach(PINOS[i], 500, 2500);
  for (uint8_t i = 0; i < N; i++) moverJunta(i, atual[i]);
  lcd.begin(16, 2);
  lcd.setBacklight(1);
  mostrar(F("HUMOR 75%"));
  Serial.println(F("Comandos: a <acao> | t <texto> | u <canal> <us> | j <junta> <graus> | d"));
}

void loop() {
  lerComandos();
  if (demo) coreografia();
}
