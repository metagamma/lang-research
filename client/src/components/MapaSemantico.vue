<script setup>
// El mundo tal y como se PERCIBE, y la lengua encima.
//
// Cada punto es un tipo de cosa, colocado por sus rasgos sensoriales
// reales proyectados a dos dimensiones. Lo que revela: qué se parece a
// qué. Y encima, la palabra que la tribu usa para cada uno.
//
// Aquí se ve de un golpe lo que ninguna métrica enseña: si dos cosas
// están pegadas y comparten palabra, la lengua las confunde. Si están
// pegadas y tienen palabras distintas, la lengua consiguió partir algo
// que el ojo no parte solo.
//
// Y con el mundo de setas hay algo que no inventamos nosotros: los
// SOSIAS. Una comestible y una venenosa a distancia mínima. Se marcan con
// una línea roja. Confundirlas mata — es la primera causa de muerte por
// setas en el mundo real, y aquí es una línea entre dos puntos.
import { computed, ref } from 'vue'

const props = defineProps({
  mundo: { type: Object, default: null },
  entradas: { type: Array, default: () => [] },
})

const verPalabras = ref(true)
const verSosias = ref(true)

const COLOR = {
  alimento: '#2e9e5b', toxico: '#c0392b', depredador: '#8e44ad',
  agua: '#2980b9', inerte: '#7f8c8d',
}

// Proyección a 2D por análisis de componentes principales, con iteración
// de potencia. Es media página de aritmética y evita meter una librería
// de álgebra en un cliente de 30 KB.
function pca2 (X) {
  const n = X.length, d = X[0].length
  const mu = new Array(d).fill(0)
  for (const r of X) for (let j = 0; j < d; j++) mu[j] += r[j] / n
  const C = X.map(r => r.map((v, j) => v - mu[j]))

  const mul = v => {                       // (Cᵀ C) v, sin formar la matriz
    const t = new Array(n).fill(0)
    for (let i = 0; i < n; i++) {
      let s = 0
      for (let j = 0; j < d; j++) s += C[i][j] * v[j]
      t[i] = s
    }
    const out = new Array(d).fill(0)
    for (let i = 0; i < n; i++)
      for (let j = 0; j < d; j++) out[j] += C[i][j] * t[i]
    return out
  }
  const norma = v => Math.hypot(...v) || 1
  const unidad = v => { const k = norma(v); return v.map(x => x / k) }

  const potencia = (ortho) => {
    let v = unidad(new Array(d).fill(0).map((_, i) => Math.sin(i * 12.9898 + 3)))
    for (let it = 0; it < 60; it++) {
      let w = mul(v)
      if (ortho) {                          // quita la primera componente
        const p = w.reduce((s, x, j) => s + x * ortho[j], 0)
        w = w.map((x, j) => x - p * ortho[j])
      }
      v = unidad(w)
    }
    return v
  }
  const e1 = potencia(null)
  const e2 = potencia(e1)
  return C.map(r => [
    r.reduce((s, x, j) => s + x * e1[j], 0),
    r.reduce((s, x, j) => s + x * e2[j], 0),
  ])
}

const palabraDe = computed(() => {
  const m = {}
  for (const e of props.entradas) m[e.cosa] = e.formas?.[0] || null
  return m
})

const puntos = computed(() => {
  const kinds = props.mundo?.kinds || []
  if (kinds.length < 3) return []
  const P = pca2(kinds.map(k => k.prototype))
  const xs = P.map(p => p[0]), ys = P.map(p => p[1])
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)]
  const [y0, y1] = [Math.min(...ys), Math.max(...ys)]
  const esc = (v, a, b) => (b - a < 1e-9 ? 0.5 : (v - a) / (b - a))
  return kinds.map((k, i) => ({
    k,
    x: 4 + esc(P[i][0], x0, x1) * 92,
    y: 5 + esc(P[i][1], y0, y1) * 90,
    palabra: palabraDe.value[k.name],
  }))
})

// Sosias: comestible y venenosa que se parecen. Distancia en el espacio
// sensorial COMPLETO, no en la proyección — la proyección engaña.
const sosias = computed(() => {
  const ps = puntos.value
  const out = []
  for (let i = 0; i < ps.length; i++) {
    for (let j = i + 1; j < ps.length; j++) {
      const a = ps[i].k, b = ps[j].k
      const peligro = (a.affordance === 'alimento' && b.affordance === 'toxico') ||
                      (a.affordance === 'toxico' && b.affordance === 'alimento')
      if (!peligro) continue
      let s = 0
      for (let t = 0; t < a.prototype.length; t++) {
        const dd = a.prototype[t] - b.prototype[t]; s += dd * dd
      }
      const d = Math.sqrt(s)
      if (d < 0.42) out.push({ a: ps[i], b: ps[j], d })
    }
  }
  out.sort((p, q) => p.d - q.d)
  return out.slice(0, 14)
})

// ¿La lengua distingue a los sosias, o les da la misma palabra?
const veredicto = computed(() => {
  const s = sosias.value.filter(p => p.a.palabra && p.b.palabra)
  if (!s.length) return null
  const confunde = s.filter(p => p.a.palabra[0] === p.b.palabra[0]).length
  return { total: s.length, confunde, parte: s.length - confunde }
})
</script>

<template>
  <div class="mapa">
    <div class="mandos">
      <label><input type="checkbox" v-model="verPalabras" /> palabras</label>
      <label><input type="checkbox" v-model="verSosias" /> sosias peligrosos</label>
      <span class="leyenda">
        <i v-for="(c, k) in COLOR" :key="k" :style="{ background: c }" :title="k"></i>
        comestible · tóxico · depredador · agua · inerte
      </span>
    </div>

    <svg viewBox="0 0 100 100" preserveAspectRatio="none" class="lienzo">
      <line v-if="verSosias" v-for="(s, i) in sosias" :key="'s' + i"
            :x1="s.a.x" :y1="s.a.y" :x2="s.b.x" :y2="s.b.y"
            stroke="#c0392b" :stroke-width="0.55"
            :stroke-opacity="0.14 + 0.5 * (1 - s.d / 0.42)" />
      <g v-for="(p, i) in puntos" :key="i">
        <circle :cx="p.x" :cy="p.y"
                :r="p.k.sintetico ? 1.0 : 1.5"
                :fill="COLOR[p.k.affordance] || '#888'"
                :fill-opacity="p.palabra ? 0.95 : 0.3"
                :stroke="p.k.sintetico ? '#fff' : 'none'" stroke-width="0.25" />
      </g>
    </svg>

    <div class="etiquetas" v-if="verPalabras">
      <span v-for="(p, i) in puntos" :key="i" v-show="p.palabra"
            class="etiqueta"
            :style="{ left: p.x + '%', top: p.y + '%',
                      color: COLOR[p.k.affordance] || '#888' }"
            :title="(p.k.especie || p.k.name) + ' — pago ' + p.k.payoff">
        {{ p.palabra ? p.palabra[0] : '' }}
      </span>
    </div>

    <p v-if="veredicto" class="veredicto">
      De <b>{{ veredicto.total }}</b> pares comestible/venenosa que se
      parecen, la lengua <b class="parte">distingue {{ veredicto.parte }}</b>
      y <b class="confunde">confunde {{ veredicto.confunde }}</b>.
      Cada confusión es alguien que se va a intoxicar.
    </p>

    <p class="nota">
      Proyección de los rasgos sensoriales a dos dimensiones. La cercanía
      es real: si dos puntos están pegados, esas dos cosas <b>se
      perciben</b> parecidas. Las líneas rojas unen una comestible con una
      venenosa que se le parece — no las elegimos nosotros, salen del
      dataset.
    </p>
  </div>
</template>

<style scoped>
.mapa { position: relative; display: flex; flex-direction: column; gap: .5rem; }
.lienzo { width: 100%; height: 22rem; border: 1px solid rgba(128,128,128,.25);
          border-radius: 6px; background: rgba(128,128,128,.05); }
.etiquetas { position: absolute; inset: 2.1rem 0 auto 0; height: 22rem;
             pointer-events: none; }
.etiqueta { position: absolute; transform: translate(-50%, -160%);
            font-family: ui-monospace, monospace; font-size: .58rem;
            white-space: nowrap; opacity: .9; }
.mandos { display: flex; gap: 1rem; align-items: center; font-size: .8rem;
          flex-wrap: wrap; }
.leyenda { margin-left: auto; opacity: .7; font-size: .74rem; }
.leyenda i { display: inline-block; width: 9px; height: 9px; border-radius: 50%;
             margin-right: 3px; vertical-align: -1px; }
.veredicto { font-size: .84rem; margin: 0; }
.veredicto .parte { color: #2e9e5b; }
.veredicto .confunde { color: #c0392b; }
.nota { opacity: .6; font-size: .78rem; margin: 0; }
</style>
