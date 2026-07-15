import yt_dlp
import os
import conf_management as cfg


def clear(): os.system('clear')


def menu_inicio():
    clear()
    return input('Selecciona una opción:\n1. Descargar enlace (YouTube / OK.ru / ...)\n2. Descargar fichero\n3. Salir\n\nOpción (1|2|3): ')


def seleccionar_accion():
    return input('¿Qué deseas hacer?\n\n1. Descarga rápida vídeo y audio\n2. Descarga vídeo seleccionando calidad\n3. Descarga audio\n\nOpción (1|2|3): ')


def pide_url():
    return input('Url vídeo (vacío para volver al menú): ').strip()


def elige_job():
    job = ''
    while job not in ['1', '2', '3']:
        clear()
        job = seleccionar_accion()
    return job


def procesa_fichero(ruta):
    with open(ruta, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def _fmt_size(n):
    n = float(n or 0)
    for unit in ['B', 'KiB', 'MiB', 'GiB']:
        if n < 1024:
            return '{0:.1f} {1}'.format(n, unit)
        n /= 1024
    return '{0:.1f} TiB'.format(n)


def _hooks(state):
    """Devuelve (progress_hook, postprocessor_hook) que pintan una barra de
    progreso limpia y capturan la ruta final del archivo en `state`."""
    bar_len = 24

    def progress(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            done = d.get('downloaded_bytes', 0)
            pct = (done / total * 100) if total else 0
            speed = d.get('speed')
            eta = d.get('eta')
            speed_str = '{0:.1f} MiB/s'.format(speed / 1048576) if speed else '--'
            eta_str = '{0}s'.format(eta) if eta is not None else '--'
            filled = int(bar_len * pct / 100)
            bar = '█' * filled + '░' * (bar_len - filled)
            print('\r  [{0}] {1:5.1f}%  {2:>11}  ETA {3:<5}'.format(
                bar, pct, speed_str, eta_str), end='', flush=True)
        elif d['status'] == 'finished':
            state['filepath'] = d.get('filename')
            print('\r  [{0}] 100.0%  descarga completa, finalizando…{1}'.format(
                '█' * bar_len, ' ' * 10))

    def postproc(d):
        # Tras convertir a mp3 o mergear vídeo+audio, la ruta final cambia.
        if d['status'] == 'finished':
            fp = (d.get('info_dict') or {}).get('filepath')
            if fp:
                state['filepath'] = fp

    return progress, postproc


def get_info(link):
    with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
        return ydl.extract_info(link, download=False)


def inicia_proceso_descarga(link, job, loop, parent_dir, idx=None, total=None):
    """Descarga un enlace. Devuelve un dict con el resultado para el resumen."""
    link = link.strip()
    if not link:
        return None

    prefijo = '[{0}/{1}] '.format(idx, total) if idx and total and total > 1 else ''
    print('')
    print('-------------------------------------------------------')
    print('{0}🔎 Obteniendo información…'.format(prefijo))

    try:
        info = get_info(link)
    except Exception as e:
        print('❌ Error obteniendo el vídeo: {0}'.format(link))
        print('   {0}'.format(str(e).splitlines()[0] if str(e) else 'motivo desconocido'))
        return {'ok': False, 'link': link, 'title': link}

    titulo = info.get('title', 'Desconocido')
    print('   Título: {0}'.format(titulo))
    print('   Canal:  {0}'.format(info.get('uploader') or 'Desconocido'))

    state = {'filepath': None}
    progress, postproc = _hooks(state)
    base_opts = {
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,  # silencia la barra propia de yt-dlp; usamos nuestro hook
        'progress_hooks': [progress],
        'postprocessor_hooks': [postproc],
    }

    if job == '1':  # Vídeo y audio rápido
        print('⬇️  Descargando vídeo…')
        opts = dict(base_opts, **{
            'format': 'best[ext=mp4]/best',
            'outtmpl': os.path.join(parent_dir, 'video', '%(title)s.%(ext)s'),
        })

    elif job == '3':  # Solo audio
        print('⬇️  Descargando audio (→ mp3)…')
        opts = dict(base_opts, **{
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(parent_dir, 'audio', '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })

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
            print('')
            print('Seleccionar calidad (1..{0})'.format(len(unique_formats)))
            for i, f in enumerate(unique_formats, 1):
                print('    ({0}) - {1}p'.format(i, f['height']))
            print('')
            num = int(input('Nº vídeo: ')) - 1

        selected = unique_formats[num]
        print('⬇️  Descargando vídeo a {0}p…'.format(selected['height']))
        # Mergea el vídeo elegido con el mejor audio (YouTube: streams DASH separados).
        # Si no hay audio aparte (OK.ru entrega HLS ya muxeado), cae al propio format_id
        # para respetar la calidad seleccionada en vez de a '/best'.
        opts = dict(base_opts, **{
            'format': '{0}+bestaudio/{0}'.format(selected['format_id']),
            'outtmpl': os.path.join(parent_dir, 'video', '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
        })
    else:
        return None

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([link])
    except Exception as e:
        print('❌ Error descargando: {0}'.format(titulo))
        print('   {0}'.format(str(e).splitlines()[0] if str(e) else 'motivo desconocido'))
        return {'ok': False, 'link': link, 'title': titulo}

    ruta = state.get('filepath')
    if ruta and os.path.exists(ruta):
        print('✅ Guardado en: {0} ({1})'.format(ruta, _fmt_size(os.path.getsize(ruta))))
    else:
        print('✅ Descarga completada')
    return {'ok': True, 'link': link, 'title': titulo}


def resumen_final(resultados):
    hechos = [r for r in resultados if r]
    if len(hechos) <= 1:
        return
    ok = [r for r in hechos if r['ok']]
    fallos = [r for r in hechos if not r['ok']]
    print('')
    print('=======================================================')
    print('Resumen: {0} descargado(s), {1} con error'.format(len(ok), len(fallos)))
    for r in fallos:
        print('  ❌ {0}'.format(r['title']))
    print('=======================================================')


if __name__ == "__main__":
    parent_dir = cfg.get_ruta_descargas()
    tarea = None

    while tarea != '3':
        tarea = menu_inicio()

        if tarea == '1':  # Modo continuo: se pegan URLs una tras otra
            job = elige_job()
            clear()
            print('Modo continuo — pega URLs una tras otra.')
            print('Deja la URL vacía para volver al menú.')
            while True:
                url = pide_url()
                if not url:
                    break
                inicia_proceso_descarga(url, job, False, parent_dir)

        elif tarea == '2':  # Modo fichero (lote)
            ruta_fichero = input('Ruta fichero enlaces: ')
            enlaces = procesa_fichero(ruta_fichero)
            if not enlaces:
                continue
            job = elige_job()
            clear()
            total = len(enlaces)
            resultados = []
            for i, enlace in enumerate(enlaces, 1):
                resultados.append(inicia_proceso_descarga(enlace, job, True, parent_dir, i, total))
            resumen_final(resultados)
            input('\nPulsa Enter para volver al menú…')
