# pva-orchestrator

Orquestador acotado y observable. Sustituye las cinco líneas `OK` y el dashboard verde constantes por estados de descubrimiento y ejecución separados.

```bash
python3 cli.py --workspace ..
python3 cli.py --workspace .. --target ../pva-lint --run-lint
python3 -m unittest discover -s tests -v
```

El modo predeterminado no ejecuta componentes. `--run-lint` ejecuta únicamente los bytes revisados de `pva-lint/cli.py`, comprobados por SHA-256, en Python aislado y sin propagar credenciales del entorno.

El lint requerido es la revisión de preparación de artefactos del repositorio vecino, no la implementación histórica que confunde presencia con validación científica. Ante divergencia del pin se bloquea; no se descarga ni actualiza código automáticamente.

Un lint terminado deja el pipeline en `partial`. Docker, Lean, ledger y swarm siguen `missing` o `discovered_not_executed`; no se genera una certificación 5/5 ni métricas científicas inventadas. La hoja de ruta histórica `pva.yml` no es configuración ejecutable de este lector.

No se construyen contenedores, llama a modelos o escribe un dashboard por defecto. La salida JSON puede ser preservada por un consumidor autorizado; emitirla no acredita persistencia en red.
