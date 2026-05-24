#facturacion_app.py

import streamlit as st
from datetime import datetime
import os
from decimal import Decimal, ROUND_HALF_UP
from factura_generador import generar_pdf_factura, eur, calcular_iva_preciso, calcular_precio_con_iva

# Configurar la página para móvil
st.set_page_config(
    page_title="Facturación Simple",
    page_icon="📄",
    layout="centered"
)

# Cargar datos del emisor desde secrets
try:
    EMISOR = {
        'nombre': st.secrets["emisor"]["nombre"],
        'NIF': st.secrets["emisor"]["nif"],
        'direccion': st.secrets["emisor"]["direccion"],
        'email': st.secrets["emisor"]["email"]
    }
except Exception as e:
    st.error(f"Error cargando configuración: {e}")
    st.stop()

# Inicializar estado de sesión
if 'conceptos' not in st.session_state:
    st.session_state.conceptos = []

# Título
st.title("📄 Generador de Facturas")
st.markdown("---")

# Selección de tipo de factura
tipo_factura = st.radio(
    "Tipo de factura:",
    ["Simplificada", "Completa"],
    help="Factura simplificada (ticket) no requiere datos del cliente | Factura completa sí los requiere obligatoriamente"
)

st.markdown("---")

# Datos de la factura
col1, col2 = st.columns(2)
with col1:
    numero_factura = st.text_input("Número y serie de factura *", 
                                   help="Ej: 2024/001",
                                   key="num_factura")
with col2:
    fecha_emision = st.date_input("Fecha de emisión", 
                                   value=datetime.now(),
                                   format="DD/MM/YYYY")

# Datos del cliente - condicional según tipo de factura
st.subheader("Datos del cliente")

if tipo_factura == "Completa":
    # Campos OBLIGATORIOS para factura completa
    st.markdown("⚠️ **Datos obligatorios para factura completa**")
    cliente = st.text_input("Nombre del cliente *", key="cliente_nombre")
    nif_cliente = st.text_input("NIF del cliente *", key="cliente_nif")
    direccion_cliente = st.text_area("Dirección del cliente *", key="cliente_direccion")
    
    # Aviso sobre protección de datos
    st.info("ℹ️ Los datos del cliente son necesarios para cumplir con la normativa fiscal. Se almacenarán únicamente en la factura generada.")
else:
    # Factura simplificada - campos opcionales pero NO se mostrarán en el PDF
    st.markdown("✅ **Factura simplificada - No se requieren datos del cliente**")
    st.caption("Según normativa española, las facturas simplificadas (tickets) no requieren identificación del cliente")
    
    # Estos campos existen pero no se usarán en el PDF
    cliente = ""
    nif_cliente = ""
    direccion_cliente = ""
    
    # Mostrar un mensaje informativo
    st.info("📋 Al generar la factura simplificada, NO aparecerán los datos del cliente en el PDF, cumpliendo con la normativa de protección de datos y facturación.")

# Estado de pago
pagada = st.checkbox("¿Factura pagada?", value=False)

st.markdown("---")

# Gestión de conceptos
st.subheader("📝 Conceptos")

with st.form("añadir_concepto"):
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        descripcion = st.text_input("Descripción", key="desc_input")
    with col2:
        # ✅ CAMBIO IMPORTANTE: step=1.0 para que suba/baje de euro en euro
        precio = st.number_input(
            "Precio (€)", 
            min_value=0.0, 
            step=1.0,  # ← ANTES: step=0.01, AHORA: step=1.0
            format="%.2f", 
            key="precio_input"
        )
    with col3:
        iva = st.number_input(
            "IVA (%)", 
            min_value=0.0, 
            max_value=100.0, 
            value=21.0, 
            step=1.0,  # Este ya estaba bien (sube/baja de 1 en 1)
            key="iva_input"
        )
    
    incluye_iva = st.checkbox("El precio YA incluye el IVA", value=False, key="incluye_iva")
    
    submitted = st.form_submit_button("➕ Añadir concepto")
    if submitted:
        if descripcion and precio > 0:
            if incluye_iva:
                # ✅ Cálculo preciso según normativa Hacienda
                base_real, iva_real = calcular_precio_con_iva(precio, iva)
                precio_final = precio
            else:
                # ✅ Cálculo preciso según normativa Hacienda
                base_real = precio
                iva_real = calcular_iva_preciso(precio, iva)
                precio_final = round(base_real + iva_real, 2)
            
            st.session_state.conceptos.append({
                "descripcion": descripcion,
                "precio": precio,
                "iva": iva,
                "incluye_iva": incluye_iva,
                "base": base_real,
                "cuota_iva": iva_real,
                "precio_con_iva": precio_final
            })
            st.success(f"✓ Añadido: {descripcion}")
            st.rerun()
        else:
            st.error("❌ Descripción y precio son obligatorios")

# Mostrar conceptos añadidos
if st.session_state.conceptos:
    st.subheader("📋 Conceptos añadidos:")
    
    # Calcular totales sumando de manera precisa con Decimal
    base_imponible_dec = Decimal('0')
    cuota_iva_total_dec = Decimal('0')
    total_dec = Decimal('0')
    
    for c in st.session_state.conceptos:
        base_imponible_dec += Decimal(str(c['base']))
        cuota_iva_total_dec += Decimal(str(c['cuota_iva']))
        total_dec += Decimal(str(c['precio_con_iva']))
    
    # Redondear totales finales a 2 decimales
    base_imponible = float(base_imponible_dec.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    cuota_iva_total = float(cuota_iva_total_dec.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    total = float(total_dec.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    # Tabla de conceptos en Streamlit
    for idx, concepto in enumerate(st.session_state.conceptos):
        cols = st.columns([2.5, 1.2, 1, 1.2, 1.2, 0.4])
        with cols[0]:
            st.write(concepto['descripcion'])
        with cols[1]:
            st.write(eur(concepto['base']))
        with cols[2]:
            st.write(f"{concepto['iva']:.1f}%")
        with cols[3]:
            st.write(eur(concepto['cuota_iva']))
        with cols[4]:
            st.write(eur(concepto['precio_con_iva']))
        with cols[5]:
            if st.button("🗑️", key=f"del_{idx}"):
                st.session_state.conceptos.pop(idx)
                st.rerun()
    
    st.markdown("---")
    
    # Totales en UI
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Base imponible", eur(base_imponible))
    with col2:
        st.metric("IVA total", eur(cuota_iva_total))
    with col3:
        st.metric("TOTAL", eur(total))
    
    st.markdown("---")
    
    # Botón para generar factura
    if st.button("📄 Generar Factura", type="primary", use_container_width=True):
        error = False
        if not numero_factura:
            st.error("❌ El número de factura es obligatorio")
            error = True
        elif tipo_factura == "Completa" and (not cliente or not nif_cliente or not direccion_cliente):
            st.error("❌ Para factura completa, TODOS los datos del cliente son obligatorios")
            error = True
        elif not st.session_state.conceptos:
            st.error("❌ Debe añadir al menos un concepto")
            error = True
        
        if not error:
            # Preparar datos consistentes
            if tipo_factura == "Simplificada":
                # Para factura simplificada, los datos del cliente no se incluyen
                datos_factura = {
                    "tipo": tipo_factura,
                    "numero": numero_factura,
                    "fecha_emision": fecha_emision.strftime("%d/%m/%Y"),
                    "cliente": "",  # Vacío
                    "nif_cliente": "",  # Vacío
                    "direccion_cliente": "",  # Vacío
                    "pagada": pagada,
                    "base_imponible": base_imponible,
                    "cuota_iva_total": cuota_iva_total,
                    "total": total,
                    "conceptos": st.session_state.conceptos
                }
            else:
                # Para factura completa, se incluyen todos los datos
                datos_factura = {
                    "tipo": tipo_factura,
                    "numero": numero_factura,
                    "fecha_emision": fecha_emision.strftime("%d/%m/%Y"),
                    "cliente": cliente,
                    "nif_cliente": nif_cliente,
                    "direccion_cliente": direccion_cliente,
                    "pagada": pagada,
                    "base_imponible": base_imponible,
                    "cuota_iva_total": cuota_iva_total,
                    "total": total,
                    "conceptos": st.session_state.conceptos
                }
            
            try:
                # Generar PDF
                ruta_pdf = generar_pdf_factura(EMISOR, datos_factura)
                
                st.success("✅ ¡Factura generada correctamente!")
                
                # Leer el archivo para descarga
                with open(ruta_pdf, "rb") as f:
                    pdf_bytes = f.read()
                
                # Botón de descarga
                st.download_button(
                    label="📥 Descargar Factura PDF",
                    data=pdf_bytes,
                    file_name=f"factura_{numero_factura.replace('/', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                
                if not pagada:
                    st.info("💡 **Información de pago:**")
                    st.markdown(f"""
                    - **Método:** Transferencia bancaria / Efectivo
                    - **Referencia:** {numero_factura}
                    - **Total a pagar:** {eur(total)}
                    """)
                    st.warning("⚠️ Esta factura NO está marcada como pagada")
                
            except Exception as e:
                st.error(f"❌ Error al generar la factura: {str(e)}")
else:
    st.info("➕ Añade al menos un concepto para generar la factura")

# Botón para limpiar
if st.button("🔄 Limpiar todos los conceptos", use_container_width=True):
    st.session_state.conceptos = []
    st.rerun()

# Footer
st.markdown("---")
st.caption(f"Emisor: {EMISOR['nombre']} - {EMISOR['NIF']}")
