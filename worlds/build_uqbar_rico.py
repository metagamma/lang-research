#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de `uqbar_rico.json` — el genesis del regimen cooperativo.

Es `uqbar` con mas RIQUEZA, no con mas dureza. Dos cosas cambian respecto
al mundo original, y las dos apuntan a que emerjan mas clases de palabra
sin regalar ni una: se sigue respetando la Regla 1 (el fichero contiene
FISICA, nunca significados).

MAS SUSTANTIVOS
    Mas familias sensoriales -> mas tipos latentes -> mas morfos de
    categoria. Cada familia conserva su TRAMPA (un par casi indistinguible
    con afordancias opuestas), que es el unico motor de la formacion de
    conceptos de la Fase 1. Sin trampa, la particion optima seria trivial.

MAS ADJETIVOS
    Cuatro familias son GRADUADAS: ademas del par comestible/toxico llevan
    un tercer miembro que se aparta en UNA sola dimension (la fruta madura
    es mas grande y luminosa; la flor marchita, mas oscura y podrida; el
    hongo joven, mas pequeño; la baya verde, mas verde). Un morfo estirado
    por metafora hacia ese vecino cubre la region donde ambos coinciden y
    se aparta en la dimension que los separa — que es, exactamente, un
    adjetivo. No se declara la clase «adjetivo»; se crea la presion para
    que aparezca.

Se añaden tres sentidos sobre los nueve de uqbar (tamaño, podredumbre,
humedad): mas ejes perceptivos = mas propiedades sobre las que un morfo
atributivo puede especializarse.

    python worlds/build_uqbar_rico.py
"""

import json
import os

FOOD, WATER, TOXIC, PREDATOR, INERT = (
    "alimento", "agua", "toxico", "depredador", "inerte")

# 12 sentidos (9 de uqbar + tamaño, podredumbre, humedad). Nombres ASCII:
# se usan como kwargs de `kind()`, y conviene no depender de identificadores
# unicode.
SENSES = [
    ("vista", "luminosidad"), ("vista", "rojez"), ("vista", "verdor"),
    ("vista", "tamano"),
    ("olfato", "dulzor"), ("olfato", "acritud"), ("olfato", "podredumbre"),
    ("gusto", "amargor"), ("gusto", "salinidad"),
    ("tacto", "dureza"), ("tacto", "temperatura"), ("tacto", "humedad"),
]
D = {name: i for i, (_, name) in enumerate(SENSES)}

# Seis lugares con coordenadas (igual que uqbar): el coste sale de la
# distancia real y la cercania decide quien se encuentra con quien.
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
        d["regions"] = list(regiones)
    return d


#             lum  rojo verde tam  dulz acri podr amar  sal dur  temp hum
FRUTO   =    [0.70, 0.80, 0.20, 0.45, 0.85, 0.15, 0.10, 0.10, 0.20, 0.20, 0.50, 0.40]
RAIZ    =    [0.25, 0.35, 0.30, 0.55, 0.45, 0.30, 0.20, 0.35, 0.45, 0.75, 0.35, 0.35]
AGUA    =    [0.60, 0.10, 0.25, 0.20, 0.10, 0.10, 0.05, 0.05, 0.35, 0.05, 0.25, 0.95]
BESTIA  =    [0.40, 0.45, 0.15, 0.70, 0.30, 0.55, 0.30, 0.30, 0.60, 0.55, 0.80, 0.45]
PIEDRA  =    [0.35, 0.20, 0.15, 0.60, 0.05, 0.10, 0.05, 0.05, 0.25, 0.95, 0.30, 0.15]
FLOR    =    [0.85, 0.30, 0.65, 0.30, 0.70, 0.20, 0.15, 0.15, 0.10, 0.10, 0.45, 0.40]
HONGO   =    [0.45, 0.15, 0.10, 0.35, 0.35, 0.45, 0.40, 0.30, 0.30, 0.30, 0.40, 0.60]
INSECTO =    [0.30, 0.55, 0.20, 0.25, 0.20, 0.65, 0.35, 0.40, 0.50, 0.35, 0.65, 0.30]
BAYA    =    [0.75, 0.85, 0.25, 0.20, 0.75, 0.20, 0.15, 0.20, 0.15, 0.15, 0.45, 0.55]
HIERBA  =    [0.55, 0.25, 0.80, 0.40, 0.30, 0.35, 0.20, 0.30, 0.25, 0.20, 0.40, 0.50]

KINDS = [
    # --- frutos (GRADUADA): el maduro es mas grande y luminoso ---------
    kind("fruto_dulce",   FRUTO, FOOD,  +8.0, 1.00),
    kind("fruto_amargo",  FRUTO, TOXIC, -10.0, 0.60,
         dulzor=-0.30, acritud=+0.30, amargor=+0.35, rojez=-0.02),
    kind("fruto_maduro",  FRUTO, FOOD,  +6.0, 0.55,
         luminosidad=+0.15, rojez=+0.10, tamano=+0.22),

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

    # --- flores (GRADUADA): la marchita es oscura y podrida ------------
    kind("flor",          FLOR,  INERT, 0.0, 0.65),
    kind("flor_nectar",   FLOR,  FOOD,  +3.0, 0.45,
         dulzor=+0.22, luminosidad=-0.15),
    kind("flor_marchita", FLOR,  INERT, 0.0, 0.40,
         luminosidad=-0.25, verdor=-0.30, podredumbre=+0.28),

    # --- hongos (GRADUADA): el joven es mas pequeño --------------------
    kind("hongo",         HONGO, FOOD,  +7.0, 0.55, regiones=[4, 1]),
    kind("hongo_palido",  HONGO, TOXIC, -12.0, 0.38,
         luminosidad=+0.30, amargor=+0.25, dulzor=-0.18),
    kind("hongo_joven",   HONGO, FOOD,  +5.0, 0.40, regiones=[4, 1],
         tamano=-0.22, luminosidad=+0.10),

    # --- insectos: la larva alimenta, el enjambre pica -----------------
    kind("larva",         INSECTO, FOOD, +5.0, 0.50),
    kind("enjambre",      INSECTO, TOXIC, -4.0, 0.45,
         acritud=+0.28, temperatura=+0.18, dureza=-0.20),

    # --- bayas (GRADUADA): la negra y la verde son las malas -----------
    kind("baya_roja",     BAYA,  FOOD,  +5.0, 0.60),
    kind("baya_negra",    BAYA,  TOXIC, -7.0, 0.40,
         rojez=-0.40, luminosidad=-0.35, amargor=+0.30),
    kind("baya_verde",    BAYA,  TOXIC, -4.0, 0.35,
         verdor=+0.45, rojez=-0.30, dulzor=-0.30),

    # --- hierbas: la espinosa es dura y acre ---------------------------
    kind("hierba",        HIERBA, FOOD, +4.0, 0.60),
    kind("hierba_espinosa", HIERBA, TOXIC, -5.0, 0.40,
         dureza=+0.30, acritud=+0.25),

    # --- LO RARO Y LETAL -----------------------------------------------
    # Region sensorial que no ocupa nadie: un encuentro basta para
    # categorizarlo, pero aparece tan poco que la mayoria muere sin verlo.
    # Su abundancia NO entra en la calibracion (fija=True). Ver la nota
    # larga de build_uqbar.py sobre por que 0.06 y por que en region [4].
    kind("veneno_raro",
         [0.15, 0.10, 0.90, 0.30, 0.15, 0.85, 0.70, 0.80, 0.85, 0.45, 0.15, 0.40],
         TOXIC, -22.0, 0.06, spread=0.050, fija=True, regiones=[4]),
]

# Referencia: mismo pago esperado a ciegas que uqbar. Que el mundo rico lo
# respete significa que crece en variedad, no en dureza.
REFERENCIA = 2.25


def expected_payoff(kinds):
    prey = [k for k in kinds if k["affordance"] != PREDATOR]
    total = sum(k["abundance"] for k in prey)
    return sum(k["payoff"] * k["abundance"] for k in prey) / total


def calibrate(kinds, target=REFERENCIA):
    """Escala la abundancia de los toxicos hasta igualar la referencia.

    Lineal en el factor `f` sobre las abundancias toxicas; se despeja, no
    se busca. Identico al de build_uqbar.py.
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
    familias = ("frutos, raices, agua, bestias, minerales, flores, hongos, "
                "insectos, bayas, hierbas (+ veneno raro)")
    spec = {
        "name": "Uqbar rico",
        "version": 1,
        "note": ("El mundo del regimen cooperativo. Contiene FISICA, no "
                 "significados: vectores sensoriales, afordancias y costes. "
                 "Los campos 'name' existen SOLO para las metricas -- ningun "
                 "agente los ve jamas."),
        "design": ("Mas familias (mas sustantivos) y cuatro familias "
                   "GRADUADAS con un tercer miembro que se aparta en una "
                   "sola dimension (mas adjetivos). Cada familia conserva su "
                   "trampa comestible/toxico."),
        "expected_payoff": round(ev, 3),
        "toxic_calibration": round(factor, 4),
        "senses": [list(s) for s in SENSES],
        "places": [{"name": n, "cost": c, "x": x, "y": y}
                   for n, c, x, y in PLACES],
        "kinds": KINDS,
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "uqbar_rico.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)

    print(f"escrito {out}")
    graduadas = [k["name"] for k in KINDS if k["name"] in (
        "fruto_maduro", "flor_marchita", "hongo_joven", "baya_verde")]
    loc = [k["name"] for k in KINDS if "regions" in k]
    print(f"  {len(KINDS)} tipos en 11 familias, {len(PLACES)} lugares, "
          f"{len(SENSES)} sentidos")
    print(f"  familias: {familias}")
    print(f"  miembros GRADUADOS (presion de adjetivo): {', '.join(graduadas)}")
    print(f"  tipos LOCALIZADOS: {', '.join(loc)}")
    tox = sum(k["abundance"] for k in KINDS if k["affordance"] == TOXIC)
    tot = sum(k["abundance"] for k in KINDS if k["affordance"] != PREDATOR)
    print(f"  pago esperado a ciegas: {ev:+.3f}  (referencia: {REFERENCIA:+.2f})")
    print(f"  abundancia toxica escalada x{factor:.3f} -> "
          f"{tox / tot:.1%} de los encuentros son trampa")


if __name__ == "__main__":
    main()
