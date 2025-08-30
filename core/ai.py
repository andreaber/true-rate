# --- Explicación con IA ---
# core/ai.py

def explicar_con_ia(
    client,
    pv, pmt, n, adelantado, i_mensual,
    periodicidad=None, fecha_inicial=None, modo="Calcular tasa (i)", ultima_cuota=None,
    lang="es", model="gpt-4o-mini",
):
    """
    Explica el resultado SIN recalcular. Devuelve {'text','prompt'}.
    Mantiene compatibilidad con tu llamado actual (los nuevos args son opcionales).
    """
    if not client:
        return {"text": "⚠️ Falta configurar OPENAI_API_KEY (st.secrets o .env).", "prompt": ""}

    esquema = "pago adelantado" if adelantado else "pago vencido"
    tea_frac = (1 + i_mensual) ** 12 - 1
    tna_frac = i_mensual * 12
    mensual_pct = i_mensual * 100
    tea_pct = tea_frac * 100
    tna_pct = tna_frac * 100

    # Normalizar idioma
    lang = "es" if (lang or "").lower().startswith("es") else "en"
    idioma_texto = "en español" if lang == "es" else "in English"

    # Mensaje de sistema con instrucción explícita de idioma
    system_msg = (
        f"Actúas como profesor de Matemática Financiera. Sé claro y conciso (120–180 palabras). "
        f"Usa: prestación, contraprestación, equivalencia financiera, pago vencido/adelantado. "
        f"NO recalcules: utiliza exactamente los valores provistos."
        f"Redacta la explicación {idioma_texto}."
    )

    user_msg = (
        "Datos cerrados (no recalcular):\n"
        f"- precio_contado={pv:,.2f}\n"
        f"- cuotas={n} de {pmt:,.2f}\n"
        f"- esquema={esquema}\n"
        f"- i_mensual={i_mensual:.6f} (={mensual_pct:.3f}%)\n"
        f"- TEA={tea_frac:.6f} (={tea_pct:.2f}%)\n"
        f"- TNA={tna_frac:.6f} (={tna_pct:.2f}%)\n"
        + (f"- periodicidad={periodicidad}\n" if periodicidad else "")
        + (f"- fecha_inicial={fecha_inicial}\n" if fecha_inicial else "")
        + (f"- modo={modo}\n" if modo else "")
        + (f"- ultima_cuota_ajustada={ultima_cuota:,.2f}\n" if ultima_cuota else "")
        + "\nExplica por qué esta tasa iguala prestación y contraprestación, "
          "y comenta brevemente el efecto de vencido vs. adelantado sobre la TEA."
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
        return {"text": resp.choices[0].message.content.strip(), "prompt": user_msg}
    except Exception as e:
        return {"text": f"Error al llamar a OpenAI: {e}", "prompt": user_msg}







# def explicar_con_ia(client, pv, pmt, n, adelantado, i_mensual, model="gpt-4o-mini"):
#     """
#     Genera una explicación breve (120-180 palabras) del cálculo de tasa.
#     Requiere un cliente OpenAI ya inicializado.
#     """
#     if not client:
#         return "⚠️ Falta configurar OPENAI_API_KEY (st.secrets o .env)."

#     esquema = "pago adelantado" if adelantado else "pago vencido"

#     # Tasas en fracción y en porcentaje (convención clara)
#     anual_frac  = (1 + i_mensual) ** 12 - 1        # fracción (tanto por uno)
#     mensual_pct = i_mensual * 100                  # porcentaje (tanto por ciento)
#     anual_pct   = anual_frac * 100                 # porcentaje (tanto por ciento)

#     # Mensajes separados: reglas (system) y caso puntual (user)
#     system_msg = (
#         "Actuás como profesor experto en Matemática Financiera. "
#         "Explicás en español claro (rioplatense neutral), en 120–180 palabras, "
#         "evitando fórmulas largas. Usás términos: prestación, contraprestación, "
#         "equivalencia financiera y pago vencido/adelantado. Tu objetivo es explicar "
#         "cómo se obtuvo la tasa mensual que iguala contado y plan en cuotas."
#     )
#     user_msg = (
#         f"Datos del caso:\n"
#         f"- Precio contado (contraprestación hoy): {pv:,.2f}\n"
#         f"- Cuotas (prestación): {n} cuotas de {pmt:,.2f}\n"
#         f"- Esquema: {esquema}\n"
#         f"- Tasa mensual ≈ {mensual_pct:.3f}%\n"
#         f"- Tasa anual efectiva ≈ {anual_pct:.2f}%\n\n"
#         "Redactá la explicación solicitada."
#     )

#     try:
#         resp = client.chat.completions.create(
#             model=model,
#             messages=[
#                 {"role": "system", "content": system_msg},
#                 {"role": "user", "content": user_msg},
#             ],
#             temperature=0.2,
#         )
#         return resp.choices[0].message.content.strip()
#     except Exception as e:
#         return f"Error al llamar a OpenAI: {e}"
