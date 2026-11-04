# pva-orchestrator

Orquestador acotado y observable. Sustituye las cinco líneas `OK` y el dashboard verde constantes por estados de descubrimiento y ejecución separados.

```bash
python3 cli.py --workspace ..
python3 cli.py --workspace .. --target ../pva-lint --run-lint
python3 cli.py --workspace .. --target ../pva-lint --run-local
python3 -m unittest discover -s tests -v
```

El modo predeterminado no ejecuta componentes. `--run-lint` ejecuta únicamente los bytes revisados de `pva-lint/cli.py`, comprobados por SHA-256, en Python aislado y sin propagar credenciales del entorno.

El lint requerido es la revisión de preparación de artefactos del repositorio vecino, no la implementación histórica que confunde presencia con validación científica. Ante divergencia del pin se bloquea; no se descarga ni actualiza código automáticamente.

Un lint terminado deja el pipeline en `partial`. Docker, Lean, ledger y swarm siguen `missing` o `discovered_not_executed`; no se genera una certificación 5/5 ni métricas científicas inventadas. La hoja de ruta histórica `pva.yml` no es configuración ejecutable de este lector.

No se construyen contenedores, llama a modelos o escribe un dashboard por defecto. La salida JSON puede ser preservada por un consumidor autorizado; emitirla no acredita persistencia en red.

## Subconjunto local conectado

`--run-local` verifica los cinco programas por SHA-256 y ejecuta sus bytes exactos en Python aislado: preparación de artefactos, resumen CSV, extracción de pendientes de formalización, recibo local del README objetivo e instantánea del registro local. No inicia un servidor ni modifica el registro. Un fallo posterior conserva los resultados previos y devuelve `blocked_partial` con salida 2.

`local_subset_completed` significa únicamente que terminaron estas cinco operaciones acotadas. Las banderas de pipeline completo, Docker, compilación Lean, publicación externa y validación adversarial permanecen falsas. El recibo usa la hora de ejecución, no una autoridad de sellado de tiempo.

Las revisiones requeridas están en borradores que todavía no se fusionaron: [lint](https://github.com/Jaime393/pva-lint/pull/1), [CSV](https://github.com/Jaime393/pva-docker-template/pull/1), [Lean backlog](https://github.com/Jaime393/pva-lean-bridge/pull/1), [recibos](https://github.com/Jaime393/pva-ledger/pull/1) y [registro](https://github.com/Jaime393/pva-swarm/pull/1). No se descargan automáticamente; el operador debe revisar y disponer las revisiones que coinciden con los pins.
