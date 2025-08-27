from flask import Flask
import redis
import time
import os

from featureflags.client import CfClient
from featureflags.evaluations.auth_target import Target

app = Flask(__name__)

def wait_for_redis():
    """Esperar a que Redis esté disponible"""
    max_retries = 10
    retry_delay = 1
    
    for i in range(max_retries):
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            redis_client.ping()
            print("✅ Redis conectado exitosamente")
            return redis_client
        except redis.ConnectionError:
            print(f"⏳ Esperando por Redis... ({i+1}/{max_retries})")
            time.sleep(retry_delay)
    
    raise Exception("❌ No se pudo conectar a Redis")

# ---------- Feature Flags (Harness) ----------
api_key = os.getenv("FF_SDK_KEY")
cf = CfClient(api_key) if api_key else None
flag_name = os.getenv("FF_FLAG_NAME", "color_por_visita")
# ---------------------------------------------

@app.route('/')
def contador_visitas():
    try:
        redis_client = wait_for_redis()
        visitas = redis_client.incr('visitas')
        es_par = visitas % 2 == 0
        flag_on = False
        flag_txt = "OFF"

        if cf is not None:
            # Target dinámico por visita
            target = Target(identifier=f"user-{visitas}", name=f"user-{visitas}")
            # Evalúa el flag booleano: True → ON, False → OFF
            flag_on = cf.bool_variation(flag_name, target, False)
            flag_txt = "ON" if flag_on else "OFF"

        color = "green" if (es_par and flag_on) else "red"
        texto = "PAR" if (flag_on and es_par) else "IMPAR"

        return f'''
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>📊 Contador de Visitas</h1>
                <p style="font-size: 24px;">¡Número de visitas: <strong>{visitas}</strong>! 🎉</p>
                <div style="display:inline-block;padding:12px 16px;border-radius:8px;color:#fff;background:{color};font-weight:700;margin-top:12px;">
                  {texto}
                </div>
                <p style="margin-top:8px;">Flag <code>{flag_name}</code>: <b>{flag_txt}</b></p>
                <p>✅ Redis funcionando correctamente</p>
                <a href="/reiniciar">🔄 Reiniciar contador</a> | 
                <a href="/health">❤️ Health check</a>
            </body>
        </html>
        '''
    except Exception as e:
        return f'❌ Error: {str(e)}'

@app.route('/reiniciar')
def reiniciar_contador():
    try:
        redis_client = wait_for_redis()
        redis_client.set('visitas', 0)
        return '✅ ¡Contador reiniciado! <a href="/">Volver</a>'
    except Exception as e:
        return f'❌ Error: {str(e)}'

@app.route('/health')
def health_check():
    try:
        redis_client = wait_for_redis()
        redis_client.ping()
        return '✅ Health check: Todo funciona correctamente (Flask + Redis)'
    except Exception as e:
        return f'❌ Health check failed: {str(e)}'

if __name__ == '__main__':
    print("🚀 Iniciando aplicación Flask + Redis...")
    app.run(host='0.0.0.0', port=5000)