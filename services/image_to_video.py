import os
import subprocess
import logging
from services.file_management import download_file
from PIL import Image

STORAGE_PATH = "/tmp/"
logger = logging.getLogger(__name__)

def process_image_to_video(
    image_url, 
    length, 
    frame_rate, 
    zoom_speed, 
    job_id, 
    output_resolution="1024x1024",  # Nuevo parámetro con valor por defecto
    webhook_url=None
):
    try:
        # Parsear la resolución de salida
        out_width, out_height = map(int, output_resolution.split('x'))
        output_dims = f"{out_width}x{out_height}"
        
        # Descargar la imagen
        image_path = download_file(image_url, STORAGE_PATH)
        logger.info(f"Downloaded image to {image_path}")

        # Obtener dimensiones de la imagen
        with Image.open(image_path) as img:
            width, height = img.size
        logger.info(f"Original image dimensions: {width}x{height}")

        # Preparar ruta de salida
        output_path = os.path.join(STORAGE_PATH, f"{job_id}.mp4")

        # Determinar orientación y dimensiones de escala
        if width > height:
            scale_dims = f"{out_width * 8}:{out_height * 8}"  # Ej: 8640x8640 para 1080x1080
        else:
            scale_dims = f"{out_height * 8}:{out_width * 8}"  # Ej: 8640x8640 para 1080x1080

        # Calcular frames y factor de zoom
        total_frames = int(length * frame_rate)
        zoom_factor = 1 + (zoom_speed * length)

        logger.info(f"Output resolution: {output_dims}")
        logger.info(f"Using scale dimensions: {scale_dims}")
        logger.info(f"Video length: {length}s, Frame rate: {frame_rate}fps, Total frames: {total_frames}")
        logger.info(f"Zoom speed: {zoom_speed}/s, Final zoom factor: {zoom_factor}")

        # Comando FFmpeg con resolución dinámica
        cmd = [
            'ffmpeg', 
            '-framerate', str(frame_rate), 
            '-loop', '1', 
            '-i', image_path,
            '-vf', 
            f"scale={scale_dims},"  # Escala inicial alta
            f"zoompan=z='min(1+({zoom_speed}*{length})*on/{total_frames},{zoom_factor})':"
            f"d={total_frames}:"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"s={output_dims}",  # Resolución dinámica aquí
            '-c:v', 'libx264', 
            '-t', str(length), 
            '-pix_fmt', 'yuv420p', 
            output_path
        ]

        logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
        
        # Ejecutar FFmpeg
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg command failed. Error: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)

        logger.info(f"Video created successfully: {output_path}")
        os.remove(image_path)  # Limpiar
        return output_path
        
    except Exception as e:
        logger.error(f"Error in process_image_to_video: {str(e)}", exc_info=True)
        raise
