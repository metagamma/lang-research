<script setup>
// Vista científica. Sin animación: números, y los que importan.
//
// Ordenada por preguntas, no por métricas sueltas. Cada bloque responde
// algo que se podría contestar mal, y dice cuándo la respuesta no es
// fiable. Un visor de UNA corrida sin semillas no demuestra nada — eso
// está arriba del todo y no se quita.
import { computed, ref } from 'vue'
import { instantanea, serie, cortes, gen, tic, mundo } from '../../core/state.js'
import MetricCurve from '../../components/MetricCurve.vue'
import VariantBars from '../../components/VariantBars.vue'
import Diccionario from '../../components/Diccionario.vue'
import MapaSemantico from '../../components/MapaSemantico.vue'

const pestana = ref('diccionario')

const CURVAS = [
  ['success', 'decisiones acertadas'],
  ['coherence', 'coherencia léxica'],
  ['topsim', 'composicionalidad (topsim)'],
  ['pop', 'población'],
  ['signal_rate', 'episodios con señal'],
  ['said_composed', 'señales compuestas'],
  ['past_rate', 'enunciados sobre el pasado'],
  ['desc_rate', 'descripciones'],
  ['novel_rate', 'frases nunca oídas'],
  ['testimony_rate', 'saber por testimonio'],
  ['alarm_rate', 'alarmas'],
  ['lex_size', 'tamaño del léxico'],
]

const s = computed(() => { tic.value; return instantanea.value })
const tribus = computed(() => s.value?.tribus || [])
const marcas = computed(() => cortes.value.map(c => c.g))
const dicc = computed(() => s.value?.diccionario || [])
const dialectos = computed(() => s.value?.dialectos || [])
const lexico = computed(() => s.value?.lexico || {})
const metricas = computed(() => s.value?.metricas || {})
const coh = computed(() => s.value?.coherencia ?? 0)

const ordenes = computed(() => {
  const c = {}
  for (const t of tribus.value) {
    for (const [o, q] of (t?.orden || [])) c[o] = (c[o] || 0) + q
  }
  const tot = Object.values(c).reduce((a, b) => a + b, 0) || 1
  return Object.entries(c).map(([o, q]) => [o, q / tot])
    .sort((a, b) => b[1] - a[1])
})

const NOMBRE_LEX = {
  synonymy: 'sinonimia', polysemy: 'polisemia', size: 'morfos por agente',
  metaphor: 'préstamos metafóricos', composed: 'señales compuestas',
  rules: 'agentes con reglas',
}
const NOMBRE_MET = {
  alignment: 'alineamiento de conceptos', prediction: 'predicción',
  past_rate: 'sobre el pasado', desc_rate: 'descripciones',
  said_composed: 'compuestas', novel_rate: 'frases nuevas',
  novel_success: 'frases nuevas entendidas', testimony_rate: 'testimonio',
  quote_rate: 'discurso referido', meta_rate: 'metalingüística',
  alarm_rate: 'alarmas',
}
</script>

<template>
  <section class="lab">
    <p v-if="!s" class="esperando">Esperando datos…</p>

    <template v-else>
      <p class="disclaimer">
        Esto es <b>una corrida</b>, sin réplicas ni brazos de control.
        Sirve para mirar, no para concluir. Para medir están
        <code>ablation</code>, <code>social</code>, <code>bottleneck</code>
        y <code>audit</code>, que corren por lotes con semillas.
      </p>

      <div class="cifras">
        <div><b>{{ gen }}</b><span>generación</span></div>
        <div><b>{{ s.pop }}</b><span>población</span></div>
        <div :class="{ atractor: coh > 0.3 && coh < 0.6 }">
          <b>{{ coh?.toFixed(3) }}</b><span>coherencia</span>
        </div>
        <div><b>{{ s.topsim?.toFixed(3) }}</b><span>composicionalidad</span></div>
        <div><b>{{ (s.exito * 100)?.toFixed(1) }}%</b><span>aciertos</span></div>
        <div><b>{{ dicc.length }}</b><span>cosas con nombre</span></div>
      </div>

      <p v-if="marcas.length" class="aviso">
        {{ marcas.length }} cambio(s) de parámetro en vivo. La serie
        <b>deja de ser comparable</b> a ambos lados de cada marca: no es
        una sola corrida.
      </p>

      <nav class="pestanas">
        <button v-for="p in ['diccionario', 'mapa', 'curvas', 'tribus', 'cifras']"
                :key="p" :class="{ on: pestana === p }" @click="pestana = p">
          {{ p }}
        </button>
      </nav>

      <div v-show="pestana === 'diccionario'">
        <h2>La lengua, leída</h2>
        <p class="nota">
          Nadie escribió esto. Cada entrada es una palabra que se inventó
          alguien y que otros adoptaron —o no—.
        </p>
        <Diccionario :entradas="dicc" :mundo="mundo" />
      </div>

      <div v-show="pestana === 'mapa'">
        <h2>Qué se parece a qué, y si la lengua lo distingue</h2>
        <MapaSemantico :mundo="mundo" :entradas="dicc" />
      </div>

      <div v-show="pestana === 'curvas'">
        <h2>Series</h2>
        <div class="curvas">
          <MetricCurve v-for="[k, t] in CURVAS" :key="k"
                       :serie="serie" :clave="k" :titulo="t" :marcas="marcas" />
        </div>
      </div>

      <div v-show="pestana === 'tribus'">
        <h2>Orden de palabras</h2>
        <p class="nota">
          Seis órdenes posibles (SVO, SOV, VSO, VOS, OVS, OSV) y ninguno
          programado. Que converja uno sale en 12 de 12 semillas.
        </p>
        <div class="ordenes">
          <div v-for="[o, q] in ordenes" :key="o" class="orden">
            <b>{{ o }}</b>
            <div class="tira"><span :style="{ width: (q * 100) + '%' }"></span></div>
            <small>{{ Math.round(q * 100) }}%</small>
          </div>
        </div>

        <h2>Dialectos</h2>
        <p class="nota">
          Cuánto comparten las lenguas de dos tribus separadas. Cero
          significa que no coinciden en el nombre de <b>nada</b>: dos
          idiomas distintos surgidos del mismo mundo.
        </p>
        <ul class="dial">
          <li v-for="(d, i) in dialectos" :key="i">
            tribu {{ d.a + 1 }} ↔ tribu {{ d.b + 1 }}:
            <b>{{ Math.round(d.comparte * 100) }}%</b> de {{ d.cosas }} cosas
            se llaman igual
          </li>
          <li v-if="!dialectos.length" class="vacio">una sola tribu viva</li>
        </ul>

        <h2>Reparto de variantes por tipo</h2>
        <p class="nota">
          Varias barras parejas para una misma cosa = convenciones rivales
          que no se deshacen. Es el atractor de 0.45, visto de cerca.
        </p>
        <div class="tribus">
          <div v-for="(t, i) in tribus" :key="i" class="tribu">
            <h3>Tribu {{ i + 1 }}
              <small v-if="t">{{ t.n }} agentes · coherencia
                {{ t.coherencia?.toFixed(3) }}</small>
            </h3>
            <VariantBars v-if="t" :nombres="t.nombres" />
            <p v-else class="perdida">extinguida</p>
          </div>
        </div>
      </div>

      <div v-show="pestana === 'cifras'">
        <h2>Forma del léxico</h2>
        <table class="tabla">
          <tr v-for="(v, k) in lexico" :key="k">
            <td>{{ NOMBRE_LEX[k] || k }}</td><td><b>{{ v?.toFixed(3) }}</b></td>
          </tr>
        </table>
        <h2>Qué se está usando la lengua para hacer</h2>
        <table class="tabla">
          <tr v-for="(v, k) in metricas" :key="k">
            <td>{{ NOMBRE_MET[k] || k }}</td><td><b>{{ v?.toFixed(3) }}</b></td>
          </tr>
        </table>
      </div>
    </template>
  </section>
</template>

<style scoped>
.cifras { display: flex; gap: 1.8rem; margin-bottom: 1rem; flex-wrap: wrap; }
.cifras div { display: flex; flex-direction: column; }
.cifras b { font-size: 1.55rem; }
.cifras span { opacity: .65; font-size: .78rem; }
.cifras .atractor b { color: #d98324; }
.pestanas { display: flex; gap: .4rem; margin: 1rem 0; flex-wrap: wrap; }
.pestanas button { background: transparent; color: inherit; cursor: pointer;
                   border: 1px solid rgba(128,128,128,.3); border-radius: 4px;
                   padding: .28rem .7rem; font-size: .82rem; }
.pestanas button.on { border-color: currentColor; font-weight: 600; }
.curvas { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 1rem; }
.tribus { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
          gap: 1.5rem; }
.ordenes { display: flex; flex-direction: column; gap: .3rem; max-width: 26rem; }
.orden { display: flex; align-items: center; gap: .6rem; font-size: .85rem; }
.orden b { font-family: ui-monospace, monospace; width: 3rem; }
.tira { flex: 1; height: 12px; background: rgba(128,128,128,.15); border-radius: 3px; }
.tira span { display: block; height: 100%; background: #4a7fd4; border-radius: 3px;
             transition: width .4s ease; }
.dial { font-size: .85rem; padding-left: 1.1rem; }
.tabla { font-size: .85rem; border-collapse: collapse; }
.tabla td { padding: .18rem 1.2rem .18rem 0; }
.tabla td:first-child { opacity: .75; }
.aviso { border-left: 3px solid var(--sig-fallo); padding-left: .7rem; }
.disclaimer { border-left: 3px solid rgba(128,128,128,.4); padding-left: .7rem;
              font-size: .82rem; opacity: .85; }
h2 { font-size: .95rem; margin: 1.4rem 0 .3rem; }
.nota, .esperando, .vacio { opacity: .68; font-size: .82rem; }
.perdida { opacity: .5; font-style: italic; }
small { font-weight: 400; opacity: .6; }
</style>
