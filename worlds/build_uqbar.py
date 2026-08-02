#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de `uqbar.json`.

El mundo se escribe con un programa y no a mano por dos razones: 16
prototipos de 9 dimensiones a pelo son un campo de minas de erratas, y
sobre todo porque asi el DISEÑO queda explicito y auditable.

Principio de diseño: CADA FAMILIA CONTIENE UNA TRAMPA.

Los tipos se agrupan en familias que ocupan la misma region sensorial
(frutos, raices, hongos, bestias...). Dentro de cada familia hay al menos
un par casi indistinguible con afordancias opuestas: uno alimenta y el
otro envenena, y solo se separan por uno o dos sentidos.

Eso no es decoracion. Es el unico motor que tiene la Fase 1 para afilar
conceptos: un agente de percepcion gruesa mete los dos en el mismo saco,
se envenena, y el daño le obliga a partir la categoria. Sin trampas, la
particion optima seria trivial y no habria nada que descubrir.

Calibracion: las abundancias se ajustan para que el pago esperado de un
encuentro a ciegas sea equivalente al del mundo pequeño original. Asi el
mundo crece en RIQUEZA sin volverse mas duro, y la economia de la
simulacion no hay que reajustarla de cero.

    python worlds/build_uqbar.py
"""

import json
import os

FOOD, WATER, TOXIC, PREDATOR, INERT = (
    "alimento", "agua", "toxico", "depredador", "inerte")

SENSES = [
    ("vista", "luminosidad"), ("vista", "rojez"), ("vista", "verdor"),
    ("olfato", "dulzor"), ("olfato", "acritud"),
    ("gusto", "amargor"), ("gusto", "salinidad"),
    ("tacto", "dureza"), ("tacto", "temperatura"),
]
D = {name: i for i, (_, name) in enumerate(SENSES)}

# Seis lugares. El coste de llegar es lo que hace que DONDE esta algo sea
# informacion util y no adorno: sin coste, el lugar no cambiaria ninguna
# decision y no habria razon para nombrarlo.
# FASE 9: los lugares tienen COORDENADAS, no solo un coste escalar.
# El coste de ir a algo pasa a salir de la distancia real, y la cercania
# decide quien se encuentra con quien. Sin esto, cualquier par de la tribu
# se cruzaba con la misma probabilidad y todos acababan viendolo todo —
# que es exactamente lo que dejo sin nicho a la transmision cultural.
PLACES = [
    ("junto",  0.4, 0.50, 0.50),
    ("vega",   1.3, 0.22, 0.60),
    ("valle",  2.2, 0.75, 0.35),
    ("loma",   3.2, 0.60, 0.85),
    ("bosque", 4.3, 0.15, 0.18),
    ("lejos",  5.4, 0.88, 0.82),
]


def kind(name, base, affordance, payoff, abundance, spread=0.055,
         fija=False, regiones=None, **deltas):
    v = list(base)
    for dim, delta in deltas.items():
        v[D[dim]] = round(min(1.0, max(0.0, v[D[dim]] + delta)), 4)
    d = {"name": name, "prototype": v, "spread": spread,
         "affordance": affordance, "payoff": payoff, "abundance": abundance}
    if fija:
        d["fixed_abundance"] = True
    if regiones is not None:
        # Solo crece en estas regiones. Es lo que reparte el SABER por
        # geografia: quien no ha estado en el bosque no ha visto nunca lo
        # que crece alli, y solo puede enterarse si alguien se lo cuenta.
        d["regions"] = list(regiones)
    return d


#                lum  rojo verde dulz acri amar  sal dureza temp
FRUTO   =       [0.70, 0.80, 0.20, 0.85, 0.15, 0.10, 0.20, 0.20, 0.50]
RAIZ    =       [0.25, 0.35, 0.30, 0.45, 0.30, 0.35, 0.45, 0.75, 0.35]
AGUA    =       [0.60, 0.10, 0.25, 0.10, 0.10, 0.05, 0.35, 0.05, 0.25]
BESTIA  =       [0.40, 0.45, 0.15, 0.30, 0.55, 0.30, 0.60, 0.55, 0.80]
PIEDRA  =       [0.35, 0.20, 0.15, 0.05, 0.10, 0.05, 0.25, 0.95, 0.30]
FLOR    =       [0.85, 0.30, 0.65, 0.70, 0.20, 0.15, 0.10, 0.10, 0.45]
HONGO   =       [0.45, 0.15, 0.10, 0.35, 0.45, 0.30, 0.30, 0.30, 0.40]
INSECTO =       [0.30, 0.55, 0.20, 0.20, 0.65, 0.40, 0.50, 0.35, 0.65]

KINDS = [
    # --- frutos: iguales a la vista, distintos al olfato y al gusto ----
    kind("fruto_dulce",   FRUTO, FOOD,  +8.0, 1.00),
    kind("fruto_amargo",  FRUTO, TOXIC, -10.0, 0.60,
         dulzor=-0.30, acritud=+0.30, amargor=+0.35, rojez=-0.02),

    # --- raices: la mala huele distinto y es mas blanda ----------------
    kind("raiz",          RAIZ,  FOOD,  +6.0, 0.70),
    kind("raiz_fibrosa",  RAIZ,  TOXIC, -8.0, 0.42,
         acritud=+0.32, amargor=+0.28, dureza=-0.22),

    # --- agua: la salobre solo se delata por el gusto ------------------
    kind("charca",        AGUA,  WATER, +4.0, 0.90, regiones=[1, 2, 0]),
    kind("charca_salobre", AGUA, TOXIC, -5.0, 0.40,
         salinidad=+0.38, amargor=+0.22),

    # --- bestias: la peligrosa es mas roja, mas acre y mas caliente ----
    kind("bestia",        BESTIA, FOOD, +9.0, 0.55),
    kind("acechante",     BESTIA, PREDATOR, 0.0, 0.60,
         rojez=+0.25, acritud=+0.25, dureza=+0.13, temperatura=+0.15),

    # --- minerales: una quema; el tacto lo dice, la vista no -----------
    kind("piedra",        PIEDRA, INERT, 0.0, 0.80),
    kind("piedra_ardiente", PIEDRA, TOXIC, -6.0, 0.30,
         temperatura=+0.45, acritud=+0.20),

    # --- flores: una da nectar. Distinguirlas casi no importa ----------
    kind("flor",          FLOR,  INERT, 0.0, 0.65),
    kind("flor_nectar",   FLOR,  FOOD,  +3.0, 0.45,
         dulzor=+0.22, luminosidad=-0.15),

    # --- hongos: la trampa mas cara del mundo --------------------------
    kind("hongo",         HONGO, FOOD,  +7.0, 0.55, regiones=[4, 1]),
    kind("hongo_palido",  HONGO, TOXIC, -12.0, 0.38,
         luminosidad=+0.30, amargor=+0.25, dulzor=-0.18),

    # --- LO RARO Y LETAL ------------------------------------------------
    # Un tipo aparte, en una region sensorial que no ocupa nadie: basta un
    # encuentro para categorizarlo. Pero aparece tan poco que la mayoria
    # de los agentes muere sin haberlo visto jamas.
    #
    # Es la condicion que le faltaba al modelo para que la transmision
    # cultural tuviera algun nicho. El propio modelo la pidio dos veces:
    # el canal de alarma no cuaja porque el depredador es demasiado raro
    # para que su palabra se estabilice, y la prueba de cultura fallo
    # porque lo toxico es tan frecuente que todos lo viven y nadie
    # necesita que se lo cuenten. Entre esas dos cotas deberia haber una
    # ventana — o no haberla, que tambien seria un resultado.
    #
    # Su abundancia NO entra en la calibracion (`fija=True`): si el
    # despeje la reescalara, el parametro que anunciamos de antemano
    # dejaria de ser el que corremos.
    #
    # 0.01, y el numero sale de una cuenta, no del gusto. La rareza hay
    # que medirla en ENCUENTROS ESPERADOS POR VIDA, no en fraccion de
    # encuentros. Con 400 episodios por generacion y bandas de 8, cada
    # agente acumula ~85 exposiciones por generacion y ~850 en su vida;
    # al 0.8% eso eran SIETE ingestiones por cabeza y todo el mundo lo
    # vivia. Para que las ingestiones esperadas bajen de 0.5 hace falta
    # ~0.13% de los encuentros. La tribu entera lo sigue viendo ~9 veces
    # por generacion — suficiente para que exista la palabra — mientras
    # que cada individuo casi nunca lo prueba. Esa es la ventana.
    kind("veneno_raro",
         [0.15, 0.10, 0.90, 0.15, 0.85, 0.80, 0.85, 0.45, 0.15],
         TOXIC, -22.0, 0.06, spread=0.050, fija=True, regiones=[4]),

    # --- insectos: la larva alimenta, el enjambre pica -----------------
    kind("larva",         INSECTO, FOOD, +5.0, 0.50),
    kind("enjambre",      INSECTO, TOXIC, -4.0, 0.45,
         acritud=+0.28, temperatura=+0.18, dureza=-0.20),
]

# Referencia: pago esperado de un encuentro a ciegas en el mundo pequeño
# original (8 tipos). Que el mundo grande lo respete significa que crece
# en variedad, no en dureza.
REFERENCIA = 2.25


def expected_payoff(kinds):
    prey = [k for k in kinds if k["affordance"] != PREDATOR]
    total = sum(k["abundance"] for k in prey)
    return sum(k["payoff"] * k["abundance"] for k in prey) / total


def calibrate(kinds, target=REFERENCIA):
    """Escala la abundancia de los toxicos hasta igualar la referencia.

    Al pasar de 8 tipos a 16 se duplicaron las trampas, y con ellas la
    dureza del mundo: el pago esperado de un encuentro a ciegas caia de
    +2.25 a +1.03. Eso habria confundido dos cosas distintas — mundo mas
    RICO y mundo mas CRUEL — y cualquier cambio en los resultados seria
    inatribuible.

    Con `f` como factor sobre las abundancias toxicas, el pago esperado es

        (F + f*T) / (A_F + f*A_T) = objetivo

    que es lineal en f y se despeja directamente. No hay busqueda ni
    ajuste a ojo: sale un numero.
    """
    prey = [k for k in kinds if k["affordance"] != PREDATOR]
    tox = [k for k in prey if k["affordance"] == TOXIC
           and not k.get("fixed_abundance")]
    ben = [k for k in prey if k["affordance"] != TOXIC
           or k.get("fixed_abundance")]
    F = sum(k["payoff"] * k["abundance"] for k in ben)
    A_F = sum(k["abundance"] for k in ben)
    T = sum(k["payoff"] * k["abundance"] for k in tox)
    A_T = sum(k["abundance"] for k in tox)
    denom = T - target * A_T
    if denom == 0:
        return 1.0
    f = (target * A_F - F) / denom
    if not (0.05 <= f <= 20.0):
        raise SystemExit(f"factor de calibracion absurdo ({f:.3f}); "
                         "revisa los pagos antes de seguir")
    for k in tox:
        k["abundance"] = round(k["abundance"] * f, 4)
    return f


def main():
    factor = calibrate(KINDS)
    ev = expected_payoff(KINDS)
    spec = {
        "name": "Uqbar",
        "version": 2,
        "note": ("El mundo. Contiene FISICA, no significados: vectores "
                 "sensoriales, afordancias y costes. Los campos 'name' "
                 "existen SOLO para las metricas -- ningun agente los ve "
                 "jamas. Meter aqui palabras, conceptos o enseñanzas seria "
                 "regalarle al modelo justo lo que debe emerger."),
        "design": ("Cada familia sensorial contiene una trampa: un par casi "
                   "indistinguible con afordancias opuestas. Es el motor de "
                   "la formacion de conceptos."),
        "expected_payoff": round(ev, 3),
        "toxic_calibration": round(factor, 4),
        "senses": [list(s) for s in SENSES],
        "places": [{"name": n, "cost": c, "x": x, "y": y}
                   for n, c, x, y in PLACES],
        "kinds": KINDS,
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uqbar.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)

    print(f"escrito {out}")
    loc = [k["name"] for k in KINDS if "regions" in k]
    print(f"  {len(KINDS)} tipos en 8 familias, {len(PLACES)} lugares con "
          f"coordenadas, {len(SENSES)} sentidos")
    print(f"  tipos LOCALIZADOS (solo en ciertas regiones): {', '.join(loc)}")
    tox = sum(k["abundance"] for k in KINDS if k["affordance"] == TOXIC)
    tot = sum(k["abundance"] for k in KINDS if k["affordance"] != PREDATOR)
    print(f"  pago esperado a ciegas: {ev:+.3f}  "
          f"(referencia: {REFERENCIA:+.2f})")
    print(f"  abundancia toxica escalada x{factor:.3f} -> "
          f"{tox / tot:.1%} de los encuentros son trampa")


if __name__ == "__main__":
    main()
