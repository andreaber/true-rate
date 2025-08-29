import pandas as pd


# --- Matemática financiera (pago vencido) ---
def present_value_annuity(pmt, i, n, adelantado=False):
    """Valor presente de una renta; pago vencido o adelantado."""
    if i == 0:
        pv = pmt * n
    else:
        pv = pmt * (1 - (1 + i) ** (-n)) / i
    if adelantado:
        pv *= (1 + i)
    return pv

# --- Cálculo de tasa implícita ---
def baily_initial_guess(pv, pmt, n):
    """Semilla tipo Baily para arrancar Newton."""
    return max(((pmt * n / pv) - 1) * 2.0 / (n + 1.0), 1e-6)

# --- Tasa mensual que iguala PV y PMT en n cuotas ---
def solve_monthly_rate(pv, pmt, n, adelantado=False, tol=1e-12, max_iter=80):
    """Halla i mensual tal que VP(cuotas)=pv. Newton con fallback bisección."""
    i = baily_initial_guess(pv, pmt, n)

    # --- Newton-Raphson ---
    for _ in range(max_iter):
        if i <= 0:
            i = 1e-6
        a = (1 + i) ** (-n)
        f = present_value_annuity(pmt, i, n, adelantado) - pv
        # derivada aproximada clásica para renta vencida/adelantada
        df = pmt * ((i * n * a) / (1 + i) + (a - 1)) / (i ** 2)
        if df == 0:
            break
        i_new = i - f / df
        if abs(i_new - i) < tol:
            i = i_new
            return i
        i = i_new

    # --- Bisección robusta, si Newton no fue suficiente ---
    lo, hi = 1e-12, 10.0
    mid = (lo + hi) / 2
    for _ in range(200):
        mid = (lo + hi) / 2
        fmid = present_value_annuity(pmt, mid, n, adelantado) - pv
        if abs(fmid) < 1e-10:
            return mid
        flo = present_value_annuity(pmt, lo, n, adelantado) - pv
        if flo * fmid <= 0:
            hi = mid
        else:
            lo = mid
    return mid

# --- Tasa mensual con traza (pasos) ---
def solve_monthly_rate_trace(pv, pmt, n, adelantado=False, tol=1e-12, max_iter=80):
    """Como solve_monthly_rate pero devolviendo (i, trace) con pasos de Newton y Bisección."""
    trace = []
    # --- Newton-Raphson con semilla tipo Baily ---
    i = baily_initial_guess(pv, pmt, n)

    # Newton
    for k in range(1, max_iter + 1):
        if i <= 0:
            i = 1e-6
        a = (1 + i) ** (-n)
        f = present_value_annuity(pmt, i, n, adelantado) - pv

        df = pmt * ((i * n * a) / (1 + i) + (a - 1)) / (i ** 2)
        trace.append({"iter": k, "method": "newton", "i": i, "f": f, "df": df})
        if df == 0:
            break
        i_new = i - f / df
        if abs(i_new - i) < tol:
            i = i_new
            return i, trace
        i = i_new

    # Bisección de respaldo
    lo, hi = 1e-12, 10.0
    for k in range(1, 201):
        mid = (lo + hi) / 2
        fmid = present_value_annuity(pmt, mid, n, adelantado) - pv
        trace.append({"iter": k, "method": "bisect", "lo": lo, "hi": hi, "mid": mid, "fmid": fmid})
        if abs(fmid) < 1e-10:
            return mid, trace
        flo = present_value_annuity(pmt, lo, n, adelantado) - pv
        if flo * fmid <= 0:
            hi = mid
        else:
            lo = mid
    return mid, trace

# --- Tasa anual efectiva desde tasa mensual ---
def annual_effective(i_m):
    """Tasa anual efectiva a partir de la tasa mensual i_m."""
    return (1 + i_m) ** 12 - 1

# --- Tabla de flujo de caja ---
def cashflow_table(pmt, n, adelantado, i):
    """
    Devuelve (df_flujo, total_vp) con columnas: periodo, cuota, factor_descuento, vp_cuota.
    """
    rows = []
    for k in range(1, n + 1):
        # Pago vencido: descuenta k períodos; adelantado: k-1
        exp = (k - 1) if adelantado else k
        factor = (1 + i) ** (-exp)
        vp = pmt * factor
        rows.append({
            "periodo": k,
            "cuota": pmt,
            "factor_descuento": factor,
            "vp_cuota": vp,
        })
    total_vp = sum(r["vp_cuota"] for r in rows)
    df = pd.DataFrame(rows)
    return df, total_vp
