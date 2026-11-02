"""سرویس‌های انبار — محاسبه‌ی بهای تمام‌شده میانگین موزون."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import StockBalance, StockMove, Warehouse

def get_or_create_default_warehouse(company) -> Warehouse:
    wh = Warehouse.objects.filter(company=company, is_active=True).order_by("code").first()
    if wh:
        return wh
    wh, _ = Warehouse.objects.get_or_create(
        company=company, code="MAIN",
        defaults={"name": "انبار اصلی", "is_active": True},
    )
    return wh

def get_balance(warehouse: Warehouse, product) -> StockBalance:
    bal, _ = StockBalance.objects.get_or_create(
        company=warehouse.company, warehouse=warehouse, product=product,
        defaults={"quantity": Decimal("0"), "avg_cost": Decimal("0"), "total_value": Decimal("0")},
    )
    return bal

@transaction.atomic
def receive_stock(*, warehouse: Warehouse, product, qty, unit_cost,
                  date, reference: str = "", note: str = "") -> StockMove:
    qty = Decimal(qty)
    unit_cost = Decimal(unit_cost)
    if qty <= 0:
        raise ValidationError("مقدار ورودی باید بزرگ‌تر از صفر باشد.")
    if unit_cost < 0:
        raise ValidationError("بهای واحد نمی‌تواند منفی باشد.")

    bal = StockBalance.objects.select_for_update().filter(
        warehouse=warehouse, product=product,
    ).first()
    if not bal:
        bal = StockBalance.objects.create(
            company=warehouse.company, warehouse=warehouse, product=product,
            quantity=Decimal("0"), avg_cost=Decimal("0"), total_value=Decimal("0"),
        )

    old_qty, old_val = bal.quantity, bal.total_value
    added_val = (qty * unit_cost).quantize(Decimal("0.01"))
    new_qty = old_qty + qty
    new_val = old_val + added_val
    new_avg = (new_val / new_qty).quantize(Decimal("0.0001")) if new_qty > 0 else Decimal("0")

    bal.quantity = new_qty
    bal.avg_cost = new_avg
    bal.total_value = new_val.quantize(Decimal("0.01"))
    bal.save(update_fields=["quantity", "avg_cost", "total_value"])

    return StockMove.objects.create(
        company=warehouse.company, warehouse=warehouse, product=product,
        move_type=StockMove.MoveType.IN, quantity=qty,
        unit_cost=unit_cost, total_cost=added_val,
        date=date, reference=reference, note=note,
    )

@transaction.atomic
def issue_stock(*, warehouse: Warehouse, product, qty,
                date, reference: str = "", note: str = "") -> StockMove:
    qty = Decimal(qty)
    if qty <= 0:
        raise ValidationError("مقدار خروجی باید بزرگ‌تر از صفر باشد.")

    bal = StockBalance.objects.select_for_update().filter(
        warehouse=warehouse, product=product,
    ).first()
    if not bal or bal.quantity <= 0:
        raise ValidationError(f"موجودی «{product.name}» در انبار «{warehouse.name}» صفر است.")
    if bal.quantity < qty:
        raise ValidationError(
            f"موجودی کافی نیست: «{product.name}» — موجودی: {bal.quantity}، نیاز: {qty}"
        )

    unit_cost = bal.avg_cost
    remaining = bal.quantity - qty

    if remaining <= Decimal("0.0001"):
        total_cost = bal.total_value
        bal.quantity = Decimal("0")
        bal.total_value = Decimal("0")
    else:
        total_cost = (qty * unit_cost).quantize(Decimal("0.01"))
        bal.quantity = remaining
        bal.total_value = (bal.total_value - total_cost).quantize(Decimal("0.01"))

    bal.save(update_fields=["quantity", "total_value"])

    return StockMove.objects.create(
        company=warehouse.company, warehouse=warehouse, product=product,
        move_type=StockMove.MoveType.OUT, quantity=qty,
        unit_cost=unit_cost, total_cost=total_cost,
        date=date, reference=reference, note=note,
    )
