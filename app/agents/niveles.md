🟢 Nivel 1: Prompt Engineering (Lo que estamos haciendo)
Problema: Es impredecible. La IA es creativa por naturaleza, y tú necesitas que sea un robot aburrido y exacto.
Cuándo se usa: Solo para prototipos rápidos.

🔵 Nivel 2: "Structured Outputs" y Esquemas (Lo que necesitas)
En lugar de decirle a la IA "Responde en JSON", usas una técnica donde obligas a la IA a seguir un esquema rígido (como un molde de pastel). Si la IA intenta salirse del molde, el sistema ni siquiera acepta la respuesta.

Cómo hacerlo rápido:

Pydantic: Usas una librería de Python para definir exactamente qué campos quieres.

OpenAI Tools / Function Calling: En lugar de un prompt gigante, le das a la IA "herramientas" (ej: una herramienta para buscar citas, otra para saludar). La IA no "decide qué escribir", decide "qué herramienta usar".

🔴 Nivel 3: Frameworks de Agentes (LangGraph / CrewAI)
Para "cosas grandes", no escribes if/else. Usas grafos donde defines estados. Es más complejo de aprender, pero es lo que usan las empresas que procesan miles de citas.

Carpeta / Archivo,Función (Principio SRP)
app/agents/,"Contenedor: Directorio raíz que agrupa toda la lógica, estados y nodos de la IA."
agent_state.py,"La Memoria: Define el esquema de datos (TypedDict) que Valeria recuerda durante la sesión (fecha, hora, servicio)."
greeting_node.py,La Voz: Nodo dedicado exclusivamente a generar el saludo y mantener el tono humano de la conversación.
graph_builder.py,"El Mapa: Configura el flujo de LangGraph, definiendo qué nodo sigue a cuál y dónde empieza/termina el proceso."
orchestrator.py,"El Puente: Clase encargada de conectar FastAPI con el grafo, manejando la entrada de WhatsApp y la sesión de DB."

1. Extractor Node (El Traductor)
Su función: Es el único que "lee" el lenguaje humano.

Responsabilidad: Convertir el texto sucio del usuario en datos limpios (JSON). No sabe nada de bases de datos, solo sabe de gramática e intenciones.

2. Availability Node (El Bibliotecario)
Su función: Es el puente con tus modelos de SQLAlchemy (Neon).

Responsabilidad: Ir a la base de datos y decir: "¿Hay hueco el miércoles?". No decide qué responder, solo entrega los datos crudos.

3. Orchestrator (El Jefe de Departamento)
Aquí es donde estaba tu duda. En tu estructura, el Orchestrator (ej: BookingOrchestrator) es el que maneja un dominio específico.

Su función: Recibir los datos del Extractor y los datos del Availability Node para armar la respuesta final.

Responsabilidad: "Si el Availability Node dice que no hay citas, yo (el Orquestador) redacto el mensaje: Lo siento, no hay cupo, pero tengo estos otros días...".

Diferencia con el Master: El Master es el "Dueño del Negocio" (manda a todo el bot). El Orquestador de Booking es solo el "Gerente de Citas".

4. Graph Builder (El Mapa de Carreteras)
Su función: Definir el orden.

Responsabilidad: Dice: "Primero ejecuta el Extractor, LUEGO pasa al Orquestador de Booking". Si usas LangGraph, aquí es donde dibujas las flechas.