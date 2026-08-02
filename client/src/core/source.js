// Conexion con el backend en vivo.
//
// SSE y no WebSocket: el flujo va en un solo sentido y el navegador trae
// la reconexion de serie. El control va por POST aparte.
//
// Quien llega tarde arranca por /state: una corrida de doce horas no se
// descarga entera para ver que esta pasando ahora.

const BASE = import.meta.env.DEV ? 'http://localhost:8080' : ''

export function crearFuente (manejadores) {
  let es = null
  let vivo = false

  async function arrancar () {
    const mundo = await fetch(`${BASE}/world`).then(r => r.json())
    manejadores.mundo?.(mundo)
    const estado = await fetch(`${BASE}/state`).then(r => r.json())
    manejadores.instantanea?.(estado)
    conectar()
    return mundo
  }

  function conectar () {
    es = new EventSource(`${BASE}/stream`)
    for (const canal of ['episodio', 'generacion', 'instantanea', 'oracion',
                         'corte', 'tribu_perdida', 'fin']) {
      es.addEventListener(canal, e => {
        vivo = true
        manejadores[canal]?.(JSON.parse(e.data))
      })
    }
    // EventSource reconecta solo; solo hace falta avisar de que se cayo
    es.onerror = () => { vivo = false; manejadores.corte_conexion?.() }
  }

  async function control (orden) {
    return fetch(`${BASE}/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(orden),
    }).then(r => r.json())
  }

  return { arrancar, control, cerrar: () => es?.close(), estaVivo: () => vivo }
}
