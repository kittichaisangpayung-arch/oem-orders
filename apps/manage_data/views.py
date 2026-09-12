from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.core.access import staff_required
from apps.core.models import Customer, Product, Store


@method_decorator(login_required, name="dispatch")
class StaffRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not staff_required(request.user):
            return HttpResponseForbidden(render_to_string("manage_data/forbidden.html", request=request))
        return super().dispatch(request, *args, **kwargs)


class CustomerListView(StaffRequiredMixin, ListView):
    model = Customer
    template_name = "manage_data/customer_list.html"
    context_object_name = "customers"
    ordering = ["name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search', '')
        status = self.request.GET.get('status', '')

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(parser_key__icontains=search)
            )

        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        return context


class CustomerCreateView(StaffRequiredMixin, CreateView):
    model = Customer
    fields = ["name", "code", "parser_key", "is_active"]
    template_name = "manage_data/customer_form.html"
    success_url = reverse_lazy("manage_data:customer_list")


class CustomerUpdateView(StaffRequiredMixin, UpdateView):
    model = Customer
    fields = ["name", "code", "parser_key", "is_active"]
    template_name = "manage_data/customer_form.html"
    success_url = reverse_lazy("manage_data:customer_list")


class CustomerDeleteView(StaffRequiredMixin, DeleteView):
    model = Customer
    template_name = "manage_data/customer_confirm_delete.html"
    success_url = reverse_lazy("manage_data:customer_list")


class StoreListView(StaffRequiredMixin, ListView):
    model = Store
    template_name = "manage_data/store_list.html"
    context_object_name = "stores"
    ordering = ["name"]

    def get_queryset(self):
        queryset = super().get_queryset().select_related("customer")
        search = self.request.GET.get('search', '')
        customer_id = self.request.GET.get('customer', '')
        status = self.request.GET.get('status', '')

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(store_code__icontains=search) |
                Q(customer__name__icontains=search)
            )

        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['customer_filter'] = self.request.GET.get('customer', '')
        context['status'] = self.request.GET.get('status', '')
        context['customers'] = Customer.objects.filter(is_active=True).order_by('name')
        return context


class StoreCreateView(StaffRequiredMixin, CreateView):
    model = Store
    fields = ["customer", "store_code", "name", "is_active"]
    template_name = "manage_data/store_form.html"
    success_url = reverse_lazy("manage_data:store_list")


class StoreUpdateView(StaffRequiredMixin, UpdateView):
    model = Store
    fields = ["customer", "store_code", "name", "is_active"]
    template_name = "manage_data/store_form.html"
    success_url = reverse_lazy("manage_data:store_list")


class StoreDeleteView(StaffRequiredMixin, DeleteView):
    model = Store
    template_name = "manage_data/store_confirm_delete.html"
    success_url = reverse_lazy("manage_data:store_list")


class ProductListView(StaffRequiredMixin, ListView):
    model = Product
    template_name = "manage_data/product_list.html"
    context_object_name = "products"
    ordering = ["barcode"]

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search', '')
        status = self.request.GET.get('status', '')

        if search:
            queryset = queryset.filter(
                Q(barcode__icontains=search) |
                Q(description__icontains=search)
            )

        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        return context


class ProductCreateView(StaffRequiredMixin, CreateView):
    model = Product
    fields = ["barcode", "description", "uom", "min_order_qty", "sort_rank", "is_active"]
    template_name = "manage_data/product_form.html"
    success_url = reverse_lazy("manage_data:product_list")


class ProductUpdateView(StaffRequiredMixin, UpdateView):
    model = Product
    fields = ["barcode", "description", "uom", "min_order_qty", "sort_rank", "is_active"]
    template_name = "manage_data/product_form.html"
    success_url = reverse_lazy("manage_data:product_list")


class ProductDeleteView(StaffRequiredMixin, DeleteView):
    model = Product
    template_name = "manage_data/product_confirm_delete.html"
    success_url = reverse_lazy("manage_data:product_list")
