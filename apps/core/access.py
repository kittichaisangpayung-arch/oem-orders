def in_group(user, group_name):
    return user.is_superuser or user.groups.filter(name=group_name).exists()


def in_sales_group(user):
    return in_group(user, "sales")


def staff_required(user):
    return user.is_active and user.is_staff
