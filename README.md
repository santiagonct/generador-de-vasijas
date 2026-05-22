# generador-de-vasijas

Genera archivos `.gcode` listos para imprimir en sistemas Marlin. La forma de la pieza generada se controla con funciones matemáticas simples: el radio de cada capa varía según una ecuación, produciendo superficies onduladas o irregulares. Una vez generado el archivo se puede visualizar con un slicer antes de imprimir.

El script no cuenta con generacion de soportes y los archivos pueden tener problemas al momento de imprimir.
 
---
 
## Instalación
 
```bash
pip install numpy
```
 
---
 
## Uso básico
 
```bash
python generador_gcode.py
```
 
Genera una vasija con parámetros por defecto: modo `seno`, radio 25mm, altura 60mm, 2 paredes. El archivo se guarda automáticamente como `vasija_modo_YYYYMMDD_HHMMSS.gcode`.
 
---
 
## Parámetros
 
| Parámetro | Default | Descripción |
|---|---|---|
| `--modo` | `seno` | Tipo de superficie (ver modos abajo) |
| `--radio` | `25.0` | Radio base en mm |
| `--altura` | `60.0` | Altura total en mm |
| `--amplitud` | `3.0` | Amplitud de la onda en mm |
| `--frecuencia` | `6.0` | Ciclos de onda a lo largo de la altura |
| `--capa` | `0.2` | Altura de capa en mm |
| `--puntos` | `90` | Puntos por círculo — más puntos = superficie más suave |
| `--paredes` | `2` | Número de paredes por capa |
| `--salida` | auto | Nombre del archivo de salida |
 
---
 
## Modos de superficie
 
### `seno` 
El radio sube y baja uniformemente a lo largo de la altura.
```
r(z) = R + A · sin(f · z)
```
```bash
python generador_gcode.py --modo sine --amplitud 3 --frecuencia 6
```
 
### `doble` 
Dos frecuencias superpuestas. La forma es más orgánica e irregular que `seno`.
```
r(z) = R + 0.7A · sin(f·z) + 0.3A · sin(2.3f·z)
```
```bash
python generador_gcode.py --modo doble --amplitud 4
```
 
### `cono` 
El radio crece y la vasija se ensancha en forma de cono hasta que el patron se repite`
r(z) = R + (A/2)·(z/h) + (A/2)·sin(f·z)
```
```bash
python generador_gcode.py --modo cono --amplitud 5 --altura 80
```
 
### `ruido` 
Suma de armónicos con frecuencias y fases distintas. Superficie irregular pero continua, sin bordes abruptos.
```bash
python generador_gcode.py --modo ruido --amplitud 4 --frecuencia 4
```
 
---
 
## Paredes
 
Cada capa imprime una cantidad de paredes, perímetros concéntricos. El exterior sigue la función matemática, los interiores están separados una distancia del diámetro de boquilla (0.4mm) hacia adentro.
 
| Cantidad de paredes | Grosor aproximado de la pieza. |
|---|---|
| `1` | 0.4mm |
| `2` | 0.8mm |
| `3` | 1.2mm |
| `4` | 1.6mm |
 
```bash
python generador_gcode.py --paredes 3
```
 
---
 
## Ejemplos
 
```bash
# vasija alta con mucho relieve
python generador_gcode.py --modo seno --altura 100 --amplitud 6 --frecuencia 8
 
# forma orgánica ancha
python generador_gcode.py --modo doble --radio 35 --amplitud 4 --paredes 3
 
# cono
python generador_gcode.py --modo cono --amplitud 5 --altura 80
```
 
## Configuración de impresora
 
Los parámetros de hardware están al inicio del archivo en `IMPRESORA`:
 
```python
IMPRESORA = {
    "temperatura_cama": 60,	# Temperatura de la camilla (C°) 
    "temperatura_boca": 200,	# Temperatura de la boqulla (C°)
    "diametro_filamento": 1.75, # Diámetro del filamento (mm)
    "diametro_boquilla": 0.4,	# Diámetro de la boquilla (mm)
    "velocidad_impresion": 40,	# Velocidad de la impresión (mm/s)
    "velocidad_viaje": 150,	# Velocidad de viaje (mm/s)
    "velocidad_fan": 255,	# Velocidad del ventilador 
    "centro_cama_x": 117.5,	# Centro de la camilla en el eje x (mm)
    "centro_cama_y": 117.5,	# Centro de la camilla en el eje x (mm)
)
```
 
