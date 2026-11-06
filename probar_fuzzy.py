from fuzzy_nivel import tiempo, errores, ayudas, fuzzificar, inferir

# Paso 1: fuzzificación (compara con la tabla del ejemplo a mano)
print("tiempo = 10  ->", fuzzificar(tiempo, 10))
print("errores = 4  ->", fuzzificar(errores, 4))
print("ayudas = 1.5 ->", fuzzificar(ayudas, 1.5))

# Resultado final
valor, etiqueta, _ = inferir(2, 0, 8)
print(f"\nNivel = {valor:.2f} ({etiqueta})")