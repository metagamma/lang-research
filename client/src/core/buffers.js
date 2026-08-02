// Memoria acotada del cliente.
//
// Una corrida indefinida emite sin fin. Si el navegador guarda todo, la
// pestaña muere en unas horas. Dos estructuras, cada una con su olvido:
//
//   Anillo    los ultimos N episodios, para la vista de mundo. Lo viejo
//             no interesa: se esta viendo lo que pasa AHORA.
//
//   Serie     las metricas por generacion, DECIMADAS: resolucion completa
//             en lo reciente y cada vez mas gruesa hacia atras. Una curva
//             de 100.000 puntos no se lee mejor que una de 600, y cuesta
//             mil veces mas dibujarla.

export class Anillo {
  constructor (tope = 2000) {
    this.tope = tope
    this.datos = []
    this.inicio = 0
  }

  push (x) {
    if (this.datos.length < this.tope) this.datos.push(x)
    else {
      this.datos[this.inicio] = x
      this.inicio = (this.inicio + 1) % this.tope
    }
  }

  // los mas recientes primero
  ultimos (n) {
    const out = []
    const total = this.datos.length
    for (let i = 0; i < Math.min(n, total); i++) {
      out.push(this.datos[(this.inicio + total - 1 - i + total) % total])
    }
    return out
  }
}

export class Serie {
  // finos: cuantos puntos se guardan a resolucion completa
  // factor: cada cuantos se conserva uno al decimar lo viejo
  constructor (finos = 300, factor = 10) {
    this.finos = finos
    this.factor = factor
    this.puntos = []      // {g, ...valores}
    this._n = 0
  }

  push (p) {
    this.puntos.push(p)
    this._n++
    if (this.puntos.length <= this.finos * 2) return
    // conserva completo el tramo reciente y adelgaza el resto
    const corte = this.puntos.length - this.finos
    const viejos = this.puntos.slice(0, corte)
      .filter((_, i) => i % this.factor === 0)
    this.puntos = viejos.concat(this.puntos.slice(corte))
  }

  columna (clave) {
    return this.puntos.map(p => p[clave] ?? null)
  }

  get gens () { return this.puntos.map(p => p.g) }
  get largo () { return this.puntos.length }
  get vistos () { return this._n }
}
