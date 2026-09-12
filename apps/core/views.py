from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProductMinOrderForm
from .models import Product


@login_required
def product_config(request):
    if request.method == "POST":
        product = get_object_or_404(Product, pk=request.POST.get("product_id"))
        form = ProductMinOrderForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
        return redirect("core:product_config")

    products = Product.objects.filter(is_active=True)
    rows = [{"product": p, "form": ProductMinOrderForm(instance=p)} for p in products]

    return render(request, "core/product_config.html", {"rows": rows})
