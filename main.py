import os
import time
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from openpyxl import load_workbook

# Guardar las credenciales en archivo físico si vienen como variable
if os.getenv("GOOGLE_CREDS_JSON"):
    with open("credentials.json", "w") as f:
        f.write(os.getenv("GOOGLE_CREDS_JSON"))

# Variables de entorno
EROS_USER = os.getenv("EROS_USER")
EROS_PASS = os.getenv("EROS_PASS")
FENIX_USER = os.getenv("FENIX_USER")
FENIX_PASS = os.getenv("FENIX_PASS")
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID")
EXCEL_NAME = os.getenv("EXCEL_NAME", "reportes_diarios.xlsx")

# Carpeta de descargas temporales
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# URLs
EROS_URL = "https://admin.erosonline.net/index.php"
FENIX_URL = "https://admin.fenixcasino.vip/index.php"

# Función para automatizar login y descarga

def descargar_reporte(playwright, plataforma):
    browser = playwright.chromium.launch()
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()

    if plataforma == "Eros":
        login_url = EROS_URL
        user = EROS_USER
        password = EROS_PASS
    else:
        login_url = FENIX_URL
        user = FENIX_USER
        password = FENIX_PASS

    page.goto(login_url)
    page.fill("input[name='username']", user)
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle")

    # Ir a balance o sección de descargas
    page.goto(f"{login_url}?act=admin&area=balance")
    page.wait_for_load_state("networkidle")

    # Click en ícono de descarga (ajustar selector según la web)
    with page.expect_download() as download_info:
        page.click("a[href*='export']")  # REVISAR selector real
    download = download_info.value
    file_path = os.path.join(DOWNLOAD_DIR, f"{plataforma.lower()}.xlsx")
    download.save_as(file_path)
    print(f"{plataforma} descargado en: {file_path}")

    context.close()
    browser.close()
    return file_path

# Subida a Google Drive

def subir_a_drive(nombre_archivo):
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("credentials.json")
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
    gauth.SaveCredentialsFile("credentials.json")

    drive = GoogleDrive(gauth)
    archivo = drive.CreateFile({
        'title': nombre_archivo,
        'parents': [{'id': GDRIVE_FOLDER_ID}]
    })
    archivo.SetContentFile(nombre_archivo)
    archivo.Upload()
    print(f"Archivo subido a Google Drive: {nombre_archivo}")

# Combina y actualiza el Excel

def actualizar_excel(ruta_eros, ruta_fenix):
    df_eros = pd.read_excel(ruta_eros)
    df_fenix = pd.read_excel(ruta_fenix)
    df_final = pd.concat([df_eros, df_fenix], ignore_index=True)

    if os.path.exists(EXCEL_NAME):
        libro = load_workbook(EXCEL_NAME)
        hoja = libro.active
        for fila in df_final.itertuples(index=False, name=None):
            hoja.append(fila)
        libro.save(EXCEL_NAME)
    else:
        df_final.to_excel(EXCEL_NAME, index=False)
    print("Excel actualizado.")

    subir_a_drive(EXCEL_NAME)

# MAIN

def main():
    with sync_playwright() as playwright:
        ruta_eros = descargar_reporte(playwright, "Eros")
        ruta_fenix = descargar_reporte(playwright, "Fenix")
        actualizar_excel(ruta_eros, ruta_fenix)

if __name__ == "__main__":
    main()
