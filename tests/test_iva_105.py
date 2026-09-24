"""Validación local de desglose IVA 21% + 10,5% (sin llamar a AFIP)."""
from app.factura_electronica import resolver_importes_iva, ALIC_IVA_105, ALIC_IVA_21


def test_carne_pura():
    neto21, iva21, neto105, iva105, imp_neto, imp_iva = resolver_importes_iva(
        {"neto": 0.0, "iva": 0.0, "neto105": 3167.42, "iva105": 332.58, "total": 3500.0}
    )
    assert neto21 == 0.0 and iva21 == 0.0
    assert neto105 == 3167.42 and iva105 == 332.58
    assert imp_neto == 3167.42 and imp_iva == 332.58
    assert abs((imp_neto + imp_iva) - 3500.0) < 0.01


def test_mixto_21_y_105():
    # 21%: 9195.6 → neto 7599.67 + iva 1595.93; 10.5%: 3500 → 3167.42 + 332.58
    neto21, iva21, neto105, iva105, imp_neto, imp_iva = resolver_importes_iva(
        {
            "neto": 7599.67,
            "iva": 1595.93,
            "neto105": 3167.42,
            "iva105": 332.58,
            "total": 12695.6,
        }
    )
    assert abs(imp_neto - (7599.67 + 3167.42)) < 0.01
    assert abs(imp_iva - (1595.93 + 332.58)) < 0.01
    assert abs((imp_neto + imp_iva) - 12695.6) < 0.01
    assert ALIC_IVA_105 == 4 and ALIC_IVA_21 == 5


def test_solo_21():
    _, _, neto105, iva105, imp_neto, imp_iva = resolver_importes_iva(
        {"neto": 2644.63, "iva": 555.37, "neto105": 0, "iva105": 0, "total": 3200.0}
    )
    assert neto105 == 0.0 and iva105 == 0.0
    assert abs((imp_neto + imp_iva) - 3200.0) < 0.01
