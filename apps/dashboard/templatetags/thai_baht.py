# -*- coding: utf-8 -*-
from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def thai_baht_text(amount):
    """Convert number to Thai text (Baht)."""
    try:
        if not amount:
            return "ศูนย์บาทถ้วน"

        # Convert to Decimal for precision
        if isinstance(amount, str):
            amount = Decimal(amount)
        elif isinstance(amount, (int, float)):
            amount = Decimal(str(amount))

        baht = int(amount)
        satang = int(round((amount - baht) * 100))

        def num_to_thai(num):
            if num == 0:
                return ""

            ones = ["", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า"]
            places = ["", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน", "ล้าน"]

            num_str = str(num)
            length = len(num_str)
            result = ""

            for i, digit in enumerate(num_str):
                d = int(digit)
                place_value = length - i - 1

                if d == 0:
                    continue

                # Million
                if place_value >= 6:
                    result += num_to_thai(int(num_str[:length - 6]))
                    result += "ล้าน"
                    return result + num_to_thai(int(num_str[length - 6:]))

                # Tens place special cases
                if place_value == 1:
                    if d == 1:
                        result += "สิบ"
                    elif d == 2:
                        result += "ยี่สิบ"
                    else:
                        result += ones[d] + "สิบ"
                # Ones place when previous is tens
                elif place_value == 0 and length > 1 and int(num_str[-2]) != 0:
                    if d == 1:
                        result += "เอ็ด"
                    else:
                        result += ones[d]
                else:
                    result += ones[d] + places[place_value]

            return result

        result = num_to_thai(baht) if baht > 0 else "ศูนย์"
        result += "บาท"

        if satang > 0:
            result += num_to_thai(satang) + "สตางค์"
        else:
            result += "ถ้วน"

        return result
    except Exception as e:
        return f"Error: {str(e)}"
