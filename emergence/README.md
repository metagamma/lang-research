# emergence — un modelo generativo del origen del lenguaje

> *Nothing in language exists unless it improves prediction,
> coordination or survival.*

Este paquete sustituye a `tribes_perception_myth.py`. El simulador
anterior demostraba que un léxico compartido converge; este pregunta
algo más difícil: **si el lenguaje no se le regala a nadie, ¿aparece? y
si aparece, ¿sirve para algo?**

Ese "¿sirve para algo?" es falsable, y la respuesta está más abajo.

---

## Qué se le quitó al modelo anterior

| antes | ahora |
|---|---|
| `CONCEPT_ROLES = ["sol", "agua", ...]` | no existe. El mundo tiene objetos, no conceptos |
| firma sensorial decorativa (solo aparecía en los mitos) | los rasgos sensoriales son lo **único** que el agente percibe |
| ambos agentes reciben el mismo `role` por telepatía | el hablante percibe; el oyente **no** |
| `fitness = coincidir con el consenso` | fitness = energía y descendencia. Nada más |
| `word_for: dict concepto -> palabra` | grafo bipartito con pesos: sinonimia y polisemia posibles |
| el léxico se heredaba genéticamente | el hijo nace mudo y aprende viviendo |

La `fitness` vieja era circular: el consenso se definía como la palabra
mayoritaria y el fitness premiaba estar en la mayoría. Convergía siempre,
con cualquier mundo, incluso con uno vacío. Aquí no hay ninguna función
que premie hablar parecido.

---

## Uqbar — el mundo en un fichero

El mundo se carga de `worlds/*.json`; no esta cableado en el codigo. Eso
separa la definicion del mundo del mecanismo, permite versionarlo y hace
comparables los experimentos entre mundos.

**La linea que ese fichero no cruza**: contiene FISICA, no significados.
Vectores sensoriales, afordancias, costes, abundancias. Nunca palabras,
conceptos ni enseñanzas. Meter ahi un inventario de saberes seria repetir
el error de `CONCEPT_ROLES = ["sol", "agua", ...]` con mas ceremonia: lo
que los agentes deben descubrir no se les puede entregar en un fichero.

`uqbar.json` lo genera `worlds/build_uqbar.py`, con un principio de
diseño explicito: **cada familia sensorial contiene una trampa**. Frutos,
raices, hongos, bestias, minerales, flores, insectos y agua — y dentro de
cada una, un par casi indistinguible con afordancias opuestas: uno
alimenta y el otro envenena, separados por uno o dos sentidos. Sin
trampas la particion optima seria trivial y la Fase 1 no tendria nada que
descubrir.

Al pasar de 8 a 16 tipos se duplicaron las trampas y el pago esperado de
un encuentro a ciegas caia de +2.25 a +1.03. Eso habria confundido dos
cosas distintas —mundo mas RICO y mundo mas CRUEL— y cualquier cambio en
los resultados seria inatribuible. El generador **despeja algebraicamente**
el factor de abundancia toxica que restaura la referencia. Sale un numero
(0.583), no un ajuste a ojo.

    python -m emergence.world            # inspeccionar el mundo cargado
    python worlds/build_uqbar.py         # regenerarlo

---

## Las fases implementadas

### Fase 1 — los conceptos emergen (`percept.py`)

El mundo son ocho tipos latentes que generan instancias como puntos en un
espacio sensorial continuo de 9 dimensiones (vista, olfato, gusto,
tacto). El agente ve el vector con ruido y nada más. Los nombres
`fruto_dulce`, `acechante`… existen solo en `metrics.py`, para que
nosotros podamos medir; el agente no los ve nunca.

Cada agente construye **su propia** partición por clustering incremental
con vigilancia (familia ART). Dos detalles importan:

- **radio por categoría**, no un umbral global;
- **match tracking**: cuando el resultado de consumir contradice lo
  esperado, esa categoría estaba mezclando dos realidades. La frontera se
  traza *a mitad de camino* entre el prototipo culpable y el ejemplo que
  lo desmintió, y nace una categoría nueva.

El mundo está diseñado con pares confundibles: `fruto_dulce` y
`fruto_amargo` distan 0.55 y solo se separan por olfato y gusto;
`bestia` y `acechante` distan 0.41. Un agente de vigilancia gruesa los
mezcla y se envenena. **La partición se afila solo donde el mundo castiga
no distinguir**, y se queda gruesa donde da igual. Nadie le dice cuántas
categorías debe tener.

> Nota de implementación: la primera versión usaba un factor de
> encogimiento fijo en vez de la regla del punto medio. Seguía recortando
> en cada sorpresa, pulverizaba la partición en decenas de categorías
> diminutas sin datos suficientes para estimar su valor, y **extinguía a
> la población entera**. La regla del punto medio se autolimita.

### Fase 2 — la comunicación la empuja la supervivencia (`episodes.py`)

No hay ningún *naming game*. Nadie ejecuta un protocolo. Hay agentes con
hambre y depredadores. La asimetría que lo hace todo posible:

    el HABLANTE percibe el objeto.
    el OYENTE no.

El oyente decide a ciegas: explorar cuesta (viajar, y lo que hay puede
envenenarte). El lenguaje es, literal y exclusivamente, **un sustituto de
la percepción a distancia**. Si no sirve para eso, no sirve para nada.

Dos reglas de aprendizaje, deliberadamente disjuntas:

- el **léxico** solo se refuerza por **co-observación** (oí la forma y
  luego vi el objeto). Nunca por el pago recibido.
- el **valor** solo se aprende **experimentándolo** (lo comí; no huí y me
  alcanzó). Nunca de oídas.

Por eso el lenguaje no puede colarse en la función de recompensa. Su
único canal causal hacia la supervivencia es permitir decidir sin
percibir. Si aun así la ablación detecta ventaja, la ventaja es real.

Hablar cuesta energía, y el hablante cobra una fracción del resultado del
oyente (parentesco). De ahí sale sin programarlo que **solo se hable de
lo que importa**: avisar de un fruto venenoso compensa, comentar una
piedra no.

### Fase 3 — el léxico como grafo con pesos (`lexicon.py`)

`w[(forma, categoría)] → peso`, con inhibición lateral (Steels) y dos
constantes distintas a propósito:

- `lex_inhib_form = 0.28` — competencia entre **formas** de un
  significado. Alta: es lo que hace converger a la tribu.
- `lex_inhib_meaning = 0.04` — competencia entre **significados** de una
  forma. Baja: la polisemia está **permitida, no impuesta**. Si fuera
  igual de alta, sería imposible por construcción y habríamos vuelto al
  diccionario.

### Fase 4 — metáfora y cambio semántico (`agent._stretch`)

Una sola regla. Cuando a un agente le falta palabra para una categoría,
antes de acuñar una de la nada mira si algún concepto **suyo** parecido
ya tiene nombre, y se la presta:

```python
src, _ = self.concepts.nearest_among(cat, self.lex.named_categories(),
                                     self.cfg.metaphor_radius)
```

Es el mecanismo de *mano → mano de pintura*. La palabra viaja por
semejanza perceptiva. El agente no consulta ninguna etiqueta del mundo ni
sabe que está haciendo una metáfora: solo usa la distancia entre sus
propios prototipos, que es lo único que puede percibir.

El intercambio es real y no se puede resolver razonando: **acuñar** da
una palabra unívoca pero cuesta que la tribu la aprenda; **estirar**
reutiliza algo que los demás ya entienden pero mete ambigüedad. Por eso
`p_metaphor` es un parámetro y `p_metaphor = 0` la ablaciona.

El cambio semántico no se implementa: se **mide**. `metrics.SemanticLog`
guarda, cada pocas generaciones, a qué tipo latente se aplica
dominantemente cada forma viva; `shifts()` compara extremos y solo cuenta
una deriva si en ambos el dominio era nítido (si una palabra nunca
significó nada claro, cambiar de moda no es cambio semántico).

### Fase 5 — composicionalidad por cuello de botella (`grammar.py`, `syntax.py`)

Las señales dejan de ser atomos. El agente guarda cadenas enteras y, por
INDUCCION sobre lo que ha oido, busca la costura: dos señales que hablan
de lo mismo en sitios distintos comparten el principio y difieren en el
final. Nadie le dice donde estan las fronteras.

Resultado (8 semillas x 120 generaciones), apretando la memoria de
señales enteras:

| memoria | topsim | reglas | compuestas |
|---|---|---|---|
| 8 | **+0.497** | 0.84 | **0.64** |
| 16 | +0.449 | 0.82 | 0.39 |
| 32 | +0.137 | 0.80 | 0.20 |
| inf | +0.126 | 0.82 | 0.20 |

`memoria=8 - inf`: topsim +0.370 [+0.290, +0.448] δ=1.00; compuestas
+0.440 [+0.430, +0.450] δ=1.00. A memoria 32 el efecto es **exactamente
cero**.

La lectura fina: no basta con apretar, **el cuello tiene que ser mas
estrecho que el mundo del que hay que hablar**. Y `reglas` se queda plano
en 0.80-0.84 en las cuatro condiciones: los agentes SIEMPRE inducen las
fronteras. Lo que cambia es si las usan. La gramatica no aparece por
poder hacerla, aparece por no poder evitarla.

### Fase 6 — sucesos, papeles, orden y tiempo (`events.py`, `syntax.py`)

Un significado deja de ser (cosa, lugar) y pasa a ser un suceso:
`(accion, participante1, participante2, lugar, tiempo)`. De ahi salen
tres cosas que antes eran imposibles.

**Sintaxis.** Los participantes comparten inventario de morfos, asi que
el papel lo tiene que cargar la posicion. Cada agente lleva pesos sobre
los seis ordenes tipologicos (SVO, SOV, VSO, VOS, OVS, OSV) y aprende
cual lee bien lo que oye. **La tribu converge: SVO en el 100% de los
agentes, confianza media 0.87.** Nadie lo decreto.

**Desplazamiento.** Un suceso ocurrio en una generacion concreta;
contarlo despues es hablar de lo que no esta delante. El 26% de los
enunciados son del pasado.

Y aqui esta el punto que mas me costo respetar: **el pasado no se puede
co-observar**. Un relato solo enseña PALABRAS si el oyente tambien estuvo
alli y lo recuerda (el 44% de los casos). Si no estuvo, no aprende ni una
palabra — pero puede aprender del MUNDO, si ya entendia las palabras. El
5.7% de los relatos enseñan al oyente algo que no habia vivido. Esa es la
unica via por la que un saber sobrevive a quien lo adquirio.

**Morfema cero.** El presente y el existencial no llevan pieza. Salio de
un fallo: exigir morfo para las cuatro ranuras dejaba la comprension
compuesta en cero, porque hacia falta conocer los cuatro. Que lo no
marcado no se diga es lo que hacen las lenguas reales, y aqui ademas es
lo que permite que el sistema arranque.

### Fase 7 — recursividad: discurso referido (`events.py`, `syntax.py`)

`DIJO` es la unica accion cuyo argumento no es una categoria sino **otro
suceso entero**. `express` y `parse` se llaman a si mismas: la misma
estructura dentro de si misma, sin tope teorico («dijo que dijo que hay
fruto»). El tope de `max_depth` es practico, para dejar de recorrer.

Y no es adorno gramatical: sirve para algo. Sin marca de procedencia, un
agente que aprende algo de oidas y lo recuenta lo presenta como propio, y
el rumor se amplifica. Con ella hay **tres escalones de descuento**:

    lo vivido      value_lr      0.30
    lo oido        testimony_lr  0.12
    el rumor       hearsay_lr    0.05

La recursividad existe para marcar de donde viene lo que sabes.

**Donde se cortaba la cadena.** El encaje se producia en el 1% de los
enunciados y nadie lo entendia. En vez de parchear, se instrumentaron los
siete eslabones. El resultado señalo un sitio inesperado: los agentes
tenian 23.315 recuerdos ajenos, pero al recordar algo para contarlo salia
de oidas **1 de cada 25 veces**. Cada episodio dejaba un recuerdo vivido y
el testimonio quedaba enterrado.

Arreglo: **lo visto y lo contado son dos compartimentos de memoria
distintos**. No es un sesgo puesto a mano — el modelo ya los trataba
distinto al aprender; compartir almacen era la incoherencia. Los encajes
pasaron del 1.0% al 6.3% de los enunciados.

**Segundo corte, ya diagnosticado.** El complementante se aprendia
comparando cadenas exactas: el oyente tenia que saber decir la oracion de
dentro *igual* que el hablante. Fallaba el 55% de las veces, y con razon:
dos hablantes de una lengua sin converger dicen lo mismo de formas
distintas. Estabamos pidiendo identidad de PRODUCCION cuando importa la
identidad de SIGNIFICADO. Ahora se verifica por analisis — ¿se entiende
el resto como el suceso de dentro? — y el anclaje sube a 410 de 444.

Aun asi la comprension de encajes se queda en el 4-8%, y la
instrumentacion dice por que: **no es el complementante** (el 90% de los
agentes lo tienen y lo reconocen), es que falla el analisis de la oracion
de dentro. La recursividad esta limitada por la coherencia lexica, no por
si misma.

### El techo de coherencia y cómo se rompió

Cuatro mecanismos —recursividad, descripciones, transmisión cultural,
vocabulario atributivo— quedaron construidos y funcionando al ralentí
contra el mismo techo de coherencia (~0.50). No era limitación de ninguna
fase: era la del modelo.

**Tres hipótesis mías, las tres refutadas por los datos:**

| causa que sospechaba | medida | veredicto |
|---|---|---|
| ruido de inducción dentro de cada agente | consistencia intra-agente **0.957** | no |
| divergencia conceptual irreducible | coherencia entre «puros» solo +0.036 | no |
| auto-refuerzo de la palabra propia | **90.1%** de lo que se dice es adoptado | no |

Lo que lo desbloqueó fue medir la **distribución de variantes** en vez de
seguir razonando: ~3 palabras vivas por cosa, repartidas y a veces
empatadas exactamente (0.46 / 0.46 en `hongo_palido`). No era un proceso
a medio camino sino **un equilibrio con varias convenciones simultáneas**.

Diagnóstico: fallo de **ruptura de simetría**. La inhibición lateral es
local — cada uno refuerza lo que oye y debilita el resto en su cabeza —
así que en una banda de ocho con encuentros al azar nadie llega a ver
cuál es la mayoría global, y un empate 3-3 no se deshace nunca.

**El arreglo** (`social_exp`): al hablar pesa **de cuánta gente distinta**
se ha oído cada forma, no cuántas veces. Una ventaja 3-2 pasa a ser
detectable. Es como se difunden las variantes de verdad: por número de
hablantes, no por frecuencia bruta.

Resultados (10 semillas × 3 niveles):

| variable | e=0.0 | e=0.4 | diferencia (IC95) | δ |
|---|---|---|---|---|
| **coherencia léxica** | 0.474 ± 0.037 | **0.640** ± 0.050 | +0.166 [+0.130, +0.202] | **+1.00** |
| **decisiones acertadas** | 0.587 ± 0.014 | **0.618** ± 0.008 | +0.030 [+0.020, +0.040] | +0.92 |
| composicionalidad | 0.341 | 0.389 | +0.049 [+0.013, +0.087] | +0.52 |
| comprensión de descripciones | 0.040 | 0.074 | +0.034 [+0.008, +0.059] | +0.60 |
| solapamiento adjetival | 0.042 | 0.087 | +0.046 [+0.025, +0.068] | +0.78 |
| comprensión de encajes | 0.053 | 0.058 | +0.005 [−0.019, +0.027] | **no** |

**La cadena causal se confirma en tres de cuatro.** Tres mecanismos que
nadie tocó se mueven al subir la coherencia. Pero **la recursividad no**:
mi explicación de que estaba limitada por la coherencia era falsa. Está
bloqueada por otra cosa, y no sé cuál.

Y el óptimo no es el máximo: a `e=0.8` la coherencia sube algo más pero
los aciertos bajan y la ganancia de composicionalidad desaparece.

### Fase 8 — descripción: dar el concepto, no solo su valor

Una sonda midió la forma de la nube sensorial de cada morfo — con qué
cosas aparece — y separó tres poblaciones sin declarar categorías
gramaticales: **estrecha en todo** = nombra una cosa; **estrecha en una
dimensión, ancha en el resto** = nombra una propiedad; **ancha en todo** =
lugar, acción, tiempo.

Predije que no habría adjetivos. **Los había**: 41 morfos (18.1%)
restringiendo una sola dimensión — `'ii'` y `'nu'` el *verdor*, `'ud'` la
*temperatura*. Son subproducto accidental de la metáfora de la Fase 4:
estirar una palabra hacia un concepto vecino produce una que cubre la
región donde ambos coinciden.

Sobre eso se montó describir (`agent.describe`), entender
(`understand_description`) e instalar un concepto oído
(`ConceptSpace.install_described`) — provisional, porque un concepto que
llega por el oído es una **hipótesis perceptiva** que el mundo puede
desmentir.

**Funciona de punta a punta y se usa poco**: descripciones en el ~4% de
los episodios, comprensión 7-11%.

### Fase 9 — espacio

Los lugares dejan de ser un coste escalar y pasan a tener coordenadas.
Los agentes tienen posición y derivan; **con quién te cruzas depende de
dónde estás**; y algunos tipos solo crecen en ciertas regiones.

Predicciones dichas de antemano, y lo que pasó:

| predicción | resultado |
|---|---|
| la coherencia global baja | ✅ 0.640 → **0.431** |
| aparece transmisión cultural | ❌ no |
| dialectos intra-tribu | sin medir |

Y algo no predicho: los **aciertos subieron** (0.618 → 0.627).

**El mecanismo funcionó; la consecuencia no.** La partición del saber
apareció con fuerza — de 13 de 16 agentes con experiencia directa del
veneno se pasó a **3 de 16**. Pero el testimonio sigue sin transmitir
nada, porque los que no han pisado el bosque **no tienen concepto** donde
poner lo que se les cuente.

---

## Lo que no funcionó, y por qué

Media investigación de este repo son resultados negativos. Están aquí
porque cada uno acota algo.

**El canal de alarma no emerge.** Siete fases, un mundo nuevo, toda la
maquinaria de sucesos: las muertes por depredador son idénticas en los
tres brazos. *Una señal solo se estabiliza si la situación se repite lo
bastante frente al relevo generacional.* El modelo lexicaliza bien lo
cotidiano y mal lo raro-y-letal.

**La transmisión cultural no ocurre.** Cuatro intentos:

| intento | por qué falló |
|---|---|
| tóxicos normales | todos los viven; el testimonio no tiene nicho |
| veneno raro (abundancia 0.06) | **manipulación fallida**: 13/16 lo vivían igual |
| veneno raro (0.01, dosis correcta) | nadie tiene concepto donde ponerlo |
| espacio (Fase 9) | partición lograda (3/16), pero el concepto sigue faltando |

De ahí sale la frase que resume el alcance del modelo:

> Puede decirte **cuánto vale** algo de lo que ya tienes concepto.
> No puede darte el **concepto**.

**Cinco hipótesis mías refutadas por los datos** sobre el techo de
coherencia y las descripciones: auto-refuerzo de la palabra propia,
divergencia conceptual, ruido de inducción, dos fuerzas incompatibles
(espacio contra coherencia), y el solapamiento adjetival como cuello.

La sexta funcionó, y salió de **medir la distribución de variantes** en
vez de razonar. El patrón es tan consistente que vale como método: en
este proyecto la intuición ha fallado y la instrumentación ha acertado.

**Y un error de lectura que cometí dos veces**: confundir *el eslabón con
más bajas* con *el eslabón limitante*. El choque de dimensión mataba el
16% de las descripciones y arreglarlo no cambió casi nada — porque con
3.89 candidatas por llamada, liberar el filtro más frecuente no libera
mucho.

### El tamaño de la banda manda

El resultado mas solido de todo el proyecto, y el que menos esperaba:

| banda | coherencia lexica |
|---|---|
| 30 | 0.116 |
| 18 | 0.225 |
| 12 | 0.301 |
| 10 | 0.40 |
| **8** | **0.532** |

Monotona y grande. Es la ley del juego de nombres — converge en tiempo
superlineal con el numero de hablantes — y encaja con la etnografia: las
bandas de cazadores-recolectores son de este orden, no de cientos.

**Ningun otro mando la mueve.** Se probaron cuatro hipotesis contra una
base de 0.399:

| hipotesis | coherencia |
|---|---|
| base | 0.399 |
| escuchar antes de hablar (20 señales) | **0.000** |
| inhibicion lateral mas fuerte (0.45) | 0.340 |
| quitar el alineamiento supervisado | 0.324 |

Dos de esos fallos enseñan mas que un acierto. **«Escuchar antes de
hablar» produce un bloqueo mutuo**: en la primera generacion nadie ha
oido nada, luego nadie habla, y no arranca ninguna lengua. Y **quitar el
alineamiento empeora las cosas**, lo que confirma que oir la frase, ver
lo que significa y reforzar las piezas reconocidas si estaba aportando.

---

## El experimento

```
python -m emergence.run ablation --seeds 12 --generations 100
```

Mismos mundos, mismos parámetros, mismas semillas. Un solo cambio: qué
transmite el canal.

- `language` — el hablante emite su forma para su categoría
- `mute` — no hay canal
- `noise` — el hablante emite una forma **aleatoria** de un repertorio
  fijo. Control fuerte: separa **señalar** de **informar**

### Resultados (12 semillas × 80 generaciones, 2 tribus, Uqbar de 16 tipos)

| variable | language | mute | noise | lang − mute (IC95) | δ |
|---|---|---|---|---|---|
| **decisiones acertadas** | **0.603** ± 0.016 | 0.491 ± 0.004 | 0.513 ± 0.005 | **+0.112 [+0.104, +0.122]** | **+1.00** |
| energía media | 102.6 ± 2.0 | 101.1 ± 1.9 | 100.3 ± 1.7 | +1.54 [−0.01, +2.97] | +0.47 |
| población sostenida | 16.0 ± 0.0 | 16.0 ± 0.0 | 16.0 ± 0.0 | +0.01 [0.00, +0.02] | +0.08 |
| muertes/alarma | 0.126 ± 0.015 | 0.128 ± 0.023 | 0.112 ± 0.018 | −0.002 [−0.017, +0.012] | −0.03 |

Contra el control fuerte: `language − noise = +0.090 [+0.082, +0.099]`,
δ = +1.00.

**El lenguaje se gana su existencia, y ahora se cobra en decisiones.**
Separación total contra los DOS controles: δ = 1.00 significa que ninguna
corrida muda ni ruidosa alcanza a ninguna corrida hablante. Los
intervalos son estrechos porque el efecto es grande y consistente.

El brazo `noise` es lo que da valor a la conclusión. Emite señales con la
misma frecuencia y los agentes aprenden asociaciones con esas formas
huecas, pero sus decisiones apenas mejoran sobre el silencio (0.513 frente
a 0.491). Señalar no es informar.

### Lo que cambió respecto a la versión anterior de esta tabla

La ablación anterior presumía de que el lenguaje **multiplicaba por 2.4 la
capacidad de carga**. Ese argumento ya no se sostiene, y conviene decir
por qué en vez de borrarlo sin más.

Con bandas de 30 la población era el discriminador: las tribus mudas no
llegaban al techo. Con bandas de 8 —el tamaño al que la lengua converge—
**los tres brazos llenan su banda**: 16.0 ± 0.0 en los tres. Ya no hay
diferencia demográfica que medir, porque hasta una tribu muda alimenta a
ocho personas en este mundo.

O sea: el efecto demográfico de antes no era falso, pero **dependía de
que la banda fuera lo bastante grande como para que el lenguaje no
convergiera**. Un régimen donde la ventaja se veía en la demografía era
justamente un régimen donde la lengua funcionaba mal. Al arreglarla, la
ventaja se mudó a donde tenía que estar desde el principio: la calidad de
las decisiones.

### El canal de alarma sigue sin funcionar

Las muertes por depredador son las mismas en los tres brazos (0.126 /
0.128 / 0.112), todas pegadas a la probabilidad base de 0.12. Traducción:
**los oyentes prácticamente nunca huyen**, tengan lengua o no.

Es el mismo resultado negativo que apareció en la Fase 2 y que sigue en
pie tras siete fases, un mundo nuevo y toda la maquinaria de sucesos. Las
palabras de peligro no llegan a estabilizarse: los encuentros con
depredador son demasiado escasos frente al relevo generacional. El modelo
lexicaliza bien lo cotidiano y mal lo raro-y-letal.

Un detalle que no sé explicar y por tanto no voy a adornar: `language`
tiene *más* muertes que `noise` (+0.014 [+0.002, +0.026], δ = 0.42). Es
estadísticamente distinto de cero pero el efecto es diminuto y no tengo
un mecanismo que lo justifique. Lo dejo anotado como inexplicado.

### Fase 4: ¿la metáfora se gana su sitio?

```
python -m emergence.run metaphor --seeds 10 --generations 100
```

Mismo mundo, misma semilla, mismo todo; solo cambia si se pueden estirar
palabras. 10 semillas × 100 generaciones:

| `p_metaphor` | población | aciertos | coherencia | polisemia | léxico metafórico | derivas semánticas |
|---|---|---|---|---|---|---|
| 0.00 | 39.2 | 0.615 | 0.574 | 0.89 | 0.00 | 1.5 |
| 0.35 | 40.8 | 0.617 | 0.616 | 0.90 | 0.01 | 2.9 |
| 0.70 | 40.8 | 0.615 | 0.626 | 0.97 | 0.03 | 2.9 |

Contra `p_metaphor = 0`:

| | p=0.35 | p=0.70 |
|---|---|---|
| población | +1.62 [−1.81, +6.56] δ=−0.02 **no** | +1.55 [−2.39, +6.71] δ=−0.02 **no** |
| aciertos | +0.002 [−0.006, +0.008] δ=+0.20 **no** | −0.001 [−0.011, +0.008] δ=+0.02 **no** |
| coherencia | +0.042 [+0.017, +0.068] δ=+0.66 **sí** | +0.052 [+0.026, +0.076] δ=+0.78 **sí** |
| polisemia | +0.013 [−0.026, +0.052] δ=+0.20 **no** | +0.080 [+0.030, +0.133] δ=+0.62 **sí** |

**La metáfora no se paga en supervivencia.** Ni población ni aciertos se
mueven: los intervalos de confianza contienen el cero y la δ de Cliff es
prácticamente nula. Si el único criterio fuera "¿ayuda a sobrevivir?", la
respuesta sería no y habría que quitarla.

**Pero acelera la convergencia léxica**, y ese efecto sí es sólido
(δ = 0.66 y 0.78). Y duplica las derivas semánticas (1.5 → 2.9).

Eso ubica la metáfora con precisión dentro del axioma del proyecto:

> *…unless it improves **prediction**, **coordination** or **survival**.*

No mejora la predicción ni la supervivencia. Mejora la **coordinación**.
Es el único de los tres mecanismos implementados que se justifica por el
término del medio, y el resultado lo dice sin que haya que forzarlo.

Un detalle que conviene no sobreinterpretar: solo el 1–3 % del léxico
superviviente nació por extensión, y aun así la coherencia sube medio
punto porcentual largo. La explicación plausible es que estirar reutiliza
una forma que la tribu **ya entiende**, así que se salta la fase cara de
aprender una palabra nueva. Plausible, pero no demostrado: haría falta
aislar el mecanismo para afirmarlo.

Un efecto secundario que sí se ve en la tabla principal: al activar la
metáfora, la desviación de la población hablante cayó de ±5.9 a ±2.0.
La media apenas se movió, pero las corridas dejaron de depender de la
suerte. Converger antes hace el resultado **más fiable**, no mayor.

### La curva que más dice

    python -m emergence.analyze data/ablation.jsonl --metric success

Los brazos **arrancan pegados** y se separan solo cuando el léxico
converge. La ventaja no está en el diseño: aparece en el momento en que
el lenguaje empieza a funcionar, no antes.

### Un resultado negativo que lleva siete fases en pie

El sistema de alarma **casi no emerge**, y sigue sin hacerlo. Ya salió en
la Fase 2 y la ablación de 12 semillas lo confirma: las muertes por
depredador son idénticas en los tres brazos (0.126 / 0.128 / 0.112), todas
pegadas a la probabilidad base. Los oyentes prácticamente nunca huyen,
tengan lengua o no.

Con la versión antigua del modelo (cuando la depredación era una fracción
de los episodios) se pudo comprobar que subiendo la frecuencia de
encuentros el canal **sí** aparecía: la tasa de huida pasaba de 0.10 a
0.27 y las muertes casi se reducían a la mitad. Esa medición es de una
configuración que ya no existe y no la traslado a esta tabla, pero la
lectura que dejó sigue valiendo y es una predicción que nadie programó:

> **Una señal solo se estabiliza si la situación se repite lo bastante
> como para sostener la asociación frente al relevo generacional.**

El modelo lexicaliza bien lo cotidiano y mal lo raro-y-letal. Los sucesos
escasos y graves no llegan a tener nombre estable — que es, dicho sea de
paso, un problema real de cualquier sistema de aviso.

## Lo que emerge sin haberlo programado

Una corrida típica (`--seed 3 --generations 100 --tribes 2`):

```
  tipo latente   afordancia  tribu 1        tribu 2
  fruto_dulce    alimento    vrera (57%)    koridros (100%)
  fruto_amargo   toxico      vrera (85%)    zuvo (40%)
  raiz           alimento    febeslo (100%) drabelo (100%)
  charca         agua        kolen (100%)   brakese (88%)
  bestia         alimento    kadivu (29%)   trabutru (65%)
  acechante      depredador  sitar (47%)    fatrosu (43%)

  distancia lexica entre tribu 1 y 2: 1.00   (1.00 = ninguna palabra en comun)
```

1. **Dos lenguas independientes** para el mismo mundo, sin una sola
   palabra en común.
2. **Polisemia real**: la tribu 1 usa `vrera` para el fruto dulce *y*
   para el amargo — el par confundible del espacio sensorial. Dentro de
   un agente concreto: `'vrera' -> cat1(valor +8.0), cat5(valor -10.0)`.
   Es una ambigüedad que les cuesta energía, y aun así se sostiene.
   Nadie la programó: es lo que pasa cuando dos cosas se parecen
   demasiado y la inhibición por significado es baja.
3. **Solo se nombra lo que importa.** `piedra` y `flor` (inertes) apenas
   reciben nombre estable. No está prohibido nombrarlas.
4. **Cambio semántico** entre los pares confundibles, que es justo donde
   cabía esperarlo: `leslan` pasa de *bestia* (gen 75) a *acechante*
   (gen 100); `tidago` de *fruto_dulce* (gen 5) a *fruto_amargo*
   (gen 100). Nadie define qué palabra debe derivar ni hacia dónde.
5. **La facultad evoluciona, la lengua se aprende.** La vigilancia media
   deriva de 0.55 hacia ~0.48–0.53 por selección; el léxico no se hereda
   nunca.

---

## Uso

```bash
python -m emergence.world                      # inspeccionar el mundo
python -m emergence.run sim --generations 100 --seed 3 --tribes 2
python -m emergence.run sim --mode mute --generations 100
python -m emergence.run ablation --seeds 12 --generations 100 --out data/ablation.jsonl
python -m emergence.run metaphor --seeds 10 --generations 100
python -m emergence.analyze data/ablation.jsonl
python -m emergence.analyze data/ablation.jsonl --metric coherence
```

Sin dependencias externas: solo la biblioteca estándar. Una corrida de
100 generaciones tarda ~1 s; la ablación completa, unos 3 minutos.

Parámetros útiles: `--tribes`, `--tribe-size`, `--max-pop`, `--vigilance`
(resolución perceptiva inicial), `--alarms` (encuentros con depredador
por cabeza), `--world`, `--episodes`, `--contact` (0 = tribus
aisladas; >0 abre préstamos entre lenguas). El subcomando `metaphor`
acepta `--levels 0.0 0.35 0.7`.

### Módulos

```
config.py     todos los parametros. Un numero magico fuera de aqui es un bug
world.py      carga Uqbar del JSON: objetos, afordancias, lugares
percept.py    Fase 1: clustering incremental, radio por categoria, match tracking
lexicon.py    Fase 3: grafo forma x significado, inhibicion lateral asimetrica
grammar.py    Fase 5: gramatica de dos piezas (cosa, lugar)
events.py     Fase 6-7: sucesos, papeles, tiempo, memoria en dos compartimentos
syntax.py     Fase 6-7: vocabularios por tipo, orden emergente, recursividad
agent.py      particion + valor + lengua, decisiones, metafora, testimonio
episodes.py   Fase 2+6: forrajeo, alarma, relatos. El canal y sus tres modos
tribe.py      demografia; forrajeo con presupuesto fijo, depredacion por cabeza
metrics.py    NMI, coherencia, topsim, SemanticLog, bootstrap, delta de Cliff
audit.py      la carta de la lengua: ¿cumple los criterios de un idioma?
fastrand.py   ruido gaussiano por lotes (era el mayor coste del modelo)
run.py        CLI, informe, ablacion, metafora, cuello de botella
analyze.py    curvas ASCII desde el JSONL
```

### La carta de la lengua

```
python -m emergence.run sim --generations 80 --seed 3
```

El informe termina pasando la lista de criterios que un lingüista pediria
para llamar «lengua» a un sistema, con un numero detras de cada veredicto.
La regla: si algo no se puede medir se declara NO MEDIDO, y si sale mal,
sale mal. Un informe que solo sabe decir que si no sirve para nada.

Estado actual: **14 criterios con evidencia, 3 parciales, 3 sin cumplir.**

Con evidencia: inventario finito de unidades, doble articulacion, lexico,
arbitrariedad, morfologia, **sintaxis convergente (SVO en el 100% de la
tribu, confianza 1.00)**, productividad (94 morfos → ~1920 significados),
creatividad, **desplazamiento** (32% de enunciados sobre el pasado, 77%
anclados en memoria compartida), **saber transmitido** (6.6% de los
relatos enseñan algo no vivido), polisemia, dialectos, cambio semantico,
transmision cultural.

Parciales: convencionalidad, composicionalidad, recursividad.

Sin cumplir: pragmatica, metalingüistica, y el orden de los
circunstanciales — que va al final porque lo fijamos nosotros. Emerge el
orden de los ARGUMENTOS, no la posicion de los adjuntos.

---

## La carta de la lengua

`python -m emergence.run audit --seeds 12`

El informe pasa la lista de criterios que un lingüista pediría para llamar
«lengua» a un sistema. El veredicto agregado exige **SÍ en ≥70% de las
corridas**: un criterio que sale bien en la mitad no está cumplido, es uno
que depende de la semilla.

**14 de 20 con evidencia, 4 parciales, 2 no cumplidos** (12 semillas,
Uqbar de 17 tipos, banda 8) — con una advertencia grande, más abajo.

| criterio | valor | consistencia |
|---|---|---|
| inventario de unidades | 30 | 12/12 |
| doble articulación | 104.1 ± 19.5 | 12/12 |
| léxico | 16.5 ± 2.4 | 12/12 |
| morfología | 0.911 | 12/12 |
| **sintaxis (SVO convergente)** | **1.000 ± 0.000** | **12/12** |
| productividad | 2808 significados | 12/12 |
| creatividad | 0.212 | 12/12 |
| desplazamiento | 0.330 | 12/12 |
| saber transmitido | 0.240 | 12/12 |
| variación (dialectos) | 1.000 | 12/12 |
| cambio semántico | 7.8 palabras | 12/12 |
| transmisión cultural | — | 12/12 |
| arbitrariedad | +0.128 | 9/12 |
| composicionalidad | 0.330 | 9/12 |
| *polisemia* | 1.048 | 6/12 |
| *convencionalidad* | 0.469 | 4/12 |
| *recursividad* | 0.051 | 0/12 |
| *metalingüística* | 0.060 | 0/12 |
| **pragmática** | **0.000** | **0/12** |
| **orden de circunstanciales** | **0.000** | **0/12** |

### El 14 no está ganado

Composicionalidad cruzó de 8/12 a 9/12 con el umbral en 8.4. **Una semilla
de margen**, con el topsim moviéndose de 0.324 a 0.330. Es ruido, y en el
mismo brazo la arbitrariedad bajó de 11/12 a 9/12. Quien cite este 14 sin
esta advertencia está citando mal: el resultado defendible sigue siendo
**13-14/20**, y la diferencia entre ambos es una corrida.

### El mundo pequeño: un resultado negativo con potencia

La literatura del *naming game* sobre grafos geométricos dice que las
retículas regulares se atascan en fases metaestables y que unos pocos
enlaces de largo alcance las desatascan — con el matiz de que los atajos
deben ser de distancia intermedia, no aleatorios. Nuestro emparejamiento
por vecindad (Fase 9) es una retícula, así que la predicción era directa.

Se probó, en las dos formas, con 12 semillas cada una:

| red | coherencia | marcador |
|---|---|---|
| retícula pura (`p_lejano=0`) | 0.475 | 13/20 |
| atajos aleatorios (`p=0.10`) | 0.473 | 13/20 |
| atajos de media distancia (`p=0.10`) | 0.469 | 14/20 |

**La coherencia no se mueve.** El cuello de la convergencia léxica de este
modelo no es la topología de la red. Es un resultado negativo con potencia
estadística, no una duda pendiente.

Un sondeo previo de 4 semillas dio +0.052 de coherencia para los atajos de
media distancia, y lo di por bueno durante media hora. No replicó a 12. Es
el mismo error que este README ya documenta en otro sitio: a 4 semillas la
varianza entre semillas es del orden del efecto que se busca.

### Los seis que faltan, y por qué

**Cinco cuelgan del mismo cuello.** Recursividad, metalingüística,
convencionalidad, polisemia y arbitrariedad dependen de
la convergencia léxica, que se estanca en ~0.47. Los mecanismos están
construidos y son correctos — pero **un morfo nuevo solo converge si entra
en el circuito de co-observación que alinea los nombres**, y el
complementante, los adjetivos y la marca metalingüística no entran nunca.
Comprobado seis veces con seis mecanismos distintos.

**La pragmática tiene un impedimento propio.** La polisemia de este modelo
es *nominal*: la brecha media entre la primera y la segunda acepción es
0.341, y solo el 34.5% de los pares están lo bastante parejos para que el
contexto pudiera voltearlos. Sin ambigüedad real no hay nada que
desambiguar, y subir el peso del contexto hasta que aparezca el número
sería fabricar el resultado.

**Y uno lo puse yo.** El orden de los circunstanciales: lugar y tiempo van
siempre al final porque lo fijé al diseñar la Fase 6. No emerge, y contarlo
como sintaxis emergente sería mentir.

### Una corrección

En su momento afirmé que apagar la pragmática «devuelve el marcador a
14/20». Devuelve **13**. Ese 14 salía de una auditoría anterior sobre un
código que ya no existía: era una extrapolación presentada como medición.
Las dos auditorías comparables, sobre el mismo código, dan 12/20 con
pragmática y 13/20 sin ella.

### El 0.47 no es un techo: es un atractor

La pregunta que faltaba por hacer, y que se hizo la última: **¿y si 55
generaciones son sencillamente pronto?** En los juegos de nombres el
tiempo hasta el acuerdo escala como N^1.4; toda auditoría de este repo
corre 55 generaciones y nadie había comprobado que eso bastara.

| generaciones | coherencia | topsim | por semilla |
|---|---|---|---|
| 55 | 0.483 | 0.377 | 0.410 · 0.502 · 0.535 |
| 110 | 0.496 | 0.342 | 0.494 · 0.442 · 0.552 |
| 220 | 0.453 | 0.342 | **0.452 · 0.449 · 0.457** |

Cuadruplicar el tiempo no sube la coherencia. Pero lo revelador no es la
media, es **la dispersión entre semillas**: 0.125 a las 55 generaciones,
**0.005** a las 220. Y la semilla que estaba en 0.535 *bajó* a 0.457.

El sistema no se queda corto de 0.45: converge a 0.45 desde arriba y desde
abajo. Es un atractor, no un límite.

Eso reinterpreta toda la serie de intentos fallidos. El cuello de botella,
la amplificación de mayorías y las dos variantes de mundo pequeño no
fracasaron por ser débiles — fracasaron porque existe una fuerza que
devuelve el sistema a 0.45 haga lo que haga el mecanismo. Explica que tres
auditorías de 12 semillas dieran 0.475, 0.473 y 0.469.

**Hipótesis del mecanismo, sin medir todavía:** es la regla 2 del proyecto.
El léxico está deliberadamente aislado de la recompensa, así que lo único
que empuja hacia el acuerdo es la co-observación, que tiene alcance local
fijo. El equilibrio entre esa presión y la deriva de variantes nuevas cae
en 0.45. Si es cierto, el 0.45 no es un defecto del modelo: es el precio
de la regla que hace que la ablación signifique algo.

---

### Dónde queda esto frente al estado del arte

Revisión bibliográfica hecha en agosto de 2026, después de medir. No
cambia una línea de código; cambia cómo hay que leer el 14/20.

**Los criterios que nos faltan son los que el campo apenas ha
investigado.** El survey de taxonomía de lenguaje emergente lo dice
literalmente: *«recursion, metalinguistic functions, and cultural
transmission receive minimal empirical investigation»*, y *«pragmatics
remains underdeveloped compared to semantic and syntactic analysis»*. Dos
de nuestros huecos y uno que aquí sí sale en 12/12.

**La convencionalidad estancada es un resultado publicado.** Bouchacourt y
Baroni encuentran que los agentes desarrollan *múltiples idiolectos* y
concluyen que la simetría completa no basta para que emerja una lengua
común. Es nuestro `convencionalidad 4/12` con otro nombre, y encaja con el
resultado negativo del mundo pequeño: más mezcla no disuelve los
idiolectos.

**El trabajo reciente más ambicioso no tiene gramática.** El marco de
*social learning agents* (Nature Communications, 2024) obtiene
composicionalidad medida con topsim y una forma de pragmática, pero
declara: *«our model lacks predefined syntax or grammar»* y *«we did not
utilize sequential composition»*. Aquí el orden SVO converge en 12/12.

**Y el survey reclama tres cosas que este modelo ya tiene**: restricciones
de memoria (nuestro cuello de botella), alternancia de roles (todo agente
habla y escucha) y dinámica de poblaciones — el campo trabaja
mayoritariamente con dos agentes de rol fijo.

Una advertencia que va en nuestra contra: el survey señala *«ill-adapted
metrics»* y umbrales arbitrarios como problema extendido. Nuestro umbral
del 70% de corridas es una decisión de este repo, no un estándar. El 14/20
**no es comparable** con las cifras de otros trabajos, porque cada uno
mide con su propia regla.

---

## Honestidad sobre los límites

Cosas que este modelo **no** hace, y que no conviene confundir con lo que
sí hace:

- **No hay pragmática.** Una señal significa lo mismo dicha por quien sea
  y cuando sea. El contexto no interviene en la interpretación.
- **No hay capacidad metalingüística.** La lengua no puede hablar de sí
  misma.
- **El orden de los circunstanciales lo fijamos nosotros**: lugar y
  tiempo van siempre detrás del núcleo. Emerge el orden de los
  argumentos, no la posición de los adjuntos.
- **La recursividad se usa poco y se entiende menos** (≈5% de los
  enunciados, comprensión 4–8%). Está limitada por la coherencia léxica,
  con el diagnóstico hecho y la ruta identificada.
- **La política de hablar es una heurística**, no algo aprendido: hablar
  si `|valor| × kin_share > umbral`. Que emerja *cuándo* hablar sigue
  pendiente.
- **La co-observación del presente es una concesión.** El oyente acaba
  viendo de qué se hablaba aunque no vaya. Se justifica porque viven en
  la misma banda y porque la decisión —donde se cobra el pago— ya estaba
  tomada; pero es una simplificación, no un hecho derivado.
- **La memoria en dos compartimentos y la depredación por cabeza** son
  decisiones de modelado tomadas *después* de ver que sus alternativas
  rompían algo. Son defendibles por sí solas, pero llegaron por
  diagnóstico, no por diseño previo. Conviene saberlo.

### Sobre la potencia estadística

La ablación, el experimento de metáfora y el del cuello de botella se
corrieron con 8–12 semillas y llevan intervalos de confianza. **El resto
de cifras de este README son de 2–3 semillas.** La variación entre
semillas con configuración idéntica que hemos observado (coherencia 0.349
frente a 0.445) es del mismo orden que varios de los efectos medidos.

La escalera del tamaño de banda es lo bastante monótona y grande como
para creérsela. Las comparaciones que se mueven en ±0.07 —las cuatro
hipótesis sobre coherencia, por ejemplo— **no son concluyentes** y están
marcadas como tales. No deberían citarse sin repetirlas.

### El parámetro que más manda

`max_pop`. Fija el tamaño de banda, y de ahí cuelgan la coherencia
léxica, la composicionalidad y la comprensión de encajes. A banda 30 la
lengua no converge y todo lo demás se cae con ella. Conviene saberlo
antes de leer cualquier tabla.
