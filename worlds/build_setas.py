#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Construye un mundo a partir de setas REALES.

    python worlds/build_setas.py            # 48 especies, las de familias trampa
    python worlds/build_setas.py --todas    # las 173

POR QUE ESTE DATASET
--------------------
Uqbar lo diseñe a mano con un principio: «cada familia contiene una
trampa» — dentro de un grupo que se percibe parecido hay algo que mata.
Era una invencion mia para que distinguir finamente tuviera valor de
supervivencia.

Resulta que eso es micologia. En Amanita conviven la oronja (comestible,
excelente) y la phalloides (mortal), y se parecen lo bastante como para
que la confusion sea la primera causa de muerte por setas en Europa. El
`Secondary Mushroom Dataset` (Wagner, Heider, Hattab — 173 especies del
libro de Hardin, CC BY 4.0) trae para cada especie sus rangos de rasgos
FISICOS y si es comestible o venenosa.

Asi que el mundo deja de ser un invento con la estructura que me convenia
y pasa a tener la estructura que tiene la realidad. Es una prueba mas
dura: yo no elegi que se parece a que.

QUE RESPETA LA REGLA 1
----------------------
«A los agentes no se les regala nada. El mundo contiene fisica — vectores
sensoriales, afordancias, costes — nunca significados.»

Cada dimension sensorial de aqui es una propiedad MEDIBLE de la seta:
diametro del sombrero en cm, altura del pie en cm, color del sombrero
convertido a luminosidad/rojez/verdor, si magulla al tocarla. El nombre
de la especie («Fly Agaric») viaja al JSON solo para las metricas, igual
que en Uqbar, y el modelo no lo lee nunca.

LO QUE NO SALE DEL DATASET, Y VA DECLARADO
------------------------------------------
1. Los COSTES DE VIAJE y las coordenadas de los habitats. El dataset dice
   en que habitats sale cada especie, pero no a que distancia esta un
   prado de un bosque. Las distancias son nuestras.
2. Los DEPREDADORES y el AGUA. El dataset es de hongos; no trae ni
   depredadores ni bebida. Sin depredador no hay canal de alarma y sin
   agua no hay una segunda afordancia que competir. Se añaden cuatro
   tipos sinteticos, marcados con `sintetico: true` en el JSON.
3. La MAGNITUD del pago. El dataset da comestible/venenosa, binario. La
   magnitud se escala con el tamaño del sombrero: una seta grande
   alimenta mas, y una seta grande venenosa mata mas. Es una decision
   nuestra, defendible pero nuestra.

LO QUE SALE DEL DATASET
-----------------------
Los 12 rasgos sensoriales, el signo del pago, en que habitats aparece
cada especie, y la estructura de parecidos — que es lo que importa.
"""

import argparse
import csv
import json
import math
import os
import random
import re

AQUI = os.path.dirname(os.path.abspath(__file__))
FUENTE = os.path.join(os.path.dirname(AQUI), "data", "raw",
                      "MushroomDataset", "primary_data.csv")
SALIDA = os.path.join(AQUI, "setas.json")

# --- de codigo del dataset a magnitud perceptible ---------------------
#
# Los colores se convierten a lo que un ojo mide, no a la etiqueta: una
# terna (luminosidad, rojez, verdor). Asi dos setas de colores parecidos
# quedan cerca en el espacio sensorial sin que nadie diga que "marron" y
# "buff" se parecen — se parecen porque sus numeros se parecen.
COLOR = {
    "k": (0.06, 0.50, 0.50),   # negro
    "n": (0.36, 0.62, 0.38),   # marron
    "b": (0.74, 0.58, 0.46),   # buff
    "g": (0.55, 0.50, 0.50),   # gris
    "r": (0.46, 0.18, 0.88),   # verde
    "p": (0.76, 0.80, 0.44),   # rosa
    "u": (0.38, 0.64, 0.30),   # purpura
    "e": (0.40, 0.96, 0.14),   # rojo
    "w": (0.96, 0.50, 0.50),   # blanco
    "y": (0.86, 0.70, 0.74),   # amarillo
    "l": (0.42, 0.20, 0.34),   # azul
    "o": (0.70, 0.86, 0.42),   # naranja
    "f": (0.50, 0.50, 0.50),   # ninguno / ausente
}

# cuanto sobresale el sombrero: hundido 0, esferico 1
FORMA = {"s": 0.05, "f": 0.28, "x": 0.60, "b": 0.52, "c": 0.78,
         "p": 0.92, "o": 0.50}

# como se nota al tacto: pulido 0, escamoso 1
SUPERFICIE = {"h": 0.02, "s": 0.08, "k": 0.18, "t": 0.26, "e": 0.36,
              "l": 0.46, "i": 0.54, "w": 0.62, "g": 0.74, "y": 0.92,
              "f": 0.30}

# laminas apretadas o separadas
ESPACIADO = {"c": 0.85, "d": 0.25, "f": 0.50}

SENTIDOS = [
    ["vista", "luminosidad"],      # 0  color del sombrero
    ["vista", "rojez"],            # 1
    ["vista", "verdor"],           # 2
    ["vista", "tamaño"],           # 3  diametro del sombrero (cm)
    ["vista", "altura"],           # 4  altura del pie (cm)
    ["vista", "grosor"],           # 5  anchura del pie (mm)
    ["vista", "convexidad"],       # 6  forma del sombrero
    ["tacto", "aspereza"],         # 7  superficie del sombrero
    ["vista", "laminas_claras"],   # 8  color de las laminas
    ["vista", "laminas_juntas"],   # 9  espaciado de las laminas
    ["vista", "anillo"],           # 10 tiene anillo o no
    ["tacto", "magulla"],          # 11 magulla o sangra al tocarla
]

# habitats reales del dataset. El coste y las coordenadas son nuestros:
# el dataset no dice a que distancia esta un prado de un bosque.
HABITATS = [
    ("d", "bosque",  3.4, 0.22, 0.78),
    ("g", "hierbas", 0.9, 0.44, 0.52),
    ("m", "prado",   1.8, 0.68, 0.40),
    ("l", "hojarasca", 2.6, 0.30, 0.62),
    ("p", "senda",   1.2, 0.56, 0.66),
    ("h", "brezal",  4.1, 0.14, 0.30),
    ("u", "urbano",  2.0, 0.80, 0.72),
    ("w", "yermo",   4.6, 0.86, 0.18),
]

# Sinteticos. NO salen del dataset y van marcados como tales en el JSON.
# Sin depredador no hay canal de alarma; sin agua no hay una segunda
# afordancia con la que competir. Los prototipos se colocan LEJOS del
# grueso de las setas para que no compitan por el mismo espacio.
SINTETICOS = [
    {"name": "depredador_rapido", "affordance": "depredador",
     "payoff": -24.0, "abundance": 0.30, "spread": 0.07,
     "prototype": [0.10, 0.90, 0.05, 0.95, 0.90, 0.95, 0.95, 0.90,
                   0.10, 0.10, 0.00, 0.95]},
    {"name": "depredador_lento", "affordance": "depredador",
     "payoff": -16.0, "abundance": 0.22, "spread": 0.08,
     "prototype": [0.20, 0.75, 0.10, 0.88, 0.75, 0.88, 0.85, 0.80,
                   0.20, 0.15, 0.00, 0.85]},
    {"name": "agua", "affordance": "agua", "payoff": 4.0, "abundance": 0.70, "spread": 0.05,
     "prototype": [0.90, 0.15, 0.20, 0.05, 0.05, 0.05, 0.05, 0.02,
                   0.90, 0.05, 0.00, 0.05]},
    {"name": "piedra", "affordance": "inerte", "payoff": 0.0,
     "abundance": 0.55, "spread": 0.09,
     "prototype": [0.45, 0.48, 0.48, 0.55, 0.10, 0.60, 0.35, 0.70,
                   0.45, 0.50, 0.00, 0.10]},
]


# ---------------------------------------------------------------------
# lectura del dataset
# ---------------------------------------------------------------------

def _lista(celda):
    """`[x, f]` -> ['x','f'];  `[10, 20]` -> [10.0, 20.0];  '' -> []."""
    celda = (celda or "").strip()
    if not celda:
        return []
    dentro = celda.strip("[]")
    if not dentro:
        return []
    return [t.strip() for t in dentro.split(",") if t.strip()]


def _rango(celda, por_defecto=(0.0, 0.0)):
    vals = []
    for t in _lista(celda):
        try:
            vals.append(float(t))
        except ValueError:
            pass
    if not vals:
        return por_defecto
    return (min(vals), max(vals))


def _medio(codigos, tabla, por_defecto=0.5):
    """Media de los valores posibles. Una especie con sombrero pardo o
    rojizo cae en medio, que es lo que se ve de lejos."""
    vals = [tabla[c] for c in codigos if c in tabla]
    return sum(vals) / len(vals) if vals else por_defecto


def _color_medio(codigos):
    ternas = [COLOR[c] for c in codigos if c in COLOR]
    if not ternas:
        return (0.5, 0.5, 0.5)
    return tuple(sum(t[i] for t in ternas) / len(ternas) for i in range(3))


def leer_especies(ruta):
    with open(ruta, encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh, delimiter=";"))
    fuera = []
    for f in filas:
        nombre = (f.get("name") or "").strip()
        if not nombre:
            continue
        fuera.append({
            "familia": (f.get("family") or "").strip(),
            "nombre": nombre,
            "venenosa": (f.get("class") or "").strip().lower() == "p",
            "diametro": _rango(f.get("cap-diameter"), (5.0, 10.0)),
            "altura": _rango(f.get("stem-height"), (5.0, 10.0)),
            "grosor": _rango(f.get("stem-width"), (10.0, 20.0)),
            "forma": _lista(f.get("cap-shape")),
            "superficie": _lista(f.get("Cap-surface")),
            "color": _lista(f.get("cap-color")),
            "magulla": _lista(f.get("does-bruise-or-bleed")),
            "lam_color": _lista(f.get("gill-color")),
            "lam_esp": _lista(f.get("gill-spacing")),
            "anillo": _lista(f.get("has-ring")),
            "habitats": _lista(f.get("habitat")),
            "estaciones": _lista(f.get("season")),
        })
    return fuera


# ---------------------------------------------------------------------
# de especie a tipo del mundo
# ---------------------------------------------------------------------

def _norm(v, lo, hi):
    if hi <= lo:
        return 0.5
    return max(0.0, min(1.0, (v - lo) / (hi - lo)))


def prototipo(sp, escalas):
    d_lo, d_hi, a_lo, a_hi, g_lo, g_hi = escalas
    lum, rojo, verde = _color_medio(sp["color"])
    lam_lum = _color_medio(sp["lam_color"])[0]
    diam = sum(sp["diametro"]) / 2.0
    alt = sum(sp["altura"]) / 2.0
    gro = sum(sp["grosor"]) / 2.0
    return [
        round(lum, 4),
        round(rojo, 4),
        round(verde, 4),
        round(_norm(diam, d_lo, d_hi), 4),
        round(_norm(alt, a_lo, a_hi), 4),
        round(_norm(gro, g_lo, g_hi), 4),
        round(_medio(sp["forma"], FORMA), 4),
        round(_medio(sp["superficie"], SUPERFICIE, 0.3), 4),
        round(lam_lum, 4),
        round(_medio(sp["lam_esp"], ESPACIADO), 4),
        round(1.0 if "t" in sp["anillo"] else 0.0, 4),
        round(1.0 if "t" in sp["magulla"] else 0.0, 4),
    ]


def dispersion(sp, escalas):
    """Cuanto varia un ejemplar dentro de su especie.

    Sale de los RANGOS del dataset: una especie cuyo sombrero mide de 5 a
    20 cm es mas variable que una que mide de 8 a 10, y eso hace que sea
    genuinamente mas dificil de reconocer. No es un numero que yo elija.
    """
    d_lo, d_hi, a_lo, a_hi, g_lo, g_hi = escalas
    anchos = [
        _norm(sp["diametro"][1], d_lo, d_hi) - _norm(sp["diametro"][0], d_lo, d_hi),
        _norm(sp["altura"][1], a_lo, a_hi) - _norm(sp["altura"][0], a_lo, a_hi),
        _norm(sp["grosor"][1], g_lo, g_hi) - _norm(sp["grosor"][0], g_lo, g_hi),
    ]
    # tambien cuenta la ambigüedad nominal: una especie que puede ser de
    # cuatro colores es mas escurridiza que una que solo es blanca
    amb = (len(sp["color"]) + len(sp["forma"]) + len(sp["superficie"])) / 3.0
    base = sum(anchos) / 3.0
    return round(max(0.035, min(0.16, 0.035 + 0.16 * base + 0.012 * amb)), 4)


def pago(sp, escalas):
    """Comestible o venenosa sale del dataset; la MAGNITUD la ponemos
    nosotros, escalada con el tamaño. Una seta grande alimenta mas; una
    seta grande venenosa hace mas daño."""
    d_lo, d_hi = escalas[0], escalas[1]
    tam = _norm(sum(sp["diametro"]) / 2.0, d_lo, d_hi)
    if sp["venenosa"]:
        return round(-(6.0 + 20.0 * tam), 2)
    return round(2.5 + 8.0 * tam, 2)


def abundancia(sp):
    """Cuanto sale al monte: mas habitats y mas estaciones, mas frecuente."""
    h = len(sp["habitats"]) or 1
    e = len(sp["estaciones"]) or 1
    return round(min(1.0, 0.10 + 0.10 * h + 0.06 * e), 4)


# ---------------------------------------------------------------------
# seleccion
# ---------------------------------------------------------------------

def familias_trampa(especies):
    """Familias que contienen a la vez comestibles y venenosas.

    Son las unicas donde distinguir finamente vale la vida. Es el
    principio de diseño de Uqbar, pero ahora lo dicta el dataset.
    """
    por_fam = {}
    for sp in especies:
        por_fam.setdefault(sp["familia"], []).append(sp)
    return {f: g for f, g in por_fam.items()
            if any(s["venenosa"] for s in g) and any(not s["venenosa"] for s in g)}


def elegir(especies, cuantas, rng):
    """Subconjunto que conserva la estructura de trampa.

    Prioriza familias mixtas y, dentro de cada una, el par mas PARECIDO
    entre una comestible y una venenosa — que es exactamente la confusion
    que mata gente de verdad.
    """
    if cuantas is None or cuantas >= len(especies):
        return list(especies)
    escalas = _escalas(especies)
    trampa = familias_trampa(especies)
    elegidas, vistas = [], set()

    for fam, grupo in sorted(trampa.items()):
        buenas = [s for s in grupo if not s["venenosa"]]
        malas = [s for s in grupo if s["venenosa"]]
        mejor, mejor_d = None, 1e9
        for b in buenas:
            pb = prototipo(b, escalas)
            for m in malas:
                pm = prototipo(m, escalas)
                d = math.dist(pb, pm)
                if d < mejor_d:
                    mejor, mejor_d = (b, m), d
        if mejor:
            for s in mejor:
                if s["nombre"] not in vistas:
                    vistas.add(s["nombre"])
                    elegidas.append(s)

    resto = [s for s in especies if s["nombre"] not in vistas]
    rng.shuffle(resto)
    for s in resto:
        if len(elegidas) >= cuantas:
            break
        elegidas.append(s)
    return elegidas[:cuantas]


def _escalas(especies):
    d = [x for s in especies for x in s["diametro"]]
    a = [x for s in especies for x in s["altura"]]
    g = [x for s in especies for x in s["grosor"]]
    return (min(d), max(d), min(a), max(a), min(g), max(g))


# ---------------------------------------------------------------------

def _slug(nombre):
    s = re.sub(r"[^a-z0-9]+", "_", nombre.lower()).strip("_")
    return s or "sp"


def construir(especies, semilla=7):
    rng = random.Random(semilla)
    escalas = _escalas(especies)
    codigo_a_idx = {c: i for i, (c, *_r) in enumerate(HABITATS)}

    kinds = []
    for sp in especies:
        regiones = sorted({codigo_a_idx[h] for h in sp["habitats"]
                           if h in codigo_a_idx})
        k = {
            "name": _slug(sp["nombre"]),
            "prototype": prototipo(sp, escalas),
            "spread": dispersion(sp, escalas),
            "affordance": "toxico" if sp["venenosa"] else "alimento",
            "payoff": pago(sp, escalas),
            "abundance": abundancia(sp),
            # procedencia — para las metricas y para poder auditar
            "especie": sp["nombre"],
            "familia": sp["familia"],
            "fuente": "secondary-mushroom-dataset",
        }
        if regiones:
            k["regions"] = regiones
        kinds.append(k)

    for s in SINTETICOS:
        k = dict(s)
        k["sintetico"] = True
        k["fuente"] = "añadido por nosotros"
        kinds.append(k)

    places = [{"name": n, "cost": c, "x": x, "y": y}
              for _c, n, c, x, y in HABITATS]

    venenosas = sum(1 for s in especies if s["venenosa"])
    mixtas = familias_trampa(especies)
    return {
        "name": "setas",
        "version": 1,
        "note": ("Mundo derivado del Secondary Mushroom Dataset (Wagner, "
                 "Heider & Hattab; 173 especies del libro de Hardin, "
                 "CC BY 4.0). Los rasgos sensoriales y el signo del pago "
                 "salen del dataset; los costes de viaje, la magnitud del "
                 "pago y los cuatro tipos sinteticos son nuestros y van "
                 "marcados."),
        "design": ("La trampa no la puse yo: en las familias mixtas "
                   "conviven comestibles y venenosas que se parecen. "
                   "Distinguirlas finamente vale la vida, igual que en "
                   "Uqbar, pero aqui la estructura de parecidos la dicta "
                   "la micologia."),
        "fuente": {
            "dataset": "Secondary Mushroom Dataset",
            "autores": "D. Wagner, D. Heider, G. Hattab",
            "licencia": "CC BY 4.0",
            "url": "https://archive.ics.uci.edu/dataset/848/secondary+mushroom+dataset",
            "especies_totales": 173,
        },
        "resumen": {
            "especies_usadas": len(especies),
            "venenosas": venenosas,
            "comestibles": len(especies) - venenosas,
            "familias_mixtas": len(mixtas),
            "sinteticos": len(SINTETICOS),
        },
        "senses": SENTIDOS,
        "places": places,
        "kinds": kinds,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--todas", action="store_true",
                    help="las 173 especies, no el subconjunto")
    ap.add_argument("--cuantas", type=int, default=48)
    ap.add_argument("--salida", default=SALIDA)
    ap.add_argument("--semilla", type=int, default=7)
    args = ap.parse_args()

    if not os.path.isfile(FUENTE):
        raise SystemExit(
            f"no encuentro {FUENTE}\n"
            "Descargalo con:\n"
            "  curl -sL -o data/raw/sec.zip "
            "https://archive.ics.uci.edu/static/public/848/"
            "secondary+mushroom+dataset.zip\n"
            "y descomprime el zip anidado en data/raw/")

    especies = leer_especies(FUENTE)
    elegidas = elegir(especies, None if args.todas else args.cuantas,
                      random.Random(args.semilla))
    mundo = construir(elegidas, args.semilla)

    with open(args.salida, "w", encoding="utf-8") as fh:
        json.dump(mundo, fh, ensure_ascii=False, indent=1)

    r = mundo["resumen"]
    print(f"  {args.salida}")
    print(f"  {r['especies_usadas']} especies "
          f"({r['comestibles']} comestibles, {r['venenosas']} venenosas) "
          f"+ {r['sinteticos']} sinteticos")
    print(f"  {r['familias_mixtas']} familias con comestibles Y venenosas")
    print(f"  {len(SENTIDOS)} sentidos, {len(HABITATS)} habitats reales")

    # los pares que matan: comestible y venenosa que se parecen
    escalas = _escalas(elegidas)
    pares = []
    for fam, grupo in sorted(familias_trampa(elegidas).items()):
        for b in (s for s in grupo if not s["venenosa"]):
            for m in (s for s in grupo if s["venenosa"]):
                pares.append((math.dist(prototipo(b, escalas),
                                        prototipo(m, escalas)),
                              b["nombre"], m["nombre"], fam))
    pares.sort()
    if pares:
        print("\n  los sosias mas peligrosos (distancia sensorial):")
        for d, b, m, fam in pares[:6]:
            print(f"    {d:.3f}  {b}  ~  {m}   [{fam}]")


if __name__ == "__main__":
    main()
