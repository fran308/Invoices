import streamlit as st
from datetime import datetime
import os
import json
from factura_generator import parse_number, eur, generar_pdf_factura

# Configurar la página para móvil
st.set_page_config(
    page_title="Facturación Simple",
    page_icon="📄",
    layout="centered"
)

# Cargar datos del emisor desde secrets
EMISOR = {
    'nombre': st.secrets["emisor"]["nombre"],
    'NIF': st.secrets["emisor"]["nif"],
    'direccion': st.secrets["emisor"]["direccion"],
    'email': st.secrets["emisor"]["email"]
}

# Inicializar estado de sesión
if 'conceptos' not in st.session_state:
    st.session_state.conceptos = []
if 'factura_generada' not in st.session_state:
    st.session_state.factura_generada = None

# Título
st.title("📄 Generador de Facturas")
st.markdown("---")

# Selección de tipo de factura
tipo_factura = st.radio(
    "Tipo de factura:",
    ["Simplificada", "Completa"],
    help="Factura simplificada (ticket) o factura completa con todos los datos"
)

st.markdown("---")

# Datos de la factura
col1, col2 = st.columns(2)
with col1:
    numero_factura = st.text_input("Número y serie de factura *", 
                                   help="Ej: 2024/001")
with col2:
    fecha_emision = st.date_input("Fecha de emisión", 
                                   value=datetime.now(),
                                   format="DD/MM/YYYY")

# Datos del cliente (si es factura completa o siempre obligatorio)
st.subheader("Datos del cliente")

if tipo_factura == "Completa":
    cliente = st.text_input("Nombre del cliente *")
    nif_cliente = st.text_input("NIF del cliente *")
    direccion_cliente = st.text_area("Dirección del cliente *")
else:
    # Factura simplificada - datos mínimos
    cliente = st.text_input("Nombre del cliente (opcional)", 
                            help="Para factura simplificada puede dejarse vacío")
    nif_cliente = st.text_input("NIF del cliente (opcional)")
    direccion_cliente = st.text_area("Dirección del cliente (opcional)")

# Estado de pago
pagada = st.checkbox("¿Factura pagada?", value=False)

st.markdown("---")

# Gestión de conceptos
st.subheader("📝 Conceptos")

with st.form("añadir_concepto"):
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        descripcion = st.text_input("Descripción")
    with col2:
        precio = st.number_input("Precio (€)", min_value=0.0, step=0.01, format="%.2f")
    with col3:
        iva = st.number_input("IVA (%)", min_value=0.0, max_value=100.0, value=21.0, step=1.0)
    
    incluye_iva = st.checkbox("El precio YA incluye el IVA", value=False)
    
    if st.form_submit_button("➕ Añadir concepto"):
        if descripcion and precio > 0:
            if incluye_iva:
                base_real = round(precio / (1 + iva / 100), 2)
                iva_real = round(precio - base_real, 2)
            else:
                base_real = precio
                iva_real = round(precio * iva / 100, 2)
            
            st.session_state.conceptos.append({
                "descripcion": descripcion,
                "precio": precio,
                "iva": iva,
                "incluye_iva": incluye_iva,
                "base": base_real,
                "cuota_iva": iva_real,
                "precio_con_iva": round(base_real + iva_real, 2)
            })
            st.success(f"Concepto añadido: {descripcion}")
            st.rerun()
        else:
            st.error("Debe completar descripción y precio")

# Mostrar conceptos añadidos
if st.session_state.conceptos:
    st.subheader("Conceptos añadidos:")
    
    # Calcular totales
    base_imponible = sum(c['base'] for c in st.session_state.conceptos)
    cuota_iva_total = sum(c['cuota_iva'] for c in st.session_state.conceptos)
    total = round(base_imponible + cuota_iva_total, 2)
    
    # Tabla de conceptos
    for idx, concepto in enumerate(st.session_state.conceptos):
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 0.5])
            with col1:
                st.write(concepto['descripcion'])
            with col2:
                st.write(eur(concepto['base']))
            with col3:
                st.write(f"{concepto['iva']}%")
            with col4:
                st.write(eur(concepto['precio_con_iva']))
            with col5:
                if st.button("❌", key=f"del_{idx}"):
                    st.session_state.conceptos.pop(idx)
                    st.rerun()
    
    st.markdown("---")
    st.subheader("💰 Totales")
    st.write(f"**Base imponible:** {eur(base_imponible)}")
    st.write(f"**IVA total:** {eur(cuota_iva_total)}")
    st.write(f"**TOTAL:** {eur(total)}")
    
    st.markdown("---")
    
    # Botón para generar factura
    if st.button("📄 Generar Factura", type="primary", use_container_width=True):
        # Validaciones
        if not numero_factura:
            st.error("El número de factura es obligatorio")
        elif tipo_factura == "Completa" and (not cliente or not nif_cliente or not direccion_cliente):
            st.error("Para factura completa, todos los datos del cliente son obligatorios")
        elif not st.session_state.conceptos:
            st.error("Debe añadir al menos un concepto")
        else:
            # Preparar datos para la factura
            datos_factura = {
                "numero": numero_factura,
                "fecha_emision": fecha_emision.strftime("%d/%m/%Y"),
                "cliente": cliente if cliente else "Cliente no especificado",
                "nif_cliente": nif_cliente if nif_cliente else "No especificado",
                "direccion_cliente": direccion_cliente if direccion_cliente else "No especificada",
                "pagada": pagada,
                "base_imponible": round(base_imponible, 2),
                "iva": round(cuota_iva_total, 2),
                "total": round(total, 2),
                "conceptos": st.session_state.conceptos
            }
            
            # Generar PDF
            try:
                pdf_path = generar_pdf_factura(EMISOR, datos_factura)
                
                # Guardar JSON si no está pagada
                if not pagada:
                    json_path = os.path.join("facturas", f"pending_{numero_factura.replace('/', '_')}.json")
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(datos_factura, f, indent=4, ensure_ascii=False)
                
                # Leer el PDF para ofrecer descarga
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                
                st.success(f"✅ Factura generada correctamente!")
                st.download_button(
                    label="📥 Descargar Factura PDF",
                    data=pdf_bytes,
                    file_name=f"factura_{numero_factura.replace('/', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                
                # Mostrar enlace de pago si no está pagada
                if not pagada:
                    st.info("💡 La factura no está pagada. Puedes compartir este enlace de pago:")
                    enlace_pago = f"https://tudominio.com/pagar/{numero_factura}"
                    st.code(enlace_pago)
                
            except Exception as e:
                st.error(f"Error al generar la factura: {str(e)}")
else:
    st.info("Añade al menos un concepto para generar la factura")

# Botón para limpiar todo
if st.button("🔄 Limpiar todo", use_container_width=True):
    st.session_state.conceptos = []
    st.rerun()

# Footer
st.markdown("---")
st.caption(f"Emisor: {EMISOR['nombre']} - {EMISOR['NIF']}")
