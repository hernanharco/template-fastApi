#!/usr/bin/env python3
"""
Test rápido para verificar el flujo de agentes
"""
import asyncio
import json
from app.agents.routing.graph import graph

async def test_flow():
    print("🧪 TEST DE FLUJO DE AGENTES")
    print("=" * 50)
    
    # Simular mensaje de "hola" de cliente existente
    initial_state = {
        "messages": [{"role": "user", "content": "hola"}],
        "client_phone": "34634405549",
        "client_name": "Hernán",  # Cliente existente
    }
    
    print(f"📥 Input: {initial_state}")
    print()
    
    try:
        # Ejecutar el grafo
        result = await graph.ainvoke(initial_state)
        
        print("✅ FLOJO COMPLETADO")
        print(f"📤 Result: {json.dumps(result, indent=2, default=str)}")
        
        # Verificar el flujo
        if "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                content = last_message.content
                print(f"💬 Respuesta: {content[:100]}...")
                
                # Verificar que no sea un saludo repetitivo
                if "bienvenido" in content.lower() and "servicios" in content.lower():
                    print("🎯 FLUJO CORRECTO: Mostró catálogo de servicios")
                else:
                    print("⚠️ FLUJO INCORRECTO: No mostró catálogo")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_flow())
