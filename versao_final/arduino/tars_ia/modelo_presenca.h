// modelo_presenca.h — GERADO por versao_final/ia/presenca.py (python presenca.py treinar). Não edite à mão.
// Regressão logística multiclasse: 4 características → 4 classes; acurácia no teste: 92.2%.
#pragma once
#define PRESENCA_N_CLASSES 4
#define PRESENCA_N_CARAC 4
// classes: 0 = vazio, 1 = chegando, 2 = presente, 3 = saindo
// características: media_m, inclinacao_m_s, desvio_m, fracao_perto
static const float PRESENCA_MEDIA[PRESENCA_N_CARAC] PROGMEM = {1.845038f, 0.01014788f, 0.05082072f, 0.4458f};
static const float PRESENCA_ESCALA[PRESENCA_N_CARAC] PROGMEM = {1.073631f, 0.7433073f, 0.1636234f, 0.4529927f};
static const float PRESENCA_PESOS[PRESENCA_N_CLASSES][PRESENCA_N_CARAC] PROGMEM = {
  {1.416051f, -0.009290386f, -0.1966817f, -1.564974f},
  {-0.2231158f, -3.718818f, -0.4907324f, -0.2404445f},
  {-1.066763f, 0.07668242f, 0.9932473f, 2.049124f},
  {-0.1261719f, 3.651426f, -0.3058332f, -0.2437054f},
};
static const float PRESENCA_VIES[PRESENCA_N_CLASSES] PROGMEM = {0.04418564f, 0.2686494f, -0.5836355f, 0.2708004f};
