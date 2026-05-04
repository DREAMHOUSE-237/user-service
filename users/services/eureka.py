import os
import socket
import logging
import requests
import time
from .config_loader import cached_config

logger = logging.getLogger(__name__)

# ---------------------------
# UTILITAIRES
# ---------------------------
def get_config(key, default=None):
    return cached_config.get(key, default)

def _get_host_ip():
    """Détecte l'IP locale, mais peut être remplacée par HOST_IP fixe"""
    host_ip = os.environ.get("HOST_IP")
    if host_ip:
        return host_ip

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        host_ip = s.getsockname()[0]
    except Exception:
        host_ip = "127.0.0.1"
    finally:
        s.close()
    return host_ip


# ---------------------------
# CLEANUP DES ANCIENNES INSTANCES
# ---------------------------
def cleanup_old_instances():
    """Supprime les anciennes instances USER-SERVICE d'Eureka"""
    EUREKA_SERVER = os.environ.get("EUREKA_URL", get_config("eureka.server", "http://ec2-16-171-142-15.eu-north-1.compute.amazonaws.com:8761"))
    APP_NAME = "USER-SERVICE"

    try:
        response = requests.get(f"{EUREKA_SERVER}/apps/{APP_NAME}", timeout=5)
        if response.status_code == 200:
            logger.info("🧹 Nettoyage des anciennes instances...")
    except Exception as e:
        logger.warning(f"⚠️ Impossible de nettoyer: {e}")


# ---------------------------
# REGISTER TO EUREKA
# ---------------------------
def register():
    """Enregistre USER-SERVICE sur Eureka"""
    EUREKA_SERVER = os.environ.get("EUREKA_URL", get_config("eureka.server", "http://ec2-16-171-142-15.eu-north-1.compute.amazonaws.com:8761"))
    APP_NAME = "USER-SERVICE"
    PORT = os.environ.get("APP_PORT", get_config("service.port", "8000"))

    # IP depuis variable d'environnement (injectée via docker-compose)
    HOST_IP = _get_host_ip()
    INSTANCE_ID = f"{HOST_IP}:{APP_NAME}:{PORT}"

    url = f"{EUREKA_SERVER}/apps/{APP_NAME}"

    payload = {
        "instance": {
            "instanceId": INSTANCE_ID,
            "hostName": HOST_IP,
            "app": APP_NAME,
            "ipAddr": HOST_IP,
            "status": "UP",
            "port": {"$": int(PORT), "@enabled": "true"},
            "securePort": {"$": 443, "@enabled": "false"},
            "vipAddress": APP_NAME.lower(),
            "secureVipAddress": APP_NAME.lower(),
            "homePageUrl": f"http://{HOST_IP}:{PORT}/",
            "statusPageUrl": f"http://{HOST_IP}:{PORT}/users/health/",
            "healthCheckUrl": f"http://{HOST_IP}:{PORT}/users/health/",
            "dataCenterInfo": {
                "@class": "com.netflix.appinfo.InstanceInfo$DefaultDataCenterInfo",
                "name": "MyOwn"
            },
            "metadata": {
                "management.port": str(PORT),
                "instanceId": INSTANCE_ID
            },
            "leaseInfo": {
                "renewalIntervalInSecs": 30,
                "durationInSecs": 90
            }
        }
    }

    try:
        cleanup_old_instances()
        r = requests.post(url, json=payload, timeout=5)
        if r.status_code in [200, 204]:
            logger.info(f"✅ USER-SERVICE enregistré sur Eureka avec InstanceId: {INSTANCE_ID}")
        else:
            logger.warning(f"⚠️ Échec enregistrement Eureka {r.status_code}: {r.text}")
    except Exception as e:
        logger.error(f"❌ Enregistrement Eureka échoué: {e}")


# ---------------------------
# HEARTBEAT
# ---------------------------
def _should_reregister(status_code):
    """Retourne True si l'instance n'est plus enregistrée ou DOWN"""
    return status_code in (404, 410)

def send_heartbeat():
    """Envoie un heartbeat à Eureka"""
    EUREKA_SERVER = os.environ.get("EUREKA_URL", get_config("eureka.server", "http://ec2-16-171-142-15.eu-north-1.compute.amazonaws.com:8761"))
    APP_NAME = "USER-SERVICE"
    PORT = os.environ.get("APP_PORT", get_config("service.port", "8000"))

    HOST_IP = _get_host_ip()
    INSTANCE_ID = f"{HOST_IP}:{APP_NAME}:{PORT}"
    url = f"{EUREKA_SERVER}/apps/{APP_NAME}/{INSTANCE_ID}"

    try:
        r = requests.put(url, timeout=5)
        logger.info(f"💓 Heartbeat envoyé pour {INSTANCE_ID} (status {r.status_code})")
        return r.status_code
    except Exception as e:
        logger.error(f"❌ Heartbeat échoué: {e}")
        return None


def start_heartbeat_loop():
    """Boucle infinie qui envoie un heartbeat toutes les 25 secondes"""
    logger.info("🚀 Démarrage du heartbeat pour USER-SERVICE...")

    while True:
        status = send_heartbeat()

        if status is None:
            logger.warning("Heartbeat error — will retry...")
        elif _should_reregister(status):
            logger.warning("Eureka reports instance missing — re-registering...")
            register()

        time.sleep(25)


# ---------------------------
# EXECUTION DIRECTE
# ---------------------------
if __name__ == "__main__":
    logger.info("🚀 Démarrage USER-SERVICE et enregistrement Eureka")
    register()
    start_heartbeat_loop()