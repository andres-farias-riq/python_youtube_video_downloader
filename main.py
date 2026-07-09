import yt_dlp
import os
import logging
import questionary
import conf_management as cfg


def _js_runtimes():
    import shutil
    from pathlib import Path

    # Prefer highest nvm version available
    nvm_dir = Path.home() / '.nvm' / 'versions' / 'node'
    if nvm_dir.exists():
        versions = sorted(nvm_dir.iterdir(), key=lambda p: tuple(
            int(x) for x in p.name.lstrip('v').split('.')
        ), reverse=True)
        for v in versions:
            node_bin = v / 'bin' / 'node'
            if node_bin.exists():
                return {'node': {'path': str(node_bin)}}

    for candidate in ['node', 'nodejs']:
        path = shutil.which(candidate)
        if path:
            return {'node': {'path': path}}
    return {}

YTDLP_BASE_OPTS = {
    'js_runtimes': _js_runtimes(),
    'remote_components': {'ejs:github'},
}


def setup_logging(parent_dir):
    log_path = os.path.join(parent_dir, 'downloader.log')
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[logging.FileHandler(log_path, encoding='utf-8')],
    )
    return log_path


def clear():
    os.system('clear')
    print('\n' * 3, end='')  # padding so questionary doesn't render at the very top


def print_separador():
    print('-------------------------------------------------------')


def procesa_fichero(ruta):
    with open(ruta, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def get_info(link):
    with yt_dlp.YoutubeDL({**YTDLP_BASE_OPTS, 'quiet': True}) as ydl:
        return ydl.extract_info(link, download=False)


def inicia_proceso_descarga(link, job, loop, parent_dir):
    link = link.strip()
    if not link:
        return

    try:
        info = get_info(link)
    except Exception as e:
        logging.error('Error obteniendo info del link %s: %s', link, e)
        print('Error en el link: {0}'.format(link))
        return

    print('')
    print_separador()
    print('Título : {0}'.format(info.get('title', 'Desconocido')))
    print('Canal  : {0}'.format(info.get('uploader', 'Desconocido')))
    print('')
    logging.info('Iniciando descarga: %s (job=%s)', info.get('title'), job)

    try:
        if job == 'fast':
            opts = {
                **YTDLP_BASE_OPTS,
                'format': 'best[ext=mp4]/best',
                'outtmpl': os.path.join(parent_dir, 'video', '%(title)s.%(ext)s'),
                'logger': logging.getLogger('yt_dlp'),
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([link])

        elif job == 'audio':
            opts = {
                **YTDLP_BASE_OPTS,
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(parent_dir, 'audio', '%(title)s.%(ext)s'),
                'logger': logging.getLogger('yt_dlp'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([link])

        elif job == 'quality':
            formats = [
                f for f in info.get('formats', [])
                if f.get('vcodec') != 'none' and f.get('height')
            ]
            seen, unique_formats = set(), []
            for f in sorted(formats, key=lambda x: x.get('height', 0), reverse=True):
                if f['height'] not in seen:
                    seen.add(f['height'])
                    unique_formats.append(f)

            if loop:
                selected = unique_formats[0]
            else:
                clear()
                selected = questionary.select(
                    'Selecciona la calidad:',
                    choices=[
                        questionary.Choice('{0}p'.format(f['height']), value=f)
                        for f in unique_formats
                    ]
                ).ask()
                if selected is None:
                    return

            opts = {
                **YTDLP_BASE_OPTS,
                'format': '{0}+bestaudio/best'.format(selected['format_id']),
                'outtmpl': os.path.join(parent_dir, 'video', '%(title)s.%(ext)s'),
                'merge_output_format': 'mp4',
                'logger': logging.getLogger('yt_dlp'),
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([link])

        print('')
        print_separador()
        print('Descarga completada')
        print_separador()

    except Exception as e:
        logging.error('Error durante la descarga de %s: %s', link, e, exc_info=True)
        print('Error durante la descarga. Revisa el log en: {0}'.format(
            os.path.join(parent_dir, 'downloader.log')))


if __name__ == '__main__':
    parent_dir = cfg.get_ruta_descargas()
    setup_logging(parent_dir)

    while True:
        clear()
        tarea = questionary.select(
            '¿Qué deseas hacer?',
            choices=[
                questionary.Choice('Descargar un enlace de YouTube', value='link'),
                questionary.Choice('Descargar desde fichero de enlaces', value='file'),
                questionary.Choice('Salir', value='exit'),
            ]
        ).ask()

        if tarea is None or tarea == 'exit':
            break

        enlaces = []
        loop = False

        if tarea == 'link':
            url = questionary.text('URL del vídeo:').ask()
            if url:
                enlaces.append(url.strip())
        elif tarea == 'file':
            loop = True
            ruta = questionary.path('Ruta del fichero de enlaces:').ask()
            try:
                enlaces = procesa_fichero(ruta)
            except Exception as e:
                print('Error leyendo fichero: {0}'.format(e))
                input('Presiona Enter para continuar...')
                continue

        if not enlaces:
            continue

        clear()
        job = questionary.select(
            '¿Cómo deseas descargarlo?',
            choices=[
                questionary.Choice('Descarga rápida (vídeo + audio, hasta 720p)', value='fast'),
                questionary.Choice('Seleccionar calidad (mejor calidad disponible)', value='quality'),
                questionary.Choice('Solo audio (MP3 192kbps)', value='audio'),
            ]
        ).ask()

        if job is None:
            continue

        for enlace in enlaces:
            inicia_proceso_descarga(enlace, job, loop, parent_dir)

        input('\nPresiona Enter para volver al menú...')
        clear()
