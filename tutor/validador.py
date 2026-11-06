"""Valida lo que produce el LLM ejecutándolo, en lugar de confiar en él.

1. Problemas generados: el LLM puede equivocarse al calcular "de cabeza" las
   salidas esperadas (ej. 48392 -> dijo 2 dígitos pares, son 3), así que:
     - si la solución no compila o truena  -> el problema se descarta
     - si la solución da otra salida       -> se corrige la salida esperada
   Si el problema se descarta, generar_problema_validado pide otro.
2. Respuestas del tutor: si el código que muestra pasa los casos de prueba,
   reveló la solución; respuesta_segura la bloquea.
"""

import ast
import re

from tutor import config, ejecutor


def _arreglar_saltos(texto):
    """A veces el LLM escribe '\\n' como texto en lugar de un salto de línea real."""
    return texto.replace("\\n", "\n")


def validar_problema(problema):
    """Regresa (problema, correcciones). Lanza ValueError si la solución no sirve."""
    correcciones = []

    # 1. Normalizar saltos de línea
    problema.ejemplo_entrada = _arreglar_saltos(problema.ejemplo_entrada)
    problema.ejemplo_salida = _arreglar_saltos(problema.ejemplo_salida)
    for caso in problema.casos_prueba:
        caso.entrada = _arreglar_saltos(caso.entrada)
        caso.salida = _arreglar_saltos(caso.salida)

    # 2. La solución debe compilar
    ok, mensaje = ejecutor.compilar(problema.solucion)
    if not ok:
        raise ValueError(f"La solución de referencia no compila: {mensaje}")

    # 3. Ejecutar la solución con cada caso de prueba
    for i, caso in enumerate(problema.casos_prueba, start=1):
        ok, salida = ejecutor.ejecutar(problema.solucion, caso.entrada)
        if not ok:
            raise ValueError(f"La solución de referencia falla en el caso {i}")
        if ejecutor.normalizar(salida) != ejecutor.normalizar(caso.salida):
            correcciones.append(f"Caso {i}: el LLM esperaba '{caso.salida.strip()}', "
                                f"la solución da '{salida.strip()}'")
            caso.salida = salida.strip()

    # 4. Lo mismo con el ejemplo que ve el estudiante
    ok, salida = ejecutor.ejecutar(problema.solucion, problema.ejemplo_entrada)
    if not ok:
        raise ValueError("La solución de referencia falla con el ejemplo")
    if ejecutor.normalizar(salida) != ejecutor.normalizar(problema.ejemplo_salida):
        correcciones.append(f"Ejemplo: el LLM esperaba '{problema.ejemplo_salida.strip()}', "
                            f"la solución da '{salida.strip()}'")
        problema.ejemplo_salida = salida.strip()

    return problema, correcciones


def generar_problema_validado(nivel, titulos_previos, generar,
                              intentos=config.INTENTOS_GENERACION):
    """generar(nivel, titulos_previos) -> Problema. Se recibe como parámetro
    (inyección de dependencias): así se prueba con un generador falso, sin gastar cuota.
    Un intento falla si la solución no funciona o si generar lanza ValueError
    (por ejemplo, JSON inválido del LLM). Regresa (problema, correcciones).
    Lanza ValueError si ningún intento sirve."""
    ultimo_error = None
    for _ in range(intentos):
        try:
            return validar_problema(generar(nivel, titulos_previos))
        except ValueError as error:
            ultimo_error = error
    raise ValueError(f"no se obtuvo un problema válido en {intentos} intentos ({ultimo_error})")


# =====================================================================
# Respuestas del tutor: detectar y bloquear la fuga de la solución
# =====================================================================

PISTA_FIJA = ("No puedo darte la solución, pero sí ayudarte a llegar a ella. Divide el "
              "problema en pasos: ¿qué datos lees, qué debes calcular con ellos y qué "
              "imprimes al final?\n\n**Próximo paso:** escribe en el editor sólo la lectura "
              "de los datos y pruébala con Ejecutar.")

AVISO_REGENERAR = ("[Aviso del sistema] Tu respuesta anterior incluía código que resuelve el "
                   "problema completo y eso no está permitido. Responde de nuevo a la última "
                   "pregunta del estudiante SÓLO con una pista o una pregunta guía, sin código "
                   "que resuelva el problema.")


def extraer_codigo(texto):
    """Bloques de código Markdown (```python ... ```) de una respuesta."""
    return [b.strip() for b in re.findall(r"```[^\n`]*\n(.*?)```", texto, re.DOTALL) if b.strip()]


def _sin_definiciones(codigo, nombres):
    """El código del estudiante sin las funciones o clases que el tutor redefine."""
    try:
        arbol = ast.parse(codigo)
    except SyntaxError:
        return None
    arbol.body = [n for n in arbol.body
                  if not (isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in nombres)]
    return ast.unparse(arbol)


def _candidatos(bloques, codigo_estudiante):
    """Programas a probar: cada bloque, todos juntos y cada bloque completado con el
    código del estudiante (caso "sólo completa el cuerpo de la función")."""
    candidatos = list(bloques)
    if len(bloques) > 1:
        candidatos.append("\n\n".join(bloques))
    for bloque in bloques:
        try:
            nombres = {n.name for n in ast.parse(bloque).body
                       if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        except SyntaxError:
            continue
        resto = _sin_definiciones(codigo_estudiante, nombres) if nombres else None
        if resto:
            candidatos.append(bloque + "\n\n" + resto)
    return candidatos


def revela_solucion(respuesta, problema, codigo_estudiante=""):
    """True si algún código de la respuesta pasa TODOS los casos de prueba."""
    for candidato in _candidatos(extraer_codigo(respuesta), codigo_estudiante):
        if not ejecutor.compilar(candidato)[0]:
            continue
        if all(r["paso"] for r in ejecutor.evaluar_pruebas(candidato, problema.casos_prueba)):
            return True
    return False


def respuesta_segura(pedir, historial, problema, nivel, codigo, consola):
    """Filtro en tiempo real. pedir(historial, problema, nivel, codigo, consola) -> texto
    se recibe por inyección, como generar.
    Regresa (respuesta final, respuesta original, estado), con estado:
    'ok' | 'regenerada' (se pidió otra sólo con pista) | 'reemplazada' (pista fija)."""
    original = pedir(historial, problema, nivel, codigo, consola)
    if not revela_solucion(original, problema, codigo):
        return original, original, "ok"

    historial_aviso = historial + [{"role": "assistant", "content": original},
                                   {"role": "user", "content": AVISO_REGENERAR}]
    try:
        nueva = pedir(historial_aviso, problema, nivel, codigo, consola)
    except Exception:
        nueva = None
    if nueva and not revela_solucion(nueva, problema, codigo):
        return nueva, original, "regenerada"
    return PISTA_FIJA, original, "reemplazada"
