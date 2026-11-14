from src.writer import ThingSpeakWriter

print("Conectando con ThingSpeak para enviar una muestra real...")
writer = ThingSpeakWriter()

# Enviamos valores de prueba: 
# core_load=75.5, field_stability=92.0, coolant_flow=88.0, jarvis_latency=12.0, repulsor_power=4500.0
resultado = writer.send_sample(75.5, 92.0, 88.0, 12.0, 4500.0)

print("\n--- RESULTADO DE LA PRUEBA ---")
print(f"¿Éxito?: {resultado.success}")
print(f"Entry ID en ThingSpeak: {resultado.entry_id}")
print(f"Estado HTTP: {resultado.http_status}")
print(f"Mensaje de error: {resultado.error_message}")
print(f"Cooldown restante: {resultado.cooldown_remaining}s")
