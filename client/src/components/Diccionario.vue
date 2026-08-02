<script setup>
// El diccionario de la lengua que se está inventando ahí dentro.
//
// Es la vista que faltaba. «Coherencia 0.45» es un número; esto es lo
// que ese número SIGNIFICA: cinco palabras vivas para la misma seta, la
// primera con el 45% de la tribu y las otras cuatro peleando.
//
// Cada fila es una entrada de diccionario que nadie escribió. La barra
// muestra el reparto real de la comunidad, no la palabra «correcta» —
// aquí no hay palabra correcta, hay una votación permanente.
import { computed, ref } from 'vue'

const props = defineProps({
  entradas: { type: Array, default: () => [] },
  mundo: { type: Object, default: null },
})

const orden = ref('acuerdo')     // acuerdo | disputa | alfabetico
const filtro = ref('')

// El mundo trae la afordancia de cada cosa. No es conocimiento del
// agente: es física, y sirve para colorear lo que estamos leyendo.
const porNombre = computed(() => {
  const m = {}
  for (const k of props.mundo?.kinds || []) m[k.name] = k
  return m
})

const COLOR = {
  alimento: '#2e9e5b', toxico: '#c0392b', depredador: '#8e44ad',
  agua: '#2980b9', inerte: '#7f8c8d',
}

const filas = computed(() => {
  let f = props.entradas
  if (filtro.value.trim()) {
    const q = filtro.value.trim().toLowerCase()
    f = f.filter(e => e.cosa.toLowerCase().includes(q) ||
                      e.formas.some(([w]) => w.toLowerCase().includes(q)))
  }
  const c = [...f]
  if (orden.value === 'disputa') c.sort((a, b) => b.vivas - a.vivas || a.cuota - b.cuota)
  else if (orden.value === 'alfabetico') c.sort((a, b) => a.cosa.localeCompare(b.cosa))
  else c.sort((a, b) => b.cuota - a.cuota)
  return c
})

// Cuántas entradas están de verdad acordadas. Es la coherencia, contada.
const resumen = computed(() => {
  const n = props.entradas.length
  if (!n) return null
  const firme = props.entradas.filter(e => e.cuota >= 0.7).length
  const disputa = props.entradas.filter(e => e.vivas >= 3).length
  const media = props.entradas.reduce((s, e) => s + e.vivas, 0) / n
  return { n, firme, disputa, media: media.toFixed(2) }
})

function tono (e) {
  const k = porNombre.value[e.cosa]
  return COLOR[k?.affordance] || '#7f8c8d'
}
function pago (e) {
  const k = porNombre.value[e.cosa]
  return k ? k.payoff : null
}
function especie (e) {
  const k = porNombre.value[e.cosa]
  return k?.especie || null
}
</script>

<template>
  <div class="dicc">
    <div class="mandos">
      <input v-model="filtro" placeholder="buscar cosa o palabra…" />
      <select v-model="orden">
        <option value="acuerdo">las más acordadas primero</option>
        <option value="disputa">las más disputadas primero</option>
        <option value="alfabetico">alfabético</option>
      </select>
    </div>

    <p v-if="resumen" class="resumen">
      <b>{{ resumen.firme }}</b> de {{ resumen.n }} cosas tienen nombre
      firme (≥70% de la tribu) · <b>{{ resumen.disputa }}</b> con tres o
      más palabras rivales vivas · media de
      <b>{{ resumen.media }}</b> palabras por cosa.
    </p>

    <p v-if="!filas.length" class="vacio">Todavía no hay nombres.</p>

    <ol class="entradas">
      <li v-for="e in filas" :key="e.cosa">
        <div class="cabeza">
          <span class="punto" :style="{ background: tono(e) }"></span>
          <b class="palabra">{{ e.formas[0][0] }}</b>
          <span class="cuota" :class="{ firme: e.cuota >= 0.7 }">
            {{ Math.round(e.cuota * 100) }}%
          </span>
          <span class="glosa">
            {{ especie(e) || e.cosa }}
            <em v-if="pago(e) !== null">{{ pago(e) > 0 ? '+' : '' }}{{ pago(e) }}</em>
          </span>
        </div>
        <div class="barra">
          <span v-for="([w, q], i) in e.formas" :key="w"
                :style="{ width: (q * 100) + '%',
                          background: i === 0 ? tono(e) : 'rgba(128,128,128,' + (0.5 - i * 0.09) + ')' }"
                :title="w + ' — ' + Math.round(q * 100) + '%'">
            <i v-if="q > 0.14">{{ w }}</i>
          </span>
        </div>
      </li>
    </ol>

    <p class="nota">
      El nombre de la especie es <b>nuestro</b>, para poder leer: el agente
      solo sabe que su palabra acompaña a ciertas cosas. El número es el
      pago —lo que da comerla— y el color, la afordancia. Nada de eso lo
      conoce el agente antes de probarlo.
    </p>
  </div>
</template>

<style scoped>
.dicc { display: flex; flex-direction: column; gap: .6rem; }
.mandos { display: flex; gap: .6rem; flex-wrap: wrap; }
.mandos input { flex: 1; min-width: 12rem; padding: .3rem .5rem;
                border: 1px solid rgba(128,128,128,.35); border-radius: 4px;
                background: transparent; color: inherit; font-size: .85rem; }
.mandos select { padding: .3rem; background: transparent; color: inherit;
                 border: 1px solid rgba(128,128,128,.35); border-radius: 4px;
                 font-size: .85rem; }
.resumen { font-size: .84rem; opacity: .85; margin: 0; }
.entradas { list-style: none; padding: 0; margin: 0; display: flex;
            flex-direction: column; gap: .5rem; max-height: 26rem;
            overflow-y: auto; }
.cabeza { display: flex; align-items: baseline; gap: .45rem; font-size: .86rem; }
.punto { width: 8px; height: 8px; border-radius: 50%; flex: none;
         transform: translateY(-1px); }
.palabra { font-family: ui-monospace, monospace; font-size: 1rem; }
.cuota { font-size: .72rem; opacity: .6; }
.cuota.firme { opacity: 1; color: #2e9e5b; font-weight: 600; }
.glosa { opacity: .6; font-size: .78rem; margin-left: auto; text-align: right; }
.glosa em { font-style: normal; opacity: .8; margin-left: .35rem; }
.barra { display: flex; height: 15px; border-radius: 3px; overflow: hidden;
         background: rgba(128,128,128,.12); }
.barra span { display: flex; align-items: center; overflow: hidden;
              transition: width .4s ease; }
.barra i { font-style: normal; font-size: .62rem; font-family: ui-monospace, monospace;
           color: #fff; padding-left: 3px; white-space: nowrap;
           mix-blend-mode: difference; }
.nota, .vacio { opacity: .6; font-size: .78rem; margin: 0; }
</style>
