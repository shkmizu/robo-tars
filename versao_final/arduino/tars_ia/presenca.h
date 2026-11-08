// presenca.h — classificador de presença do TARS (GS CitizenTech), em C puro: roda no Uno e no
// computador (o teste versao_final/ia/testes/test_presenca_c.py compila este arquivo com g++ e
// confere que dá o mesmo resultado que presenca.py). Os pesos vêm de modelo_presenca.h, gerado
// por "python presenca.py treinar".
#pragma once
#include <math.h>
#include <stdint.h>
#ifdef ARDUINO
#include <avr/pgmspace.h>
#else
#define PROGMEM
#define pgm_read_float(p) (*(p))
#endif
#include "modelo_presenca.h"

#define PRESENCA_N_JANELA 10      // 1 s de leituras a 10 Hz
#define PRESENCA_PERIODO_S 0.1f
#define PRESENCA_ALCANCE_CM 400   // sem eco (0) conta como 4 m
#define PRESENCA_PERTO_CM 150

enum ClassePresenca { VAZIO, CHEGANDO, PRESENTE, SAINDO };

static inline float presenca_mediana3(float a, float b, float c) {
  float lo = a < b ? a : b, hi = a < b ? b : a;
  return c < lo ? lo : (c > hi ? hi : c);
}

// d_cm: as 10 leituras em ordem (0 = sem eco) → f: média (m), inclinação (m/s), desvio da reta (m),
// fração das leituras a menos de 1,5 m. Mesmas contas de caracteristicas() em presenca.py.
static inline void presenca_caracteristicas(const uint16_t *d_cm, float *f) {
  const uint8_t n = PRESENCA_N_JANELA;
  float m[PRESENCA_N_JANELA], g[PRESENCA_N_JANELA];
  uint8_t perto = 0;
  for (uint8_t i = 0; i < n; i++) {
    m[i] = (d_cm[i] > 0 ? d_cm[i] : PRESENCA_ALCANCE_CM) / 100.0f;
    if (d_cm[i] > 0 && d_cm[i] < PRESENCA_PERTO_CM) perto++;
  }
  g[0] = m[0];
  g[n - 1] = m[n - 1];
  for (uint8_t i = 1; i < n - 1; i++) g[i] = presenca_mediana3(m[i - 1], m[i], m[i + 1]);   // tira picos
  float media = 0;
  for (uint8_t i = 0; i < n; i++) media += g[i];
  media /= n;
  const float xm = (n - 1) * PRESENCA_PERIODO_S / 2;
  float sxx = 0, sxy = 0;
  for (uint8_t i = 0; i < n; i++) {
    float dx = i * PRESENCA_PERIODO_S - xm;
    sxx += dx * dx;
    sxy += dx * (g[i] - media);
  }
  float incl = sxy / sxx, res = 0;
  for (uint8_t i = 0; i < n; i++) {
    float e = g[i] - media - incl * (i * PRESENCA_PERIODO_S - xm);
    res += e * e;
  }
  f[0] = media;
  f[1] = incl;
  f[2] = sqrtf(res / n);
  f[3] = (float)perto / n;
}

// → classe; *confianca recebe a probabilidade da classe (0 a 1).
static inline uint8_t presenca_classificar(const uint16_t *d_cm, float *confianca) {
  float f[PRESENCA_N_CARAC], z[PRESENCA_N_CLASSES];
  presenca_caracteristicas(d_cm, f);
  for (uint8_t j = 0; j < PRESENCA_N_CARAC; j++)
    f[j] = (f[j] - pgm_read_float(&PRESENCA_MEDIA[j])) / pgm_read_float(&PRESENCA_ESCALA[j]);
  uint8_t melhor = 0;
  for (uint8_t c = 0; c < PRESENCA_N_CLASSES; c++) {
    z[c] = pgm_read_float(&PRESENCA_VIES[c]);
    for (uint8_t j = 0; j < PRESENCA_N_CARAC; j++) z[c] += pgm_read_float(&PRESENCA_PESOS[c][j]) * f[j];
    if (z[c] > z[melhor]) melhor = c;
  }
  float soma = 0;
  for (uint8_t c = 0; c < PRESENCA_N_CLASSES; c++) soma += expf(z[c] - z[melhor]);
  *confianca = 1.0f / soma;
  return melhor;
}
