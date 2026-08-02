#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Config — todos los parametros del modelo en un solo sitio.

Cualquier numero magico que aparezca en otro modulo es un bug: deberia
estar aqui, para que un experimento sea reproducible con solo volcar
este objeto al fichero de resultados.
"""

from dataclasses import dataclass, asdict


@dataclass
class Config:
    # --- percepcion / formacion de conceptos (Fase 1) -----------------
    perception_noise: float = 0.05   # ruido gaussiano por dimension al percibir
    vigilance: float = 0.55          # radio de categoria inicial (gen heredable)
    vigilance_mut: float = 0.04      # desviacion de la mutacion del gen
    vigilance_min: float = 0.15
    vigilance_max: float = 1.10
    proto_lr: float = 0.12           # cuanto se mueve el prototipo hacia el ejemplo
    max_categories: int = 40         # techo cognitivo
    surprise_split: float = 8.0      # discrepancia que delata una categoria gruesa
    p_split: float = 0.60            # prob. de partirla al sorprenderse
    radius_min: float = 0.12         # suelo: la frontera no puede afinarse sin limite

    # --- lexico (Fase 3) ----------------------------------------------
    lex_init_w: float = 0.50         # peso inicial de una asociacion nueva
    lex_lr: float = 0.18             # refuerzo por co-observacion
    lex_inhib_form: float = 0.28     # competencia entre FORMAS de un significado
    #   ^ alta => convergencia a una sola palabra por concepto (mata sinonimia)
    lex_inhib_meaning: float = 0.04  # competencia entre SIGNIFICADOS de una forma
    #   ^ baja a proposito => la polisemia esta PERMITIDA, no forzada
    social_exp: float = 0.4          # cuanto pesa CUANTA GENTE usa una forma
    #   ^ 0.4 y no mas alto: a 0.8 la coherencia sube un poco (0.660 frente
    #     a 0.640) pero los aciertos BAJAN (0.609 frente a 0.618) y se
    #     pierde la ganancia de composicionalidad. Forzar demasiado la
    #     convencion mayoritaria empieza a costar precision. El optimo no
    #     es el maximo.
    #     0 = apagado (produce la forma de mayor peso, sin mas).
    #     El diagnostico mostro que el techo de coherencia no es un
    #     proceso a medio camino sino un EQUILIBRIO con ~3 palabras vivas
    #     por cosa, repartidas y empatadas (hasta 0.46/0.46). La inhibicion
    #     lateral es local y simetrica: cada uno refuerza lo que oye y
    #     debilita el resto EN SU CABEZA, asi que en una banda de 8 con
    #     encuentros al azar nadie llega a ver cual es la mayoria global y
    #     un empate 3-3 no se rompe nunca.
    #     Contar de cuanta GENTE DISTINTA se ha oido una forma — no cuantas
    #     veces — convierte una ventaja 3-2 en una señal detectable, y la
    #     realimentacion hace el resto. Es como se difunden las variantes
    #     de verdad: por numero de hablantes, no por frecuencia bruta.
    lex_prune: float = 0.05          # peso por debajo del cual se olvida
    lex_confidence: float = 0.55     # peso minimo para fiarse de lo que oyes
    pragmatica: float = 0.0          # cuanto pesa el contexto al desambiguar
    #   ^ APAGADO por defecto, y por medicion propia. Con 0.6 la
    #     desambiguacion contextual registra 0.017 (SI en 0/12 semillas)
    #     mientras degrada tres criterios que si funcionaban:
    #     convencionalidad 6/12 -> 3/12, composicionalidad 9/12 -> 5/12,
    #     arbitrariedad 10/12 -> 8/12. El marcador global cae de 14/20 a
    #     12/20. El mecanismo se queda —es correcto y esta documentado—
    #     pero encenderlo empeora el modelo, y eso pesa mas que tener un
    #     criterio mas en PARCIAL.
    #
    #     La causa, medida: la polisemia de este modelo es NOMINAL. La
    #     brecha media entre la 1a y la 2a acepcion es 0.341 y solo el
    #     34.5% de los pares estan lo bastante parejos para que el
    #     contexto pudiera voltearlos. Sin ambigüedad real no hay nada
    #     que desambiguar.
    contexto_min: int = 12           # observaciones minimas para opinar del sitio
    #   ^ FASE 10. Una forma polisemica no significa siempre lo mismo: el
    #     oyente sabe DONDE esta pasando la conversacion, y sabe por
    #     experiencia que cosas salen en cada sitio. Si `vrera` cubre el
    #     fruto dulce y el amargo, y en esta region solo ha visto el dulce,
    #     lo razonable es leer «dulce». A 0 se ablaciona: vuelve a ganar
    #     siempre el significado de mas peso, sea cual sea la situacion.
    p_invent: float = 0.85           # prob. de acuñar si quiere hablar y no tiene forma
    listen_before_speak: int = 0     # señales que hay que oir antes de acuñar
    #   ^ la idea era que la comprension precediera a la produccion: un
    #     recien nacido que acuña palabra propia para todo inyecta
    #     variantes que compiten con las de la tribu. PERO con cualquier
    #     valor > 0 la primera generacion se bloquea: nadie ha oido nada,
    #     asi que nadie habla, y no arranca ninguna lengua (coherencia
    #     0.000 medida con 20). Se deja en 0 y anotado: el problema no es
    #     que los novatos acuñen, es cuanto tardan en ADOPTAR.
    p_align: float = 1.0             # prob. de usar el alineamiento supervisado

    # --- descripcion (Fase 8) -----------------------------------------
    p_describe: float = 0.6          # describir cuando no te fias de tu palabra
    #   ^ se describe SOLO si el peso de la mejor forma propia para esa
    #     categoria no llega a `lex_confidence`. Es lo que uno hace cuando
    #     no sabe como se llama algo: enumerar como es.
    describe_min_morphs: int = 20    # co-observaciones para fiarse de una nube
    desc_refina: float = 0.5         # cuanto debe AFINAR un morfo repetido
    #   ^ un segundo morfo sobre la misma dimension entra si aporta un
    #     valor distinto (mas de 0.5 desviaciones). A 0 se admite todo y
    #     vuelven las descripciones tautologicas; muy alto equivale a la
    #     condicion vieja, que mataba el 16% de todas las descripciones.
    described_radius: float = 1.5    # el radio de un concepto oido, x vigilancia
    #   ^ ancho a proposito: un concepto que llega por el oido esta
    #     infra-especificado y no debe competir de tu a tu con los vistos.
    uptake_penalty: float = 0.80     # castigo a la forma que el oyente ignoro

    # --- metafora (Fase 4) --------------------------------------------
    p_metaphor: float = 0.55         # estirar una palabra vecina en vez de acuñar
    #   ^ a 0.0 se ablaciona la metafora: los agentes solo acuñan
    metaphor_radius: float = 0.70    # hasta donde alcanza el "se parece a"
    #   ^ distancia maxima entre prototipos para prestar la palabra. Muy
    #     grande => cualquier cosa nombra cualquier cosa y la palabra
    #     pierde valor informativo. Muy pequeña => nunca se estira nada.

    # --- gramatica (Fase 5) -------------------------------------------
    p_compose: float = 0.50          # al inventar de cero: ¿componer o bloque opaco?
    #   ^ es un prior neutro, no un sesgo. Lo que medimos no es como se
    #     inventa sino que sobrevive a la transmision.
    morph_min: int = 2               # un morfo mas corto que esto no es una pieza
    morph_max: int = 8               # ni mas largo que esto
    #   ^ sin este techo la induccion se realimenta: el trozo que varia
    #     entre dos señales se acepta como morfo, las señales se alargan,
    #     y el siguiente trozo variable es aun mayor. Llegamos a ver
    #     "morfos" de 325 caracteres. Eso no es una pieza, es una frase
    #     memorizada — y ademas dispara el coste de segmentar, que crece
    #     con la longitud.
    chunk_window: int = 40           # cuantas señales pasadas se alinean
    chunk_max_hits: int = 2          # confirmaciones por señal oida

    # --- sintaxis (Fase 6) --------------------------------------------
    order_decay: float = 0.12        # cuanto pierde un orden que no cuadro
    parse_orders: int = 2            # cuantas gramaticas prueba un oyente

    # --- recursividad (Fase 7) ----------------------------------------
    max_depth: int = 3               # encajes maximos por enunciado
    #   ^ tope practico, no teorico: la regla no tiene limite, pero hay
    #     que parar de recorrer en algun sitio.
    p_quote: float = 0.5             # prob. de marcar como oido lo que se oyo
    hearsay_lr: float = 0.05         # peso de lo que a uno le CONTARON que contaron
    #   ^ menor que testimony_lr, que a su vez es menor que value_lr. Tres
    #     escalones: lo vivido pesa mas que lo oido, y lo oido mas que el
    #     rumor. Sin ese descuento, un error se amplifica al repetirse.
    #   ^ los seis ordenes (SVO, SOV, VSO...) compiten por peso dentro de
    #     cada agente. Nadie decreta cual gana: gana el que interpreta
    #     bien lo que se oye, y la tribu converge por realimentacion.
    memory_events: int = 60          # sucesos que recuerda un agente
    memory_salience: float = 1.5     # |valor| minimo para molestarse en recordar
    #   ^ la memoria es SELECTIVA. Sin esto se llenaba de «habia algo en
    #     tal sitio», que es cierto y no sirve para nada: al recordar, casi
    #     siempre salia una trivialidad y el testimonio no enseñaba nunca.
    #     Se recuerda lo que tuvo consecuencias.
    p_report_past: float = 0.35      # prob. de contar algo pasado en vez de presente
    testimony_lr: float = 0.12       # cuanto pesa lo oido frente a lo vivido
    #   ^ SIEMPRE menor que value_lr: de oidas se aprende, pero menos que
    #     sufriendolo. Si fuera igual, el testimonio seria telepatia.
    grammar_memory: int = 80         # señales oidas que se guardan para alinear
    hol_capacity: int = 60           # cuantas señales ENTERAS caben en memoria
    #   ^ EL MANDO DEL CUELLO DE BOTELLA. 0 = memoria infinita.
    #     Los morfos inducidos no cuentan aqui: son pocos y sirven para
    #     todo. Apretar esto hace inviable memorizar cada combinacion por
    #     separado, que es justo la presion que puede forzar una gramatica.

    # --- economia de la supervivencia (Fase 2) ------------------------
    energy_start: float = 60.0
    energy_max: float = 130.0
    metabolic_cost: float = 11.0     # por generacion
    flee_cost: float = 2.0           # huir de un depredador
    speak_cost: float = 0.15         # emitir una señal cuesta
    kin_share: float = 0.35          # el hablante cobra parte del resultado del oyente
    kin_death_penalty: float = 8.0   # coste para el hablante si el oyente muere
    predator_death_p: float = 0.12   # si NO huye
    predator_death_p_fled: float = 0.02
    predator_damage: float = 5.0     # si no huye y sobrevive

    # --- decision -----------------------------------------------------
    p_explore: float = 0.45          # acercarse a lo desconocido (sin info)
    p_explore_against: float = 0.05  # acercarse pese a esperar algo malo
    value_lr: float = 0.30           # EWMA del valor aprendido por categoria
    speak_threshold: float = 0.40    # |valor esperado| * kin_share > speak_cost
    p_babble: float = 0.25           # hablar de lo desconocido (bootstrap)
    novel_count: int = 3             # categoria "nueva" si se ha visto <= N veces

    # --- demografia ---------------------------------------------------
    tribe_size: int = 8
    max_pop: int = 8
    #   ^ BANDA PEQUEÑA, y no por gusto. La coherencia lexica depende del
    #     tamaño de la comunidad de forma monotona y fuerte — 30: 0.116,
    #     18: 0.225, 12: 0.301, 10: 0.40, 8: 0.53 — porque el juego de
    #     nombres converge en tiempo superlineal con el numero de
    #     hablantes. Ningun otro parametro que probamos mueve la
    #     coherencia (inhibicion mas fuerte la baja a 0.34; quitar el
    #     alineamiento, a 0.32). Ademas encaja con la etnografia: las
    #     bandas de cazadores-recolectores son de este orden.
    episodes_per_gen: int = 400
    #   ^ el numero de OPORTUNIDADES por generacion es fijo, no proporcional
    #     a la poblacion. Eso crea capacidad de carga: cuanta mas gente,
    #     menos le toca a cada uno. Sin esto la poblacion satura el techo en
    #     los dos brazos y la ablacion no puede distinguir nada.
    repro_threshold: float = 55.0
    repro_cost: float = 25.0
    child_energy: float = 25.0
    max_age: int = 30
    alarms_per_agent: float = 0.55   # encuentros con depredador por cabeza
    #   ^ POR CABEZA, no por episodio: el depredador busca a alguien,
    #     no a un parche. Si dependiera del presupuesto de forrajeo,
    #     no se podria subir la densidad de conversacion sin subir a
    #     la vez la mortalidad.

    # --- espacio (Fase 9) ---------------------------------------------
    wander: float = 0.035            # cuanto deriva un agente por generacion
    near_k: int = 4                  # con cuantos vecinos se puede encontrar
    #   ^ el oyente sale de los `near_k` mas cercanos, no de toda la tribu.
    #     Con grafo completo todos acababan viendolo todo y la transmision
    #     cultural no tenia nicho. Con vecindad, el saber se reparte por
    #     geografia. Prediccion: bajara la coherencia global (los juegos de
    #     nombres sobre retículas forman dominios) y apareceran dialectos.
    travel_scale: float = 6.0        # de distancia a coste energetico

    # --- mundo --------------------------------------------------------
    world: str = "uqbar"             # fichero en worlds/ (o ruta a un json)
    contact: int = 0                 # encuentros entre tribus por generacion
    # Los dos siguientes los fija el cargador del mundo al arrancar; no se
    # tocan a mano. Estan aqui para que queden volcados con el resto de
    # parametros y una corrida sea reproducible con solo este objeto.
    dim: int = 9
    n_places: int = 4

    def to_dict(self):
        return asdict(self)
