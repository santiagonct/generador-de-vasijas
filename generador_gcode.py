"""Generador simple de GCode para vasijas."""

import argparse
import math
import os
from datetime import datetime

import numpy as np

IMPRESORA = {
    "temperatura_cama": 60,
    "temperatura_boca": 200,
    "diametro_filamento": 1.75,
    "diametro_boquilla": 0.4,
    "velocidad_impresion": 40,
    "velocidad_viaje": 150,
    "velocidad_fan": 255,
    "centro_cama_x": 117.5,
    "centro_cama_y": 117.5,
}

VALORES_POR_DEFECTO = {
    "radio": 25.0,
    "altura": 60.0,
    "altura_capa": 0.2,
    "amplitud": 3.0,
    "frecuencia": 6.0,
    "puntos_por_capa": 90,
    "paredes": 2,
    "modo": "seno",
}


def superficie_seno(z, params):
    factor = params["frecuencia"] * 2 * math.pi / params["altura"]
    return params["radio"] + params["amplitud"] * math.sin(factor * z)


def superficie_doble(z, params):
    base = params["frecuencia"] * 2 * math.pi / params["altura"]
    segundo = base * 2.3
    return (
        params["radio"]
        + params["amplitud"] * 0.7 * math.sin(base * z)
        + params["amplitud"] * 0.3 * math.sin(segundo * z)
    )


def superficie_cono(z, params):
    crecimiento = params["amplitud"] * 0.5 * (z / params["altura"])
    factor = params["frecuencia"] * 2 * math.pi / params["altura"]
    return params["radio"] + crecimiento + params["amplitud"] * 0.5 * math.sin(factor * z)


def superficie_ruido(z, params):
    frecuencias = [1.0, 2.3, 3.7, 5.1, 7.0]
    fases = [0.0, 1.1, 2.4, 0.7, 3.2]
    pesos = [0.5, 0.25, 0.15, 0.07, 0.03]
    base = params["frecuencia"] * 2 * math.pi / params["altura"]
    radio = params["radio"]

    for frecuencia, fase, peso in zip(frecuencias, fases, pesos):
        radio += params["amplitud"] * peso * math.sin(base * frecuencia * z + fase)

    return radio


MODOS = {
    "seno": superficie_seno,
    "doble": superficie_doble,
    "cono": superficie_cono,
    "ruido": superficie_ruido,
}


def normalizar_modo(modo):
    if modo in MODOS:
        return modo
    raise ValueError(f"Modo no válido: {modo}")


def calcular_extrusion(dx, dy, dz, altura_capa):
    longitud = math.sqrt(dx**2 + dy**2 + dz**2)
    area_cordon = IMPRESORA["diametro_boquilla"] * altura_capa
    volumen = longitud * area_cordon
    area_filamento = math.pi * (IMPRESORA["diametro_filamento"] / 2) ** 2
    return volumen / area_filamento


def escribir_gcode(params, filepath):
    capas = int(params["altura"] / params["altura_capa"])
    puntos_por_capa = params["puntos_por_capa"]
    paredes = params["paredes"]
    superficie = MODOS[params["modo"]]
    altura_capa = params["altura_capa"]

    centro_x = IMPRESORA["centro_cama_x"]
    centro_y = IMPRESORA["centro_cama_y"]
    velocidad_impresion = IMPRESORA["velocidad_impresion"] * 60
    velocidad_viaje = IMPRESORA["velocidad_viaje"] * 60
    boquilla = IMPRESORA["diametro_boquilla"]

    lineas = []
    total_e = 0.0

    def agregar(linea):
        lineas.append(linea)

    def mover_sin_extrusion(x, y):
        agregar(f"G1 X{x:.3f} Y{y:.3f} F{velocidad_viaje}")

    def extruir_segmento(x_anterior, y_anterior, x, y):
        nonlocal total_e
        paso_e = calcular_extrusion(x - x_anterior, y - y_anterior, 0, altura_capa)
        total_e += paso_e
        agregar(f"G1 X{x:.3f} Y{y:.3f} E{total_e:.5f} F{velocidad_impresion}")

    agregar(f"; GCode generado con generador_gcode.py")
    agregar(f"; {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    agregar(f"; modo={params['modo']}  radio={params['radio']}  altura={params['altura']}")
    agregar(f"; amplitud={params['amplitud']}  frecuencia={params['frecuencia']}")
    agregar(f"; capas={capas}  paredes={paredes}  puntos/capa={puntos_por_capa}")
    agregar("")
    agregar("G28")
    agregar("G90")
    agregar("M82")
    agregar(f"M104 S{IMPRESORA['temperatura_boca']}")
    agregar(f"M140 S{IMPRESORA['temperatura_cama']}")
    agregar(f"M109 S{IMPRESORA['temperatura_boca']}")
    agregar(f"M190 S{IMPRESORA['temperatura_cama']}")
    agregar("G92 E0")
    agregar("")
    agregar("; purga")
    agregar(f"G1 X10 Y20 Z0.3 F{velocidad_viaje}")
    agregar(f"G1 X10 Y180 E15 F{velocidad_impresion}")
    agregar("G92 E0")
    total_e = 0.0
    agregar(f"M106 S{IMPRESORA['velocidad_fan']}")
    agregar("")

    angulos = np.linspace(0, 2 * math.pi, puntos_por_capa, endpoint=False)

    for indice_capa in range(capas):
        z = (indice_capa + 1) * altura_capa
        radio_exterior = superficie(z, params)

        agregar("")
        agregar(f"; capa {indice_capa + 1}/{capas} z={z:.3f} mm")
        agregar(f"G1 Z{z:.3f} F{velocidad_viaje}")

        for indice_pared in range(paredes):
            radio = radio_exterior - indice_pared * boquilla
            if radio <= 0:
                break

            puntos = [
                (centro_x + radio * math.cos(angulo), centro_y + radio * math.sin(angulo))
                for angulo in angulos
            ]

            agregar(f"; pared {indice_pared + 1}/{paredes} radio={radio:.3f} mm")
            mover_sin_extrusion(puntos[0][0], puntos[0][1])

            for index in range(1, len(puntos)):
                extruir_segmento(puntos[index - 1][0], puntos[index - 1][1], puntos[index][0], puntos[index][1])

            extruir_segmento(puntos[-1][0], puntos[-1][1], puntos[0][0], puntos[0][1])

    agregar("")
    agregar("; fin de impresión")
    agregar("M104 S0")
    agregar("M140 S0")
    agregar("M106 S0")
    agregar(f"G1 X10 Y{IMPRESORA['centro_cama_y'] * 2 - 10} F{velocidad_viaje}")
    agregar("M84")

    with open(filepath, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lineas))

    return len(lineas), total_e


def imprimir_resumen(params, filepath, lineas_generadas, total_e):
    capas = int(params["altura"] / params["altura_capa"])
    tamaño_kb = os.path.getsize(filepath) / 1024
    filamento_m = (total_e * math.pi * (IMPRESORA["diametro_filamento"] / 2) ** 2) / 1000

    print("\n✓ Listo")
    print(f"  Archivo   : {filepath}")
    print(f"  Capas     : {capas}")
    print(f"  Paredes   : {params['paredes']}")
    print(f"  Líneas    : {lineas_generadas:,}")
    print(f"  Tamaño    : {tamaño_kb:.1f} KB")
    print(f"  Filamento : {filamento_m:.2f} m\n")


def main():
    parser = argparse.ArgumentParser(description="Generador de GCode para vasijas")
    parser.add_argument(
        "--modo",
        "--mode",
        dest="modo",
        default=VALORES_POR_DEFECTO["modo"],
        choices=list(MODOS.keys()),
    )
    parser.add_argument(
        "--radio",
        "--radius",
        type=float,
        default=VALORES_POR_DEFECTO["radio"],
    )
    parser.add_argument(
        "--altura",
        "--height",
        type=float,
        default=VALORES_POR_DEFECTO["altura"],
    )
    parser.add_argument(
        "--amplitud",
        "--amplitude",
        type=float,
        default=VALORES_POR_DEFECTO["amplitud"],
    )
    parser.add_argument(
        "--frecuencia",
        "--frequency",
        type=float,
        default=VALORES_POR_DEFECTO["frecuencia"],
    )
    parser.add_argument(
        "--altura-capa",
        "--layer",
        type=float,
        default=VALORES_POR_DEFECTO["altura_capa"],
    )
    parser.add_argument(
        "--puntos",
        "--points",
        type=int,
        default=VALORES_POR_DEFECTO["puntos_por_capa"],
    )
    parser.add_argument(
        "--paredes",
        "--walls",
        type=int,
        default=VALORES_POR_DEFECTO["paredes"],
    )
    parser.add_argument("--salida", "--output", default=None)
    args = parser.parse_args()

    params = {
        "modo": normalizar_modo(args.modo),
        "radio": args.radio,
        "altura": args.altura,
        "amplitud": args.amplitud,
        "frecuencia": args.frecuencia,
        "altura_capa": args.altura_capa,
        "puntos_por_capa": args.puntos,
        "paredes": args.paredes,
    }

    print("\nGenerador de vasijas")
    for clave, valor in params.items():
        etiqueta = {
            "modo": "Modo",
            "radio": "Radio",
            "altura": "Altura",
            "amplitud": "Amplitud",
            "frecuencia": "Frecuencia",
            "altura_capa": "Altura de capa",
            "puntos_por_capa": "Puntos por capa",
            "paredes": "Paredes",
        }[clave]
        print(f"  {etiqueta:<18}: {valor}")
    print()

    if args.salida:
        filepath = args.salida
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"vasija_{params['modo']}_{timestamp}.gcode"

    print(f"Generando {filepath}...")
    lineas_generadas, total_e = escribir_gcode(params, filepath)
    imprimir_resumen(params, filepath, lineas_generadas, total_e)


if __name__ == "__main__":
    main()
