import argparse
import matplotlib.pyplot as plt
from spectrometer import SpectrometerDriver
import time

def main():
    parser = argparse.ArgumentParser(description="Controlador de Espectrómetro CCD")
    parser.add_argument("-p", "--port", default="COM7", help="Puerto COM")
    parser.add_argument("-cmd", "--command", type=str, help="Comando: reset, time, accum, graph")
    parser.add_argument("-v", "--value", type=int, default=0, help="Valor para el comando (tiempo us, n accum)")
    
    args = parser.parse_args()
    
    # Instanciamos el driver
    dev = SpectrometerDriver(port=args.port)

    try:
        if args.command == "reset":
            dev.reset_device()
            
        elif args.command == "time":
            if args.value > 0:
                dev.set_integration_time(args.value)
            else:
                print("Error: Indica un valor en us con -v")

        elif args.command == "accum":
            if args.value > 0:
                dev.set_accumulations(args.value)
            else:
                print("Error: Indica N acumulaciones con -v")

        elif args.command == "cont":
            dev.set_continuous_mode()

        elif args.command == "fixed":
            print(f"Activando modo longitud fija | Acumulaciones: {dev.n_accum} - Tiempo integración: {dev.int_time_us} us")
            dev.set_fixed_length_mode()

            plt.ion()
            fig, ax = plt.subplots()
            line, = ax.plot([], [])
            ax.set_ylim(0, 4200)
            ax.set_xlim(0, dev.CCD_PIXELS)
            ax.grid(True)
            i = 1
            while True:
                pixels = dev.read_frame()
                print(f"Frame {i}/{dev.n_accum} leído.", end='\r', flush=True)
                if pixels is not None:
                    line.set_data(range(len(pixels)), pixels)
                    ax.relim()
                    # ax.autoscale_view()
                    fig.canvas.draw()
                    fig.canvas.flush_events()
                i += 1

        elif args.command == "graph":
            print("Iniciando modo gráfico... (Ctrl+C para salir)")
            plt.ion()
            fig, ax = plt.subplots()
            line, = ax.plot([], [])
            ax.set_ylim(0, 4200)
            ax.set_xlim(0, dev.CCD_PIXELS)
            ax.grid(True)
            
            while True:
                pixels = dev.read_frame()
                
                if pixels is not None:
                    line.set_data(range(len(pixels)), pixels)
                    ax.relim()
                    # ax.autoscale_view()
                    fig.canvas.draw()
                    fig.canvas.flush_events()
        
        else:
            print("Comando no reconocido o vacío. Usa -h para ayuda.")
            print("Ejemplo: python main.py -cmd time -v 10000")

    except KeyboardInterrupt:
        print("\nSaliendo...")
    finally:
        dev.close()

if __name__ == "__main__":
    main()