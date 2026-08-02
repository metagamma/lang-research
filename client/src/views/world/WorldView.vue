<script setup>
// Vista de mundo. Canvas 2D con POSICIONES REALES.
//
// Hasta la Fase 9 el modelo no tenia espacio y esta vista habria tenido
// que inventarse una disposicion. Ya no: los lugares tienen coordenadas y
// los agentes posicion. Lo que se dibuja es lo que hay.
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { mundo, episodios, tic, instantanea } from '../../core/state.js'

const lienzo = ref(null)
const verNombres = ref(false)   // los nombres latentes, ocultos por defecto
let raf = null

const COLOR = { ok: '#2e9e5b', fallo: '#d98324', perdida: '#8a8f98' }

function dibujar () {
  const c = lienzo.value
  if (!c || !mundo.value) return
  const ctx = c.getContext('2d')
  const w = c.width = c.clientWidth
  const h = c.height = c.clientHeight
  ctx.clearRect(0, 0, w, h)
  const X = x => x * w, Y = y => y * h

  // regiones
  ctx.font = '11px system-ui'
  for (const p of mundo.value.places) {
    ctx.beginPath()
    ctx.arc(X(p.x), Y(p.y), 34, 0, 7)
    ctx.strokeStyle = 'rgba(128,128,128,.28)'
    ctx.stroke()
    ctx.fillStyle = 'rgba(128,128,128,.75)'
    ctx.fillText(p.name, X(p.x) - 16, Y(p.y) - 40)
  }

  // señales recientes: las mas nuevas, mas opacas
  const recientes = episodios.ultimos(140)
  recientes.forEach((e, i) => {
    if (!e.p) return
    const a = e.p[e.sp], b = e.p[e.li]
    if (!a || !b) return
    const alfa = (1 - i / 140) * 0.85
    ctx.globalAlpha = alfa
    ctx.strokeStyle = !e.sig ? 'rgba(0,0,0,0)'
      : e.und ? (e.ok ? COLOR.ok : COLOR.fallo) : COLOR.perdida
    ctx.lineWidth = e.desc ? 2.5 : 1.2
    ctx.setLineDash(e.past ? [3, 3] : [])
    ctx.beginPath()
    ctx.moveTo(X(a[0]), Y(a[1]))
    ctx.lineTo(X(b[0]), Y(b[1]))
    ctx.stroke()
    ctx.setLineDash([])
    // el hablante
    ctx.fillStyle = e.t === 0 ? '#4a7fd4' : '#c25bb0'
    ctx.beginPath()
    ctx.arc(X(a[0]), Y(a[1]), 3.5, 0, 7)
    ctx.fill()
    if (verNombres.value && i < 12 && e.k) {
      ctx.globalAlpha = alfa
      ctx.fillStyle = 'rgba(128,128,128,.9)'
      ctx.fillText(e.k, X(b[0]) + 6, Y(b[1]) - 4)
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
      <label>
        <input type="checkbox" v-model="verNombres" />
        ojo de dios (nombres latentes)
      </label>
      <span class="leyenda">
        <i :style="{background: COLOR.ok}"></i> entendida y acertada
        <i :style="{background: COLOR.fallo}"></i> entendida y fallada
        <i :style="{background: COLOR.perdida}"></i> no entendida
        · punteado = pasado · grueso = descripción
      </span>
    </div>
    <canvas ref="lienzo"></canvas>
    <p class="nota">
      Posiciones reales del modelo. Cada trazo es un episodio: alguien
      dijo algo a alguien y el color cuenta cómo acabó.
    </p>
  </section>
</template>

<style scoped>
.mundo { display: flex; flex-direction: column; height: 78vh; }
canvas { flex: 1; border: 1px solid rgba(128,128,128,.25); border-radius: 6px; }
.barra { display: flex; gap: 1.5rem; align-items: center; margin-bottom: .5rem;
         font-size: .82rem; flex-wrap: wrap; }
.leyenda i { display: inline-block; width: 10px; height: 10px; border-radius: 2px;
             margin: 0 .2rem 0 .6rem; vertical-align: -1px; }
.nota { opacity: .6; font-size: .8rem; }
</style>
