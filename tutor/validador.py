"""Validación de lo que produce el LLM, ejecutándolo en lugar de confiar en él.

Problemas generados
    El LLM puede equivocarse al calcular "de cabeza" las salidas esperadas
    (por ejemplo, decir que 48392 tiene 2 dígitos pares cuando son 3). Por eso
    se ejecuta la solución de referencia: si no compila o falla, el problema se
    descarta; si da otra salida, se corrige la salida esperada.

Respuestas del tutor
    Si el código de una respuesta pasa todos los casos de prueba, la respuesta
    revela la solución y se bloquea antes de llegar al estudiante.
"""

import ast
import re

from tutor import config, ejecutor


def _arreglar_saltos(texto):
    """Convierte en saltos reales los ``\\n`` que el LLM a veces escribe como texto."""
    return texto.replace("\\n", "\n")


def validar_problema(problema):
    """Comprueba un problema ejecutando su solución de referencia.

    Modifica el problema: normaliza los saltos de línea y reemplaza las salidas
    esperadas que no coinciden con lo que imprime la solución.

    Args:
        problema: ``Problema`` generado por el LLM o tomado del banco.

    Returns:
        Tupla ``(problema, correcciones)``, donde ``correcciones`` describe cada
        salida esperada que se corrigió.

    Raises:
        ValueError: Si la solución no compila o falla en algún caso o en el ejemplo.
    """
    correcciones = []

    problema.ejemplo_entrada = _arreglar_saltos(problema.ejemplo_entrada)
    problema.ejemplo_salida = _arreglar_saltos(problema.ejemplo_salida)
    for caso in problema.casos_prueba:
        caso.entrada = _arreglar_saltos(caso.entrada)
        caso.salida = _arreglar_saltos(caso.salida)

    ok, mensaje = ejecutor.compilar(problema.solucion)
    if not ok:
        raise ValueError(f"La solución de referencia no compila: {mensaje}")

    for i, caso in enumerate(problema.casos_prueba, start=1):
        ok, salida = ejecutor.ejecutar(problema.solucion, caso.entrada)
        if not ok:
            raise ValueError(f"La solución de referencia falla en el caso {i}")
        if ejecutor.normalizar(salida) != ejecutor.normalizar(caso.salida):
            correcciones.append(f"Caso {i}: el LLM esperaba '{caso.salida.strip()}', "
                                f"la solución da '{salida.strip()}'")
            caso.salida = salida.strip()

    # El ejemplo es lo que ve el estudiante: se verifica igual que los casos.
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
    """Pide problemas hasta obtener uno cuya solución funcione.

    El generador se recibe como parámetro (inyección de dependencias): puede
    ser ``llm.generar_problema``, ``banco.problema_del_banco`` o un generador
    falso en las pruebas.

    Args:
        nivel: Nivel del problema (``"novato"``, ``"intermedio"`` o ``"avanzado"``).
        titulos_previos: Títulos ya vistos en la sesión, para no repetirlos.
        generar: Función ``generar(nivel, titulos_previos) -> Problema``. Si lanza
            ``ValueError`` (por ejemplo, JSON inválido del LLM) cuenta como un
            intento fallido.
        intentos: Número máximo de problemas que se piden.

    Returns:
        Tupla ``(problema, correcciones)`` del primer problema válido.

    Raises:
        ValueError: Si ningún intento produce un problema válido.
    """
    ultimo_error = None
    for _ in range(intentos):
        try:
            return validar_problema(generar(nivel, titulos_previos))
        except ValueError as error:
            ultimo_error = error
    raise ValueError(f"no se obtuvo un problema válido en {intentos} intentos ({ultimo_error})")


# --- Respuestas del tutor: detectar y bloquear la fuga de la solución ---

PISTA_FIJA = ("No puedo darte la solución, pero sí ayudarte a llegar a ella. Divide el "
              "problema en pasos: ¿qué datos lees, qué debes calcular con ellos y qué "
              "imprimes al final?\n\n**Próximo paso:** escribe en el editor sólo la lectura "
              "de los datos y pruébala con Ejecutar.")

AVISO_REGENERAR = ("[Aviso del sistema] Tu respuesta anterior incluía código que resuelve el "
                   "problema completo y eso no está permitido. Responde de nuevo a la última "
                   "pregunta del estudiante SÓLO con una pista o una pregunta guía, sin código "
                   "que resuelva el problema.")


def extraer_codigo(texto):
    """Regresa el contenido de los bloques de código Markdown (```` ``` ````) del texto."""
    return [b.strip() for b in re.findall(r"```[^\n`]*\n(.*?)```", texto, re.DOTALL) if b.strip()]


def _sin_definiciones(codigo, nombres):
    """Quita del código las funciones y clases cuyos nombres están en ``nombres``.

    Returns:
        El código resultante, o None si el código no se puede analizar.
    """
    try:
        arbol = ast.parse(codigo)
    except SyntaxError:
        return None
    arbol.body = [n for n in arbol.body
                  if not (isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in nombres)]
    return ast.unparse(arbol)


def _candidatos(bloques, codigo_estudiante):
    """Arma los programas que se ejecutan para buscar una fuga.

    Incluye cada bloque, todos los bloques juntos y cada bloque completado con
    el código del estudiante. Lo último cubre el caso "sólo completa el cuerpo
    de la función": el bloque solo no imprime nada, pero con el resto del
    programa del estudiante sí resuelve el problema.
    """
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
    """Indica si una respuesta del tutor contiene la solución del problema.

    Args:
        respuesta: Texto de la respuesta (Markdown).
        problema: ``Problema`` con los casos de prueba.
        codigo_estudiante: Código actual del estudiante, para completar bloques parciales.

    Returns:
        True si algún código de la respuesta pasa TODOS los casos de prueba.
    """
    for candidato in _candidatos(extraer_codigo(respuesta), codigo_estudiante):
        if not ejecutor.compilar(candidato)[0]:
            continue
        if all(r["paso"] for r in ejecutor.evaluar_pruebas(candidato, problema.casos_prueba)):
            return True
    return False


def respuesta_segura(pedir, historial, problema, nivel, codigo, consola):
    """Pide una respuesta al tutor y la bloquea si revela la solución.

    Si la respuesta revela la solución, se pide otra sólo con pista; si la nueva
    también la revela (o falla la llamada), se usa ``PISTA_FIJA``.

    Args:
        pedir: Función ``pedir(historial, problema, nivel, codigo, consola) -> str``
            (normalmente ``llm.pedir_ayuda``; en las pruebas, un tutor falso).
        historial: Mensajes del chat, terminando con la pregunta del estudiante.
        problema: ``Problema`` actual.
        nivel: Nivel del problema.
        codigo: Código actual del estudiante.
        consola: Última salida de la consola.

    Returns:
        Tupla ``(respuesta_final, respuesta_original, estado)``, donde ``estado``
        es ``"ok"``, ``"regenerada"`` o ``"reemplazada"``.
    """
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
