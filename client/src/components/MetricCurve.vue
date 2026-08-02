<script setup>
// Una serie. Sin librerias: es una polilinea sobre un canvas.
//
// No se interpola ni se suaviza. Si una metrica se midio cada N
// generaciones, la curva tiene los puntos que tiene — una linea suave
// insinuaria medidas que nadie tomo.
import { onMounted, onUnmounted, ref } from 'vue'

const props = defineProps({
  serie: Object, clave: String, titulo: String, marcas: Array,
})
const lienzo = ref(null)
let raf = null

function dibujar () {
  const c = lienzo.value
  if (!c) return
  const ctx = c.getContext('2d')
  const w = c.width = c.clientWidth, h = c.height = 110
  ctx.clearRect(0, 0, w, h)
  const ys = props.serie.columna(props.clave).filter(v => v != null)
  if (ys.length < 2) return
  const gs = props.serie.gens
  const g0 = gs[0], g1 = gs[gs.length - 1] || 1
  const lo = Math.min(...ys), hi = Math.max(...ys)
  const rango = (hi - lo) || 1
  const X = g => ((g - g0) / Math.max(1, g1 - g0)) * (w - 4) + 2
  const Y = v => h - 6 - ((v - lo) / rango) * (h - 16)

  for (const m of (props.marcas || [])) {
    ctx.strokeStyle = 'rgba(217,131,36,.55)'
    ctx.beginPath(); ctx.moveTo(X(m), 0); ctx.lineTo(X(m), h); ctx.stroke()
  }
  ctx.strokeStyle = '#4a7fd4'
  ctx.lineWidth = 1.4
  ctx.beginPath()
  props.serie.puntos.forEach((p, i) => {
    const v = p[props.clave]
    if (v == null) return
    i === 0 ? ctx.moveTo(X(p.g), Y(v)) : ctx.lineTo(X(p.g), Y(v))
  })
  ctx.stroke()
  ctx.fillStyle = 'rgba(128,128,128,.85)'
  ctx.font = '10px system-ui'
  ctx.fillText(hi.toFixed(3), 3, 11)
  ctx.fillText(lo.toFixed(3), 3, h - 3)
}

function bucle () { dibujar(); raf = requestAnimationFrame(bucle) }
onMounted(() => { raf = requestAnimationFrame(bucle) })
onUnmounted(() => cancelAnimationFrame(raf))
</script>

<template>
  <figure>
    <figcaption>{{ titulo }}
      <small>{{ serie.largo }} pts de {{ serie.vistos }}</small>
    </figcaption>
    <canvas ref="lienzo"></canvas>
  </figure>
</template>

<style scoped>
figure { margin: 0; }
figcaption { font-size: .8rem; opacity: .8; display: flex;
             justify-content: space-between; }
small { opacity: .55; }
canvas { width: 100%; height: 110px; }
</style>
