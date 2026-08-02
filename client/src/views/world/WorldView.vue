<script setup>
// Vista de mundo. Canvas 2D con POSICIONES REALES.
//
// Hasta la Fase 9 el modelo no tenía espacio y esta vista habría tenido
// que inventarse una disposición. Ya no: los lugares tienen coordenadas
// y los agentes posición. Lo que se dibuja es lo que hay.
//
// Qué se ve, y por qué esto y no otra cosa:
//
//   los agentes      todos, no solo los que hablan. El tamaño es su
//                    energía y el anillo su edad. Se ve morir gente.
//   las señales      cada trazo es alguien diciéndole algo a alguien.
//                    El color cuenta cómo acabó, que es el dato.
//   los lugares      con su nombre real y su coste de viaje. En el mundo
//                    de setas son hábitats de verdad: bosque, brezal…
//   las alarmas      un anillo que se expande. Es el único canal que no
//                    emergió, y verlo fallar vale más que no verlo.
//
// La regla del CLAUDE.md de esta capa sigue en pie: aquí no se
// reimplementa nada del modelo. Todo lo que se dibuja llega por el stream.
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { mundo, episodios, instantanea, tic, oraciones, gen }
  from '../../core/state.js'
import Oraciones from '../../components/Oraciones.vue'

const lienzo = ref(null)
const verNombres = ref(false)     // los nombres latentes, ocultos por defecto
const verAgentes = ref(true)
const verRastro = ref(true)
let raf = null

const COLOR = { ok: '#2e9e5b', fallo: '#d98324', perdida: '#8a8f98' }
const TRIBU = ['#4a7fd4', '#c25bb0', '#e0a03a', '#3fb6a8']
const AFOR = {
  alimento: '#2e9e5b', toxico: '#c0392b', depredador: '#8e44ad',
  agua: '#2980b9', inerte: '#7f8c8d',
}

const kindPorNombre = computed(() => {
  const m = {}
  for (const k of mundo.value?.kinds || []) m[k.name] = k
  return m
})

// Contadores en vivo, sacados del anillo de episodios: lo que está
// pasando AHORA, no una media de toda la corrida.
const pulso = computed(() => {
  tic.value
  const e = episodios.ultimos(300)
  if (!e.length) return null
  const conSenal = e.filter(x => x.sig)
  const ent = conSenal.filter(x => x.und)
  return {
    n: e.length,
    habla: conSenal.length / e.length,
    entiende: conSenal.length ? ent.length / conSenal.length : 0,
    acierta: ent.length ? ent.filter(x => x.ok).length / ent.length : 0,
    alarmas: e.filter(x => x.alarm).length,
    pasado: conSenal.filter(x => x.past).length,
    desc: conSenal.filter(x => x.desc).length,
  }
})

function dibujar () {
  const c = lienzo.value
  if (!c || !mundo.value) return
  const ctx = c.getContext('2d')
  const w = c.width = c.clientWidth
  const h = c.height = c.clientHeight
  ctx.clearRect(0, 0, w, h)
  const X = x => x * w, Y = y => y * h

  // --- lugares -------------------------------------------------------
  ctx.font = '11px system-ui'
  for (const p of mundo.value.places) {
    const r = 26 + p.cost * 5
    const g = ctx.createRadialGradient(X(p.x), Y(p.y), 2, X(p.x), Y(p.y), r)
    g.addColorStop(0, 'rgba(128,128,128,.10)')
    g.addColorStop(1, 'rgba(128,128,128,0)')
    ctx.fillStyle = g
    ctx.beginPath(); ctx.arc(X(p.x), Y(p.y), r, 0, 7); ctx.fill()
    ctx.beginPath(); ctx.arc(X(p.x), Y(p.y), r, 0, 7)
    ctx.strokeStyle = 'rgba(128,128,128,.22)'; ctx.lineWidth = 1; ctx.stroke()
    ctx.fillStyle = 'rgba(128,128,128,.8)'
    ctx.fillText(p.name, X(p.x) - ctx.measureText(p.name).width / 2, Y(p.y) - r - 5)
    ctx.fillStyle = 'rgba(128,128,128,.45)'
    const cst = 'coste ' + p.cost
    ctx.fillText(cst, X(p.x) - ctx.measureText(cst).width / 2, Y(p.y) + r + 12)
  }

  // --- agentes vivos -------------------------------------------------
  if (verAgentes.value) {
    const tribus = instantanea.value?.tribus || []
    tribus.forEach((t, ti) => {
      if (!t) return
      for (const a of t.agentes || []) {
        if (a.x == null) continue
        const e = Math.max(0, Math.min(1, a.e / 40))
        ctx.beginPath()
        ctx.arc(X(a.x), Y(a.y), 3 + e * 4, 0, 7)
        ctx.fillStyle = TRIBU[ti % TRIBU.length]
        ctx.globalAlpha = 0.25 + 0.6 * e
        ctx.fill()
        ctx.globalAlpha = 1
        if (a.edad > 18) {          // los viejos llevan corona
          ctx.beginPath()
          ctx.arc(X(a.x), Y(a.y), 7 + e * 3, 0, 7)
          ctx.strokeStyle = 'rgba(200,200,200,.35)'
          ctx.lineWidth = 1
          ctx.stroke()
        }
      }
    })
  }

  // --- señales recientes ---------------------------------------------
  const N = verRastro.value ? 160 : 40
  const recientes = episodios.ultimos(N)
  recientes.forEach((e, i) => {
    if (!e.p) return
    const a = e.p[e.sp], b = e.p[e.li]
    if (!a || !b) return
    const alfa = (1 - i / N) * 0.9
    ctx.globalAlpha = alfa

    if (e.alarm) {                  // un anillo que se expande
      ctx.beginPath()
      ctx.arc(X(a[0]), Y(a[1]), 6 + (i < 30 ? (30 - i) : 0), 0, 7)
      ctx.strokeStyle = '#8e44ad'; ctx.lineWidth = 1.4; ctx.stroke()
    }

    if (e.sig) {
      ctx.strokeStyle = e.und ? (e.ok ? COLOR.ok : COLOR.fallo) : COLOR.perdida
      ctx.lineWidth = e.desc ? 2.6 : 1.2
      ctx.setLineDash(e.past ? [3, 3] : [])
      ctx.beginPath()
      ctx.moveTo(X(a[0]), Y(a[1]))
      ctx.lineTo(X(b[0]), Y(b[1]))
      ctx.stroke()
      ctx.setLineDash([])
    }

    const k = kindPorNombre.value[e.k]
    if (k) {                        // de QUE se habla
      ctx.fillStyle = AFOR[k.affordance] || '#888'
      ctx.beginPath()
      ctx.arc(X((a[0] + b[0]) / 2), Y((a[1] + b[1]) / 2), 2.2, 0, 7)
      ctx.fill()
    }

    ctx.fillStyle = TRIBU[e.t % TRIBU.length]
    ctx.beginPath(); ctx.arc(X(a[0]), Y(a[1]), 3.2, 0, 7); ctx.fill()

    if (verNombres.value && i < 14 && e.k) {
      ctx.fillStyle = 'rgba(190,190,190,.95)'
      ctx.fillText(k?.especie || e.k, X(b[0]) + 6, Y(b[1]) - 4)
    }
  })
  ctx.globalAlpha = 1
}

function bucle () { dibujar(); raf = requestAnimationFrame(bucle) }
onMounted(() => { raf = requestAnimationFrame(bucle) })
onUnmounted(() => cancelAnimationFrame(raf))
watch(tic, () => {})
</script>

<template>
  <section class="mundo">
    <div class="barra">
      <label><input type="checkbox" v-model="verAgentes" /> agentes</label>
      <label><input type="checkbox" v-model="verRastro" /> rastro largo</label>
      <label><input type="checkbox" v-model="verNombres" /> ojo de dios</label>
      <span class="leyenda">
        <i :style="{ background: COLOR.ok }"></i> entendida y acertada
        <i :style="{ background: COLOR.fallo }"></i> entendida y fallada
        <i :style="{ background: COLOR.perdida }"></i> no entendida
        · punteado = pasado · grueso = descripción
      </span>
    </div>

    <div v-if="pulso" class="pulso">
      <div><b>{{ gen }}</b><span>generación</span></div>
      <div><b>{{ Math.round(pulso.habla * 100) }}%</b><span>habla</span></div>
      <div><b>{{ Math.round(pulso.entiende * 100) }}%</b><span>se entiende</span></div>
      <div><b>{{ Math.round(pulso.acierta * 100) }}%</b><span>y acierta</span></div>
      <div><b>{{ pulso.pasado }}</b><span>del pasado</span></div>
      <div><b>{{ pulso.desc }}</b><span>descripciones</span></div>
      <div><b>{{ pulso.alarmas }}</b><span>alarmas</span></div>
      <small>en los últimos {{ pulso.n }} episodios</small>
    </div>

    <div class="escena">
      <canvas ref="lienzo"></canvas>
      <aside>
        <h3>Lo que se está diciendo</h3>
        <Oraciones :oraciones="oraciones" />
      </aside>
    </div>

    <p class="nota">
      Posiciones reales del modelo. Cada trazo es un episodio: alguien dijo
      algo a alguien y el color cuenta cómo acabó. El tamaño de un agente
      es su energía; el anillo, que ya es viejo. El punto en mitad del
      trazo dice <b>de qué</b> se habla — verde comestible, rojo tóxico,
      morado depredador.
    </p>
  </section>
</template>

<style scoped>
.mundo { display: flex; flex-direction: column; height: 84vh; }
.escena { flex: 1; display: grid; grid-template-columns: 1fr 22rem;
          gap: 1rem; min-height: 0; }
aside { overflow-y: auto; padding-right: .3rem; }
aside h3 { font-size: .85rem; margin: 0 0 .5rem; opacity: .8; }
canvas { min-height: 0; border: 1px solid rgba(128,128,128,.25); border-radius: 6px; }
.barra { display: flex; gap: 1.1rem; align-items: center; margin-bottom: .4rem;
         font-size: .82rem; flex-wrap: wrap; }
.leyenda { margin-left: auto; opacity: .8; }
.leyenda i { display: inline-block; width: 10px; height: 10px; border-radius: 2px;
             margin: 0 .2rem 0 .6rem; vertical-align: -1px; }
.pulso { display: flex; gap: 1.5rem; align-items: baseline; margin-bottom: .5rem;
         padding: .4rem .7rem; border: 1px solid rgba(128,128,128,.2);
         border-radius: 5px; flex-wrap: wrap; }
.pulso div { display: flex; flex-direction: column; }
.pulso b { font-size: 1.15rem; }
.pulso span { font-size: .7rem; opacity: .6; }
.pulso small { margin-left: auto; opacity: .5; font-size: .72rem; }
.nota { opacity: .62; font-size: .8rem; }
</style>
