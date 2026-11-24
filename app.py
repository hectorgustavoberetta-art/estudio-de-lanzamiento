from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Estudio de Lanzamiento", layout="wide")
st.title("Estudio de Lanzamiento")
st.caption("Prototipo académico · Caso ficticio de inspección industrial")

source_path = Path(__file__).parent / "demo" / "ficha-inspecta-i1.md"
source = source_path.read_text(encoding="utf-8")
sections = dict(
    section.split("\n", 1)
    for section in source.split("\n## ")[1:]
)

source_panel, preview = st.columns([1, 1], gap="large")
with source_panel:
    st.subheader("Ficha original")
    st.markdown(source)

with preview:
    st.subheader("Vista comercial")
    audience = st.radio("Público", ["Cliente final", "Distribuidor"], horizontal=True)
    st.caption("Vista de prueba con textos preparados. Generación por IA pendiente.")
    st.markdown("### Inspecta I1")
    if audience == "Cliente final":
        st.write("Documentá condiciones visibles de cubiertas y fachadas para que el equipo de mantenimiento revise las imágenes.")
        claims = ["Aplicación", "Registro de imágenes", "Autonomía declarada"]
    else:
        st.write("Presentá el kit de inspección a tus clientes con el equipamiento incluido y las condiciones comerciales por confirmar.")
        claims = ["Contenido del kit", "Condiciones comerciales", "Autonomía declarada"]

    for heading in claims:
        with st.expander(heading):
            st.write(sections[heading].strip())

    st.warning("Afirmación de prueba pendiente de revisión: «32 minutos garantizados»")
    correction = st.text_input("Texto corregido", value="Hasta 32 minutos en condiciones de ensayo.")
    if st.button("Revisar corrección"):
        supported = correction.rstrip(".").strip().casefold() == "hasta 32 minutos en condiciones de ensayo"
        if supported:
            st.success("La corrección de prueba conserva el límite y las condiciones de ensayo.")
        else:
            st.info("Compará el texto con el apartado Autonomía declarada antes de aprobarlo.")
