"""Product discovery for the commercial review workflow."""
import json
from base64 import b64encode
from hashlib import sha256
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import streamlit as st


def request_discovery(key, payload):
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps({"store": False, **payload}).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=75) as response:
        return json.load(response)


def response_parts(response):
    return [
        part for item in response.get("output", []) if item.get("type") == "message"
        for part in item.get("content", []) if part.get("type") == "output_text"
    ]


def sourced_sheet(response):
    parts = response_parts(response)
    sources = dict.fromkeys(
        citation["url"]
        for part in parts
        for citation in part.get("annotations", [])
        if citation.get("type") == "url_citation"
        and urlsplit(citation.get("url", "")).scheme == "https"
        and urlsplit(citation["url"]).hostname
    )
    sheet = "\n\n".join(part["text"] for part in parts).strip()
    return sheet if sources else "", list(sources)


def show_discovery(api_key, authorized, model):
    st.caption("Buscá especificaciones de drones civiles. La consulta y la foto, si la cargás, se envían a OpenAI.")
    method = st.radio("Tipo de búsqueda", ["Marca y modelo", "Reconocer desde una foto"], horizontal=True)
    if not authorized or not api_key:
        st.info("Ingresá el código del equipo para iniciar la búsqueda.")
        return "", ""

    if method == "Reconocer desde una foto":
        photo = st.file_uploader("Foto del dron", type=["png", "jpg", "jpeg"], max_upload_size=5)
        if st.button("Sugerir modelos", disabled=photo is None):
            st.session_state.pop("drone_candidates", None)
            try:
                mime = "image/png" if photo.name.lower().endswith(".png") else "image/jpeg"
                data = b64encode(photo.getvalue()).decode("ascii")
                with st.spinner("Revisando la foto…"):
                    response = request_discovery(api_key, {
                        "model": model,
                        "instructions": (
                            "Identificá solo drones civiles. Devolvé hasta tres candidatos de marca y modelo, "
                            "uno por línea, sin viñetas. Si no hay rasgos suficientes o no es civil, devolvé VACÍO. "
                            "No estimes especificaciones técnicas."
                        ),
                        "input": [{"role": "user", "content": [
                            {"type": "input_text", "text": "Sugerí candidatos que pueda verificar."},
                            {"type": "input_image", "image_url": f"data:{mime};base64,{data}"},
                        ]}],
                        "max_output_tokens": 300,
                    })
                candidates = [
                    line.strip() for part in response_parts(response) for line in part["text"].splitlines()
                    if line.strip() and line.strip().upper() != "VACÍO"
                ][:3]
                st.session_state.drone_candidates = (photo.file_id, candidates)
                if not candidates:
                    st.info("La foto no permite sugerir un modelo. Probá con otra imagen o buscá por marca y modelo.")
            except (OSError, ValueError, KeyError, TypeError):
                st.error("No se pudo reconocer la imagen. Revisá el acceso a Responses API.")
        saved = st.session_state.get("drone_candidates")
        if not saved or photo is None or saved[0] != photo.file_id or not saved[1]:
            return "", ""
        st.caption("Los candidatos son sugerencias. Confirmá visualmente el modelo antes de buscar.")
        name = st.selectbox("Seleccioná el modelo que reconocés", saved[1], index=None)
    else:
        name = st.text_input("Marca y modelo", max_chars=100).strip()

    if st.button("Buscar ficha e imágenes", disabled=not name):
        st.session_state.pop("drone_lookup", None)
        try:
            with st.spinner("Buscando documentación del modelo…"):
                response = request_discovery(api_key, {
                    "model": model,
                    "tools": [{"type": "web_search"}],
                    "tool_choice": "required",
                    "instructions": (
                        "Investigá solamente drones civiles. Usá fuentes públicas, preferentemente del fabricante. "
                        "Confirmá la variante exacta. Escribí una ficha comercial en español, una característica por línea. "
                        "Incluí Modelo, Fabricante y País de origen solo si constan. Citá cada característica. "
                        "Cita las páginas oficiales de producto o galería con fotos cuando existan. "
                        "Omití cifras sin respaldo y cualquier detalle sobre armas o uso ofensivo. "
                        "Si no hay fuentes confiables, indicá que faltan datos."
                    ),
                    "input": name,
                    "max_output_tokens": 2400,
                })
            sheet, sources = sourced_sheet(response)
            st.session_state.drone_lookup = (name, sheet, sources)
        except HTTPError as error:
            if error.code in (401, 403):
                st.error("La clave necesita acceso a Responses API y búsqueda web.")
            else:
                st.error("OpenAI no pudo completar la búsqueda. Revisá el modelo o volvé a intentar.")
        except (OSError, ValueError, KeyError, TypeError):
            st.error("No se pudo completar la búsqueda.")
    result = st.session_state.get("drone_lookup")
    if not result or result[0] != name:
        return "", ""
    _, sheet, sources = result
    if not sheet:
        st.info("La búsqueda no devolvió una ficha con fuentes citadas.")
        return "", ""
    with st.expander("Ficha encontrada y páginas de referencia", expanded=True):
        st.text(sheet)
        for index, url in enumerate(sources, start=1):
            st.link_button(f"Fuente {index} · {urlsplit(url).hostname}", url)
    result_key = sha256((name + sheet).encode()).hexdigest()
    if st.checkbox("Usar esta ficha para generar el borrador", key=f"use-discovery-{result_key}"):
        return name, sheet
    return "", ""
