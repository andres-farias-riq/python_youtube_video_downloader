import yt_dlp
import os
import conf_management as cfg


def clear(): os.system('clear')


def menu_inicio():
    clear()
    return input('Selecciona una opción:\n1. Descargar enlace YouTube\n2. Descargar fichero\n3. Salir\n\nOpción (1|2|3): ')


def seleccionar_accion():
    return input('¿Qué deseas hacer?\n\n1. Descarga rápida vídeo y audio\n2. Descarga vídeo seleccionando calidad\n3. Descarga audio\n\nOpción (1|2|3): ')


def print_proceso_terminado():
    print('Descarga completada')
    print('-------------------------------------------------------')


def pide_url():
    return input('Url vídeo: ')


def procesa_fichero(ruta):
    with open(ruta, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def get_info(link):
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        return ydl.extract_info(link, download=False)


def inicia_proceso_descarga(link, job, loop, parent_dir):
    link = link.strip()
    if not link:
        return

    try:
        info = get_info(link)
    except Exception:
        print('Error en el link: {0}'.format(link))
        return

    print('')
    print('-------------------------------------------------------')
    print('Título: {0}'.format(info.get('title', 'Desconocido')))
    print('Canal: {0}'.format(info.get('uploader', 'Desconocido')))
    print('')

    if job == '1':  # Vídeo y audio rápido
        opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': os.path.join(parent_dir, 'video', '%(title)s.%(ext)s'),
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([link])

    elif job == '3':  # Solo audio
        opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(parent_dir, 'audio', '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([link])

    elif job == '2':  # Descarga seleccionando calidad
        formats = [
            f for f in info.get('formats', [])
            if f.get('vcodec') != 'none' and f.get('height')
        ]
        seen, unique_formats = set(), []
        for f in sorted(formats, key=lambda x: x.get('height', 0), reverse=True):
            if f['height'] not in seen:
                seen.add(f['height'])
                unique_formats.append(f)

        num = 0
        if not loop:
            print('Seleccionar calidad (1..{0})'.format(len(unique_formats)))
            for i, f in enumerate(unique_formats, 1):
                print('    ({0}) - {1}p'.format(i, f['height']))
            print('')
            num = int(input('Nº vídeo: ')) - 1

        selected = unique_formats[num]
        opts = {
            'format': '{0}+bestaudio/best'.format(selected['format_id']),
            'outtmpl': os.path.join(parent_dir, 'video', '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([link])

    print_proceso_terminado()


if __name__ == "__main__":
    parent_dir = cfg.get_ruta_descargas()
    tarea = None

    while tarea != '3':
        enlaces = []
        loop = False
        tarea = menu_inicio()
        clear()

        if tarea == '1':
            enlaces.append(pide_url())
        elif tarea == '2':
            loop = True
            ruta_fichero = input('Ruta fichero enlaces: ')
            enlaces = procesa_fichero(ruta_fichero)

        if not enlaces:
            continue

        job = ''
        while job not in ['1', '2', '3']:
            clear()
            job = seleccionar_accion()

        for enlace in enlaces:
            inicia_proceso_descarga(enlace, job, loop, parent_dir)
